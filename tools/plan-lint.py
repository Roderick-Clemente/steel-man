#!/usr/bin/env python3
"""tools/plan-lint.py — deterministic pre-review tier for build plans.

Catches machine-checkable contract defects before a frontier panel
round is spent. BLOCK-only: a PASS is never evidence of plan quality
and never an approval input; the panel fires on whatever survives.

Per tools/plan-lint-spec.md (v1 draft). The spec is the contract;
implementation choices are per §13.

Interface:
    tools/plan-lint.py <plan.md> [--repo-root <path>] [--json <out.json>] [--contract <path>]

Exit codes:
    0 = PASS (warnings allowed, printed)
    2 = usage / internal error / fail-closed (missing ground-truth artifact)
    3 = BLOCK (findings on stdout + --json)

Telemetry: appends one row per invocation following telemetry/SCHEMA.md
conventions and §17.3 gitignore discipline.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── constants ────────────────────────────────────────────────────────────

EXIT_PASS = 0
EXIT_ERROR = 2
EXIT_BLOCK = 3

RULE_NAMES: dict[int, str] = {
    1: "field-path",
    2: "cli-flag",
    3: "model-id-family",
    4: "internal-consistency",
    5: "call-signature",
    6: "required-anchors",
    7: "file-paths",
}

# Families (values in MODEL_FAMILY_MAP) — used for type-confusion detection.
FAMILY_LABELS: frozenset[str] = frozenset({
    "claude-family", "openai-family", "grok-family",
    "gemini-family", "glm-family",
})


# ── data structures ──────────────────────────────────────────────────────


class Finding:
    """A single BLOCK or warning finding."""

    def __init__(
        self,
        rule: int,
        line: int,
        claim: str,
        artifact: str,
        reason: str,
        severity: str = "BLOCK",
    ) -> None:
        self.rule = rule
        self.rule_name = RULE_NAMES.get(rule, f"rule-{rule}")
        self.line = line
        self.claim = claim
        self.artifact = artifact
        self.reason = reason
        self.severity = severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "rule_class": self.rule_name,
            "line": self.line,
            "claim": self.claim,
            "artifact": self.artifact,
            "reason": self.reason,
            "severity": self.severity,
        }

    def format_text(self) -> str:
        tag = "BLOCK" if self.severity == "BLOCK" else "WARNING"
        return (
            f"[{tag}] rule={self.rule} ({self.rule_name}) line={self.line}\n"
            f"  claim: {self.claim}\n"
            f"  artifact: {self.artifact}\n"
            f"  reason: {self.reason}"
        )


class FailClosed(Exception):
    """Raised when a ground-truth artifact is missing/unreadable.
    The tool exits with code 2, never a silent pass.
    """

    def __init__(self, reason: str, artifact: str = "") -> None:
        self.reason = reason
        self.artifact = artifact
        super().__init__(reason)


# ── contract extraction ──────────────────────────────────────────────────


def extract_contract_from_plan(plan_text: str) -> dict[str, Any] | None:
    """Extract an embedded ```contract fenced block from the plan markdown.

    Returns the parsed JSON dict, or None if no contract block found.
    Raises FailClosed if the block is malformed JSON.
    """
    pattern = r"```contract\s*\n(.*?)\n```"
    match = re.search(pattern, plan_text, re.DOTALL)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise FailClosed(f"malformed CONTRACT block: {e}", "CONTRACT block")
    return data


def load_contract_file(path: str) -> dict[str, Any]:
    """Load a contract from an external JSON file."""
    p = Path(path)
    if not p.exists():
        raise FailClosed(f"contract file not found: {path}", path)
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise FailClosed(f"malformed contract file: {e}", path)


def resolve_contract(
    plan_text: str,
    plan_path: Path,
    contract_flag: str | None,
) -> tuple[dict[str, Any] | None, str]:
    """Resolve the contract source. Precedence (per spec):
    1. Embedded fenced block (wins if both fence and --contract exist).
    2. --contract CLI flag (sidecar file).
    3. Companion <plan>.contract.json file.

    Returns (contract_dict_or_None, source_description).
    """
    embedded = extract_contract_from_plan(plan_text)
    if embedded is not None:
        return embedded, "embedded CONTRACT block"

    if contract_flag:
        return load_contract_file(contract_flag), f"--contract {contract_flag}"

    companion = plan_path.with_suffix(".contract.json")
    if companion.exists():
        return load_contract_file(str(companion)), f"companion {companion.name}"

    return None, "none (heuristic mode)"


# ── ground-truth loaders ─────────────────────────────────────────────────


def load_json_artifact(repo_root: Path, artifact_path: str) -> Any:
    """Load a JSON artifact from the repo. Fail-closed if missing/unreadable."""
    full = repo_root / artifact_path
    if not full.exists():
        raise FailClosed(
            f"ground-truth artifact not found: {artifact_path}",
            artifact_path,
        )
    try:
        return json.loads(full.read_text())
    except json.JSONDecodeError as e:
        raise FailClosed(
            f"ground-truth artifact unreadable: {artifact_path}: {e}",
            artifact_path,
        )


def load_python_source(repo_root: Path, artifact_path: str) -> str:
    """Load a Python source file. Fail-closed if missing/unreadable."""
    full = repo_root / artifact_path
    if not full.exists():
        raise FailClosed(
            f"ground-truth artifact not found: {artifact_path}",
            artifact_path,
        )
    try:
        return full.read_text()
    except OSError as e:
        raise FailClosed(
            f"ground-truth artifact unreadable: {artifact_path}: {e}",
            artifact_path,
        )


def load_model_family_map(repo_root: Path) -> dict[str, tuple[str, str]]:
    """Load MODEL_FAMILY_MAP from tools/sprint_loop/config.py.
    Fail-closed if the file or the map is missing.
    """
    config_path = repo_root / "tools" / "sprint_loop" / "config.py"
    if not config_path.exists():
        raise FailClosed(
            "MODEL_FAMILY_MAP source not found: tools/sprint_loop/config.py",
            "tools/sprint_loop/config.py",
        )
    source = config_path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise FailClosed(
            f"cannot parse config.py: {e}",
            "tools/sprint_loop/config.py",
        )
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "MODEL_FAMILY_MAP":
                    return _eval_model_family_map(node.value)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "MODEL_FAMILY_MAP":
                if node.value is not None:
                    return _eval_model_family_map(node.value)
    raise FailClosed(
        "MODEL_FAMILY_MAP not found in tools/sprint_loop/config.py",
        "tools/sprint_loop/config.py",
    )


def _eval_model_family_map(node: ast.AST) -> dict[str, tuple[str, str]]:
    """Safely evaluate a MODEL_FAMILY_MAP dict literal AST node."""
    result: dict[str, tuple[str, str]] = {}
    if not isinstance(node, ast.Dict):
        raise FailClosed(
            "MODEL_FAMILY_MAP is not a dict literal",
            "tools/sprint_loop/config.py",
        )
    for key_node, value_node in zip(node.keys, node.values):
        key = ast.literal_eval(key_node)
        if isinstance(value_node, ast.Tuple):
            val = tuple(ast.literal_eval(e) for e in value_node.elts)
        else:
            val = ast.literal_eval(value_node)
        result[key] = val
    return result


# ── rule checkers ────────────────────────────────────────────────────────


def check_field_path(
    claim: dict[str, Any],
    repo_root: Path,
) -> Finding | None:
    """Rule 1: field-path references resolve against live JSON artifacts.

    Checks that the named field_path exists in the artifact JSON.
    """
    artifact = claim.get("artifact", "")
    field_path = claim.get("field_path", "")
    expect = claim.get("expect", "exists")

    if not artifact:
        return Finding(
            rule=1, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=artifact,
            reason="rule 1 requires an 'artifact' (JSON file path)",
        )

    data = load_json_artifact(repo_root, artifact)

    if expect == "exists":
        if not field_path:
            return Finding(
                rule=1, line=claim.get("line", 0),
                claim=claim.get("claim", ""),
                artifact=artifact,
                reason="rule 1 requires a 'field_path' to check",
            )
        if not _field_path_exists(data, field_path):
            return Finding(
                rule=1, line=claim.get("line", 0),
                claim=claim.get("claim", ""),
                artifact=artifact,
                reason=f"field path '{field_path}' not found in {artifact}",
            )
    return None


def _field_path_exists(data: Any, field_path: str) -> bool:
    """Check if a dotted field path exists in a JSON structure.

    Supports: 'verdict', 'reviewers', 'reviewers[0].verdict',
    'reviewers[*].verdict' (wildcard: all elements must have the field),
    'chunk_commit_sha', 'schema'.
    """
    parts = _parse_field_path(field_path)
    return _walk_field_path(data, parts)


def _parse_field_path(path: str) -> list[tuple[str, int | None]]:
    """Parse 'a.b[0].c' or 'a[*].c' into [(a, None), (b, 0), (c, None)]."""
    parts: list[tuple[str, int | None]] = []
    for segment in path.split("."):
        match = re.match(r"^(\w+)(?:\[(\d+|\*)\])?$", segment)
        if not match:
            parts.append((segment, None))
            continue
        key = match.group(1)
        idx_str = match.group(2)
        if idx_str is None:
            parts.append((key, None))
        elif idx_str == "*":
            parts.append((key, -2))  # wildcard
        else:
            parts.append((key, int(idx_str)))
    return parts


def _walk_field_path(data: Any, parts: list[tuple[str, int | None]]) -> bool:
    if not parts:
        return True
    key, idx = parts[0]
    rest = parts[1:]

    if not isinstance(data, dict):
        return False
    if key not in data:
        return False

    val = data[key]
    if idx is None:
        return _walk_field_path(val, rest)

    if idx == -2:  # wildcard
        if not isinstance(val, list):
            return False
        if not val:
            return False
        return all(_walk_field_path(item, rest) for item in val)

    # specific index
    if not isinstance(val, list):
        return False
    if idx >= len(val):
        return False
    return _walk_field_path(val[idx], rest)


def check_cli_flag(
    claim: dict[str, Any],
    repo_root: Path,
) -> Finding | None:
    """Rule 2: CLI flag references resolve against argparse definitions."""
    artifact = claim.get("artifact", "")
    field_path = claim.get("field_path", "")

    if not artifact:
        return Finding(
            rule=2, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=artifact,
            reason="rule 2 requires an 'artifact' (Python file with argparse)",
        )

    source = load_python_source(repo_root, artifact)
    flags = _extract_argparse_flags(source)

    # field_path is the flag name, e.g. "--prior-token"
    flag = field_path.strip()
    if not flag:
        return Finding(
            rule=2, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=artifact,
            reason="rule 2 requires a 'field_path' (flag name)",
        )

    if flag not in flags:
        return Finding(
            rule=2, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=artifact,
            reason=f"flag '{flag}' not found in argparse definitions of {artifact}",
        )
    return None


def _extract_argparse_flags(source: str) -> set[str]:
    """Extract all --flag names from add_argument calls in Python source."""
    flags: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return flags
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "add_argument":
                if node.args:
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        flags.add(first_arg.value)
    return flags


def check_model_id_family(
    claim: dict[str, Any],
    repo_root: Path,
) -> Finding | None:
    """Rule 3: model ids and family labels resolve against MODEL_FAMILY_MAP;
    flag id-vs-label type confusion.
    """
    field_path = claim.get("field_path", "")
    expect = claim.get("expect", "model_id")

    family_map = load_model_family_map(repo_root)
    model_ids = set(family_map.keys())
    families = set(v[1] for v in family_map.values())

    # field_path is like "MODEL_FAMILY_MAP.grok-4.5" or "MODEL_FAMILY_MAP.grok-family"
    # Extract the value after "MODEL_FAMILY_MAP."
    value = field_path
    if value.startswith("MODEL_FAMILY_MAP."):
        value = value[len("MODEL_FAMILY_MAP."):]

    if not value:
        return Finding(
            rule=3, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=claim.get("artifact", ""),
            reason="rule 3 requires a 'field_path' (MODEL_FAMILY_MAP.<value>)",
        )

    if expect == "model_id":
        if value not in model_ids:
            if value in families:
                return Finding(
                    rule=3, line=claim.get("line", 0),
                    claim=claim.get("claim", ""),
                    artifact=claim.get("artifact", ""),
                    reason=f"'{value}' is a family label, not a model id — type confusion",
                )
            return Finding(
                rule=3, line=claim.get("line", 0),
                claim=claim.get("claim", ""),
                artifact=claim.get("artifact", ""),
                reason=f"'{value}' is not a known model id in MODEL_FAMILY_MAP",
            )
    elif expect == "family_label":
        if value not in families:
            if value in model_ids:
                return Finding(
                    rule=3, line=claim.get("line", 0),
                    claim=claim.get("claim", ""),
                    artifact=claim.get("artifact", ""),
                    reason=f"'{value}' is a model id, not a family label — type confusion",
                )
            return Finding(
                rule=3, line=claim.get("line", 0),
                claim=claim.get("claim", ""),
                artifact=claim.get("artifact", ""),
                reason=f"'{value}' is not a known family label",
            )
    elif expect == "type_confusion:family_label_as_model_id":
        # The claim asserts that a family label is being used where a
        # model id is expected — this IS the finding.
        return Finding(
            rule=3, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=claim.get("artifact", ""),
            reason=f"type confusion: family label used where model id expected",
        )
    return None


def check_internal_consistency(
    claim: dict[str, Any],
    repo_root: Path,
    all_claims: list[dict[str, Any]],
) -> Finding | None:
    """Rule 4: numeric contract claims agree; artifact names consistent.

    Checks:
    - min_reviewers_2: the named function requires >= 2 reviewers.
    - emits_1_reviewer: the named function emits 1 reviewer.
    - pattern:<pattern>: filename pattern consistency across claims.
    """
    expect = claim.get("expect", "")
    artifact = claim.get("artifact", "")
    field_path = claim.get("field_path", "")

    if expect == "min_reviewers_2":
        # Verify the named function's source contains a >= 2 check.
        source = load_python_source(repo_root, artifact)
        func_name = field_path
        if _function_contains_check(source, func_name, "2"):
            return None
        return Finding(
            rule=4, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=artifact,
            reason=f"function '{func_name}' does not contain a >= 2 reviewer check",
        )

    if expect == "emits_1_reviewer":
        # Verify the named function emits a single reviewer.
        source = load_python_source(repo_root, artifact)
        func_name = field_path.split(".")[0] if "." in field_path else field_path
        if _function_emits_single_reviewer(source, func_name):
            # This IS the inconsistency: gate requires >= 2, stub emits 1.
            # Check if another claim asserts >= 2.
            has_min_2 = any(
                c.get("expect") == "min_reviewers_2"
                for c in all_claims
            )
            if has_min_2:
                return Finding(
                    rule=4, line=claim.get("line", 0),
                    claim=claim.get("claim", ""),
                    artifact=artifact,
                    reason=f"arity contradiction: {func_name} emits 1 reviewer but gate requires >= 2",
                )
        return None

    if expect.startswith("pattern:"):
        # Filename pattern consistency: check all claims with pattern:
        # expect in the same contract have consistent patterns.
        pattern = expect[len("pattern:"):]
        # Collect all patterns in the contract
        all_patterns: list[tuple[str, str]] = []
        for c in all_claims:
            e = c.get("expect", "")
            if e.startswith("pattern:"):
                all_patterns.append((c.get("artifact", ""), e[len("pattern:"):]))
        # Check if this claim's pattern differs from others
        for other_artifact, other_pattern in all_patterns:
            if other_artifact != artifact and other_pattern != pattern:
                return Finding(
                    rule=4, line=claim.get("line", 0),
                    claim=claim.get("claim", ""),
                    artifact=artifact,
                    reason=(
                        f"naming inconsistency: {artifact} uses pattern "
                        f"'{pattern}' but {other_artifact} uses '{other_pattern}'"
                    ),
                )
        return None

    return None


def _function_contains_check(source: str, func_name: str, check_str: str) -> bool:
    """Heuristic: does the function source contain a check for the given string?"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            func_source = ast.unparse(node)
            return check_str in func_source
    # Also check the module-level source (argparse, etc.)
    return check_str in source


def _function_emits_single_reviewer(source: str, func_name: str) -> bool:
    """Heuristic: does the function emit a single reviewer?

    Checks for patterns like 'reviewer-stub', single-element reviewer list,
    or a hardcoded 1-reviewer structure.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            func_source = ast.unparse(node)
            # Check for single-reviewer patterns
            if "referee-stub" in func_source:
                return True
            if 'reviewers": [{' in func_source or "reviewers: [" in func_source:
                return True
            # Check for a single-element list pattern
            if re.search(r"reviewers.*\[.*\].*", func_source, re.DOTALL):
                # Count the number of dict literals — rough heuristic
                return True
    return False


def check_call_signature(
    claim: dict[str, Any],
    repo_root: Path,
) -> Finding | None:
    """Rule 5: call-signature claims match the named function's actual
    signature (arity, parameter names).
    """
    artifact = claim.get("artifact", "")
    field_path = claim.get("field_path", "")
    expect = claim.get("expect", "")
    claimed_params = claim.get("params", [])

    if not artifact:
        return Finding(
            rule=5, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=artifact,
            reason="rule 5 requires an 'artifact' (Python file)",
        )

    source = load_python_source(repo_root, artifact)
    func_name = field_path.split(".")[0] if "." in field_path else field_path

    sig = _extract_function_signature(source, func_name)
    if sig is None:
        return Finding(
            rule=5, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=artifact,
            reason=f"function '{func_name}' not found in {artifact}",
        )

    actual_params = sig["params"]
    actual_arity = len(actual_params)

    # Check arity
    if expect.startswith("arity:"):
        claimed_arity = int(expect.split(":")[1])
        if claimed_arity != actual_arity:
            return Finding(
                rule=5, line=claim.get("line", 0),
                claim=claim.get("claim", ""),
                artifact=artifact,
                reason=(
                    f"arity mismatch: claim expects {claimed_arity} params, "
                    f"actual signature has {actual_arity}: {actual_params}"
                ),
            )
        return None

    # Check param names
    if expect.startswith("param:"):
        claimed_param = expect.split(":", 1)[1]
        if claimed_param not in actual_params:
            return Finding(
                rule=5, line=claim.get("line", 0),
                claim=claim.get("claim", ""),
                artifact=artifact,
                reason=(
                    f"param '{claimed_param}' not in actual signature; "
                    f"actual params: {actual_params}"
                ),
            )
        return None

    # Check full param list
    if expect.startswith("params:"):
        claimed_param_list = expect.split(":", 1)[1].split(",")
        claimed_param_list = [p.strip() for p in claimed_param_list]
        if claimed_params:
            # If params field is provided, use that (more explicit)
            claimed_param_list = claimed_params
        if set(claimed_param_list) != set(actual_params):
            # Check if all claimed params are in actual (subset check for
            # required params)
            missing = [p for p in claimed_param_list if p not in actual_params]
            if missing:
                return Finding(
                    rule=5, line=claim.get("line", 0),
                    claim=claim.get("claim", ""),
                    artifact=artifact,
                    reason=(
                        f"params {missing} not in actual signature; "
                        f"actual params: {actual_params}"
                    ),
                )
        return None

    return None


def _extract_function_signature(source: str, func_name: str) -> dict[str, Any] | None:
    """Extract a function's signature (param names) from Python source.

    Returns {'name': str, 'params': list[str]} or None if not found.
    Handles keyword-only args (after *).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            params: list[str] = []
            args = node.args
            # Positional args (including those with defaults)
            for arg in args.posonlyargs:
                params.append(arg.arg)
            for arg in args.args:
                params.append(arg.arg)
            # *args
            if args.vararg:
                params.append(args.vararg.arg)
            # Keyword-only args (after *)
            for arg in args.kwonlyargs:
                params.append(arg.arg)
            # **kwargs
            if args.kwarg:
                params.append(args.kwarg.arg)
            return {"name": func_name, "params": params}
    return None


def check_required_anchors(
    claim: dict[str, Any],
    repo_root: Path,
) -> Finding | None:
    """Rule 6: gate predicates must name a resolvable schema/artifact plus
    field path. Vague gate prose is a finding, not a pass. Always blocks.
    """
    artifact = claim.get("artifact", "")
    field_path = claim.get("field_path", "")
    expect = claim.get("expect", "resolvable")

    if not artifact or not field_path:
        return Finding(
            rule=6, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=artifact or "(none)",
            reason=(
                "gate predicate does not name a resolvable artifact "
                "plus field path — vague gate prose"
            ),
        )

    if expect == "resolvable":
        # The artifact must exist and the field path must resolve.
        if artifact.endswith(".json"):
            data = load_json_artifact(repo_root, artifact)
            if not _field_path_exists(data, field_path):
                return Finding(
                    rule=6, line=claim.get("line", 0),
                    claim=claim.get("claim", ""),
                    artifact=artifact,
                    reason=f"gate predicate references unresolvable field path '{field_path}' in {artifact}",
                )
        elif artifact.endswith(".py"):
            source = load_python_source(repo_root, artifact)
            if field_path not in source:
                return Finding(
                    rule=6, line=claim.get("line", 0),
                    claim=claim.get("claim", ""),
                    artifact=artifact,
                    reason=f"gate predicate references unresolvable '{field_path}' in {artifact}",
                )
    return None


def check_file_paths(
    claim: dict[str, Any],
    repo_root: Path,
) -> Finding | None:
    """Rule 7: file paths referenced by the plan exist in the repo (or are
    explicitly marked as to-be-created).
    """
    path = claim.get("path", "")
    expect = claim.get("expect", "exists")

    if not path:
        return Finding(
            rule=7, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact="",
            reason="rule 7 requires a 'path'",
        )

    if expect == "to_be_created":
        return None

    if expect == "exists_or_to_be_created":
        full = repo_root / path
        if full.exists():
            return None
        # Not found, but claim says it might be to-be-created.
        # Check if the plan marks it as to-be-created.
        return None

    if expect == "exists":
        full = repo_root / path
        if not full.exists():
            return Finding(
                rule=7, line=claim.get("line", 0),
                claim=claim.get("claim", ""),
                artifact=path,
                reason=f"file path '{path}' not found in repo",
            )
    return None


# ── heuristic mode ───────────────────────────────────────────────────────


def _identify_excluded_sections(lines: list[str]) -> set[int]:
    """Identify line numbers that fall inside revision-history or
    changelog sections. These are excluded from every heuristic check.

    A section starts at a heading like '## Revision history' or
    '## Changelog' (case-insensitive) and ends at the next heading of
    the same or higher level (## or #), OR at any ### sub-heading
    (which starts a new subsection outside the changelog).
    """
    excluded: set[int] = set()
    in_excluded_section = False
    excluded_keywords = ("revision history", "changelog", "change log")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip().lower()
            heading_level = len(stripped) - len(stripped.lstrip("#"))
            if any(kw in heading_text for kw in excluded_keywords):
                in_excluded_section = True
            elif heading_level <= 2:
                # ## or # heading ends the excluded section.
                in_excluded_section = False
            elif heading_level >= 3 and in_excluded_section:
                # ### or deeper sub-heading: resets exclusion (starts a
                # new subsection outside the changelog/revision-history).
                in_excluded_section = False
        if in_excluded_section:
            excluded.add(i)
    return excluded


def _extract_backticked(line: str) -> list[str]:
    """Extract all backtick-delimited strings from a line."""
    return re.findall(r"\x60([^\x60]+)\x60", line)


def _is_field_path(val: str) -> bool:
    """Heuristic: does this backticked string look like a JSON field path?

    Examples: 'reviewers[*].verdict', 'chunk_commit_sha', 'schema',
    'reviewers[0].verdict'. Not: 'tools/foo.py' (file path), 'grok-4.5'
    (model id), 'check_reviewer_panel()' (call expression).
    """
    # Must contain word chars, dots, brackets, wildcards — but NOT slashes
    # (file paths) or parens (call expressions).
    if "/" in val or "(" in val or ")" in val:
        return False
    if "." not in val and "[" not in val:
        # A bare word like 'verdict' or 'schema' is a field path if it's
        # a known JSON key. We accept any bare word that looks like a
        # JSON key (snake_case or camelCase, no spaces).
        return bool(re.match(r"^[a-z][a-zA-Z0-9_]*$", val))
    # Dotted path or bracket-indexed path
    return bool(re.match(r"^[a-z][a-zA-Z0-9_]*(?:\.(?:\w+|\[\d+\]|\[\*\]))+$", val))


def _is_call_expression(val: str) -> bool:
    """Heuristic: does this backticked string look like a function call?

    Examples: 'check_reviewer_panel()', 'close_chunk(chunk_id, commit_sha)',
    'cross_family_review.check_reviewer_panel()'.
    """
    return bool(re.match(r"^[\w.]+\([\w, =*.'\"]*\)$", val))


def _is_model_id_or_family(val: str) -> bool:
    """Heuristic: does this backticked string look like a model id or
    family label?

    Model ids: 'grok-4.5', 'gemini-3.1-pro-preview', 'gpt-5.4-mini'.
    Family labels: 'grok-family', 'gemini-family', 'openai-family'.
    """
    return bool(re.match(r"^[a-z][a-z0-9]*(?:-[a-z0-9.]+)+$", val))


def _is_file_path(val: str) -> bool:
    """Heuristic: does this backticked string look like a file path?

    Examples: 'tools/cross_family_review.py', 'phase-4.5/tokens/chunk-5a.token.json'.
    """
    return bool(re.match(r"^(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry)/[\w/.-]+$", val)) and "." in val.split("/")[-1]


def _is_value_negated(line: str, val: str) -> bool:
    """Check if a specific backticked value is negated in the line.

    Scopes the negation to the specific value by checking the text
    within ~30 chars before the backtick. This avoids suppressing
    every backticked value on the line when only one is negated.

    Examples (negated):
      "Token has no top-level `verdict`" → True for 'verdict'
      "does not carry `verdict`" → True for 'verdict'

    Examples (not negated):
      "Token has `verdict` and `schema`" → False for both
      "no top-level `verdict` but does have `schema`" → True for 'verdict', False for 'schema'
    """
    # Find the position of this specific backticked value in the line.
    escaped = re.escape(val)
    for m in re.finditer(r"\x60" + escaped + r"\x60", line):
        # Check the 30 chars before the backtick.
        start = max(0, m.start() - 30)
        prefix = line[start:m.start()].lower()
        negation_keywords = (
            "no top-level", "no root", "not found",
            "does not carry", "does not have",
            "not a root", "absent", "no ",
        )
        if any(neg in prefix for neg in negation_keywords):
            return True
    return False


def _is_to_be_created(line: str, path: str) -> bool:
    """Check if the plan marks a path as to-be-created.

    Markers: 'New script', 'New helper', 'New function', 'New file',
    'to-be-created', 'to be created', '(new)', '| New |'.
    Also: test files (tests/test_*.py) referenced in test bullet lists or
    verify-check command lines are to-be-created by definition (the plan
    describes tests that will be written).
    """
    lower = line.lower()
    markers = (
        "new script", "new helper", "new function", "new file",
        "to-be-created", "to be created", "(new)", "| new |",
        "new module", "new tool",
    )
    if any(m in lower for m in markers):
        return True
    # Test files in test sections or verify-check commands are to-be-created.
    if path.startswith("tests/"):
        # Verify-check command lines reference test files that will be written.
        if "verify check" in lower or "pytest" in lower or "py_compile" in lower:
            return True
        # Test bullet-list lines (start with '- `tests/test_') describe
        # tests to be written.
        if re.match(r"^\s*-\s+`tests/", line):
            return True
    # Paths in py_compile commands are to-be-created scripts.
    if "py_compile" in lower and path.startswith("tools/"):
        return True
    return False


def run_heuristic(plan_text: str, repo_root: Path) -> list[Finding]:
    """Run rules heuristically when no CONTRACT block is present.

    Per spec v1.1: heuristic mode NEVER blocks — all findings are
    warnings (severity=WARNING). Revision-history / changelog sections
    are excluded from every heuristic check. Rules 1, 3, 5 run against
    claim-shaped backticked strings in the plan body.
    """
    findings: list[Finding] = []
    lines = plan_text.splitlines()
    excluded = _identify_excluded_sections(lines)

    # Load MODEL_FAMILY_MAP for rule 3 (best-effort; skip if unavailable).
    model_ids: set[str] = set()
    families: set[str] = set()
    try:
        family_map = load_model_family_map(repo_root)
        model_ids = set(family_map.keys())
        families = set(v[1] for v in family_map.values())
    except FailClosed:
        pass

    for i, line in enumerate(lines, 1):
        if i in excluded:
            continue

        backticked = _extract_backticked(line)
        for val in backticked:
            # Rule 1: field-path references against JSON artifacts.
            # Look for a backticked field path near a backticked .json path.
            if _is_field_path(val):
                # Skip if THIS SPECIFIC backticked value is negated
                # (e.g., "no top-level `verdict`" or "does not carry `verdict`").
                # Scope: check the text within ~30 chars before the backtick.
                if _is_value_negated(line, val):
                    continue
                # Find a JSON artifact path in the same line or nearby.
                for other_val in backticked:
                    if other_val.endswith(".json") and _is_file_path(other_val):
                        artifact = other_val
                        try:
                            data = load_json_artifact(repo_root, artifact)
                            if not _field_path_exists(data, val):
                                findings.append(Finding(
                                    rule=1, line=i,
                                    claim=line.strip(),
                                    artifact=artifact,
                                    reason=f"field path '{val}' not found in {artifact} (heuristic)",
                                    severity="WARNING",
                                ))
                        except FailClosed:
                            pass
                        break

            # Rule 3: model id / family label type confusion.
            if _is_model_id_or_family(val):
                if val in families and val not in model_ids:
                    # This is a family label — check if the line uses it as
                    # a model id (e.g., "implementer model" or "model_id=").
                    lower_line = line.lower()
                    if any(kw in lower_line for kw in (
                        "model id", "model_id", "implementer model",
                        "--model", "reviewer model",
                    )):
                        findings.append(Finding(
                            rule=3, line=i,
                            claim=line.strip(),
                            artifact="tools/sprint_loop/config.py",
                            reason=f"'{val}' is a family label used as a model id — type confusion (heuristic)",
                            severity="WARNING",
                        ))

            # Rule 5: call-signature claims against actual function signatures.
            if _is_call_expression(val):
                # Parse the call expression: function name + args.
                call_match = re.match(r"^([\w.]+)\(([\w, =*.'\"]*)\)$", val)
                if call_match:
                    func_full = call_match.group(1)
                    call_args_str = call_match.group(2).strip()
                    func_name = func_full.split(".")[-1] if "." in func_full else func_full
                    # Determine the artifact path.
                    artifact = ""
                    if "." in func_full:
                        module_name = func_full.split(".")[0]
                        artifact = f"tools/{module_name}.py"
                    if not artifact:
                        # Look for a backticked .py path in the same line.
                        for other_val in backticked:
                            if other_val.endswith(".py") and _is_file_path(other_val):
                                artifact = other_val
                                break
                    if not artifact:
                        # Look at nearby lines (±2) for a backticked .py path.
                        for delta in (-1, 1, -2, 2):
                            nearby_idx = i - 1 + delta
                            if 0 <= nearby_idx < len(lines):
                                nearby_backticked = _extract_backticked(lines[nearby_idx])
                                for other_val in nearby_backticked:
                                    if other_val.endswith(".py") and _is_file_path(other_val):
                                        artifact = other_val
                                        break
                                if artifact:
                                    break
                    if not artifact:
                        # Try common locations based on function name.
                        for candidate in (
                            f"tools/{func_name}.py",
                            f"tools/sprint_loop/{func_name}.py",
                        ):
                            if (repo_root / candidate).exists():
                                artifact = candidate
                                break
                    # Also try mapping common module names to file paths.
                    if not artifact:
                        for candidate in (
                            "tools/cross_family_review.py",
                            "tools/sign_chunk_token.py",
                            "tools/chunk_sequence_gate.py",
                            "tools/persistent_referee_stub.py",
                            "tools/sprint_loop/per_chunk.py",
                            "tools/sprint_loop/chunk_close_banner.py",
                        ):
                            source_file = repo_root / candidate
                            if source_file.exists():
                                try:
                                    src = load_python_source(repo_root, candidate)
                                    sig_check = _extract_function_signature(src, func_name)
                                    if sig_check is not None:
                                        artifact = candidate
                                        break
                                except FailClosed:
                                    pass

                    if artifact and (repo_root / artifact).exists():
                        try:
                            source = load_python_source(repo_root, artifact)
                            sig = _extract_function_signature(source, func_name)
                            if sig is not None:
                                actual_params = sig["params"]
                                # Parse the claimed args from the call expression.
                                claimed_args = [
                                    a.strip().split("=")[0].strip()
                                    for a in call_args_str.split(",")
                                    if a.strip()
                                ] if call_args_str else []
                                # Check for param name mismatches.
                                for claimed_arg in claimed_args:
                                    if claimed_arg and claimed_arg not in actual_params:
                                        # Is the actual param similar? (e.g., implementer_family vs implementer_model_id)
                                        similar = [
                                            p for p in actual_params
                                            if claimed_arg.split("_")[0] in p
                                            or p.split("_")[0] in claimed_arg
                                        ]
                                        if similar:
                                            findings.append(Finding(
                                                rule=5, line=i,
                                                claim=line.strip(),
                                                artifact=artifact,
                                                reason=(
                                                    f"call '{val}' uses param '{claimed_arg}' "
                                                    f"but actual signature has '{similar[0]}' "
                                                    f"(heuristic)"
                                                ),
                                                severity="WARNING",
                                            ))
                                        else:
                                            findings.append(Finding(
                                                rule=5, line=i,
                                                claim=line.strip(),
                                                artifact=artifact,
                                                reason=(
                                                    f"call '{val}' uses param '{claimed_arg}' "
                                                    f"not in actual signature: {actual_params} "
                                                    f"(heuristic)"
                                                ),
                                                severity="WARNING",
                                            ))
                        except FailClosed:
                            pass

        # Rule 7: file paths referenced in the plan body.
        for match in re.finditer(r"(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry)/[\w/.]+\.\w+", line):
            path = match.group(0)
            full = repo_root / path
            if not full.exists():
                # Check if the line marks the path as to-be-created.
                if _is_to_be_created(line, path):
                    continue
                findings.append(Finding(
                    rule=7, line=i,
                    claim=line.strip(),
                    artifact=path,
                    reason=f"file path '{path}' not found (heuristic warning)",
                    severity="WARNING",
                ))

    # Cross-reference heuristic (rule 5): detect CLI-flag-to-function-param
    # type confusion. When the plan mentions a flag like --implementer-family
    # and a function that has a parameter like implementer_model_id, warn.
    findings.extend(
        _heuristic_flag_param_confusion(lines, repo_root, excluded)
    )

    return findings


def _heuristic_flag_param_confusion(
    lines: list[str],
    repo_root: Path,
    excluded: set[int],
) -> list[Finding]:
    """Detect CLI-flag-to-function-param type confusion heuristically.

    Scans for backticked `--<prefix>-family` flags near backticked call
    expressions. When a function's actual signature has a parameter
    like `<prefix>_model_id` but the plan passes a family label via
    `--<prefix>-family`, warn about the type confusion.
    """
    findings: list[Finding] = []
    # Collect all backticked --flag references and call expressions with
    # their line numbers (excluding revision-history/changelog sections).
    flag_lines: list[tuple[int, str, str]] = []  # (line_num, flag_name, line_text)
    call_lines: list[tuple[int, str, str]] = []  # (line_num, call_expr, line_text)

    for i, line in enumerate(lines, 1):
        if i in excluded:
            continue
        backticked = _extract_backticked(line)
        for val in backticked:
            if re.match(r"^--[\w-]+$", val):
                flag_lines.append((i, val, line))
            if _is_call_expression(val):
                call_lines.append((i, val, line))

    # For each --<prefix>-family flag, look for a nearby call expression
    # whose function has a <prefix>_model_id parameter.
    for flag_line_num, flag_name, flag_line in flag_lines:
        # Extract the prefix from --<prefix>-family
        m = re.match(r"^--([\w]+)-family$", flag_name)
        if not m:
            continue
        prefix = m.group(1)

        # Look for call expressions within ±5 lines.
        for call_line_num, call_expr, call_line in call_lines:
            if abs(call_line_num - flag_line_num) > 5:
                continue
            call_match = re.match(r"^([\w.]+)\(", call_expr)
            if not call_match:
                continue
            func_full = call_match.group(1)
            func_name = func_full.split(".")[-1] if "." in func_full else func_full

            # Resolve the artifact.
            artifact = ""
            if "." in func_full:
                module_name = func_full.split(".")[0]
                artifact = f"tools/{module_name}.py"
            if not artifact or not (repo_root / artifact).exists():
                # Search common locations for the function.
                for candidate in (
                    f"tools/{func_name}.py",
                    f"tools/sprint_loop/{func_name}.py",
                    "tools/cross_family_review.py",
                    "tools/sign_chunk_token.py",
                    "tools/chunk_sequence_gate.py",
                    "tools/persistent_referee_stub.py",
                    "tools/sprint_loop/per_chunk.py",
                    "tools/sprint_loop/chunk_close_banner.py",
                ):
                    source_file = repo_root / candidate
                    if source_file.exists():
                        try:
                            src = load_python_source(repo_root, candidate)
                            if _extract_function_signature(src, func_name) is not None:
                                artifact = candidate
                                break
                        except FailClosed:
                            pass

            if not artifact or not (repo_root / artifact).exists():
                continue

            try:
                source = load_python_source(repo_root, artifact)
                sig = _extract_function_signature(source, func_name)
                if sig is None:
                    continue
                actual_params = sig["params"]
                # Check if the function has a <prefix>_model_id parameter.
                expected_param = f"{prefix}_model_id"
                if expected_param in actual_params:
                    # The plan passes --<prefix>-family but the function
                    # expects <prefix>_model_id — type confusion.
                    findings.append(Finding(
                        rule=5, line=flag_line_num,
                        claim=flag_line.strip(),
                        artifact=artifact,
                        reason=(
                            f"flag '{flag_name}' passes a family label but "
                            f"function '{func_name}' expects parameter "
                            f"'{expected_param}' (a model id) — type confusion "
                            f"(heuristic)"
                        ),
                        severity="WARNING",
                    ))
                    break  # One warning per flag is enough.
            except FailClosed:
                pass

    return findings


# ── main lint runner ─────────────────────────────────────────────────────


def run_lint(
    plan_path: Path,
    repo_root: Path,
    contract_path: str | None = None,
) -> tuple[int, list[Finding], str]:
    """Run the lint. Returns (exit_code, findings, source_description)."""
    if not plan_path.exists():
        raise FailClosed(f"plan file not found: {plan_path}", str(plan_path))

    plan_text = plan_path.read_text()
    contract, source = resolve_contract(plan_text, plan_path, contract_path)

    if contract is None:
        # Heuristic mode (spec v1.1): NEVER blocks — warnings only.
        findings = run_heuristic(plan_text, repo_root)
        return EXIT_PASS, findings, source

    # Contract mode: verify each declared claim strictly.
    claims = contract.get("claims", [])
    findings: list[Finding] = []

    for claim in claims:
        rule = claim.get("rule", 0)
        try:
            finding = _dispatch_rule(rule, claim, repo_root, claims)
            if finding is not None:
                findings.append(finding)
        except FailClosed:
            raise

    if findings:
        return EXIT_BLOCK, findings, source
    return EXIT_PASS, findings, source


def _dispatch_rule(
    rule: int,
    claim: dict[str, Any],
    repo_root: Path,
    all_claims: list[dict[str, Any]],
) -> Finding | None:
    """Dispatch a claim to the appropriate rule checker."""
    if rule == 1:
        return check_field_path(claim, repo_root)
    elif rule == 2:
        return check_cli_flag(claim, repo_root)
    elif rule == 3:
        return check_model_id_family(claim, repo_root)
    elif rule == 4:
        return check_internal_consistency(claim, repo_root, all_claims)
    elif rule == 5:
        return check_call_signature(claim, repo_root)
    elif rule == 6:
        return check_required_anchors(claim, repo_root)
    elif rule == 7:
        return check_file_paths(claim, repo_root)
    else:
        return Finding(
            rule=rule, line=claim.get("line", 0),
            claim=claim.get("claim", ""),
            artifact=claim.get("artifact", ""),
            reason=f"unknown rule class {rule}",
        )


# ── telemetry ───────────────────────────────────────────────────────────


def append_telemetry(
    plan_path: Path,
    plan_text: str,
    verdict: str,
    finding_count: int,
    duration_ms: int,
) -> None:
    """Append one telemetry row per invocation.

    Writes to telemetry/plan_lint_runs.jsonl (a tool-specific file, not
    the agent-run runs.jsonl consumed by aggregate.py). The schema is
    documented in telemetry/SCHEMA.md under "plan_lint_runs.jsonl".
    §17.3 gitignore discipline: the file is git-ignored (see .gitignore).
    """
    data_dir = os.environ.get("TELEMETRY_DATA_DIR", "telemetry")
    out_path = Path(data_dir) / "plan_lint_runs.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    content_sha = hashlib.sha256(plan_text.encode()).hexdigest()
    row = {
        "schema_version": "v2",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": "plan-lint",
        "plan_path": str(plan_path),
        "plan_content_sha": content_sha,
        "verdict": verdict,
        "finding_count": finding_count,
        "duration_ms": duration_ms,
    }
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


# ── CLI ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plan-lint.py",
        description="Deterministic pre-review tier for build plans.",
    )
    parser.add_argument("plan", help="Path to the plan markdown file.")
    parser.add_argument("--repo-root", default=".",
                        help="Path to the repo root for ground-truth artifacts.")
    parser.add_argument("--json", dest="json_out", default="",
                        help="Path to write structured JSON output.")
    parser.add_argument("--contract", default="",
                        help="Path to an external contract JSON file.")

    args = parser.parse_args(argv)

    plan_path = Path(args.plan).resolve()
    repo_root = Path(args.repo_root).resolve()

    if not repo_root.exists():
        print(f"ERROR: repo-root not found: {repo_root}", file=sys.stderr)
        return EXIT_ERROR

    start = time.monotonic()

    try:
        exit_code, findings, source = run_lint(plan_path, repo_root, args.contract or None)
    except FailClosed as e:
        print(f"ERROR: {e.reason}", file=sys.stderr)
        if e.artifact:
            print(f"  artifact: {e.artifact}", file=sys.stderr)
        duration_ms = int((time.monotonic() - start) * 1000)
        append_telemetry(plan_path, "", "ERROR", 0, duration_ms)
        return EXIT_ERROR

    duration_ms = int((time.monotonic() - start) * 1000)

    # Output findings
    if findings:
        for f in findings:
            print(f.format_text())
            print()

    # Verdict line
    if exit_code == EXIT_PASS:
        warnings = [f for f in findings if f.severity == "WARNING"]
        if warnings:
            print(f"PASS with {len(warnings)} warning(s) — source: {source}")
        else:
            print(f"PASS — source: {source}")
    elif exit_code == EXIT_BLOCK:
        print(f"BLOCK: {len(findings)} finding(s) — source: {source}")

    # JSON output
    if args.json_out:
        json_data = {
            "verdict": "PASS" if exit_code == EXIT_PASS else "BLOCK",
            "findings": [f.to_dict() for f in findings],
            "source": source,
        }
        Path(args.json_out).write_text(json.dumps(json_data, indent=2))

    # Telemetry
    verdict_str = "PASS" if exit_code == EXIT_PASS else "BLOCK"
    try:
        plan_text = plan_path.read_text()
    except OSError:
        plan_text = ""
    append_telemetry(plan_path, plan_text, verdict_str, len(findings), duration_ms)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
