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
        return (
            f"[BLOCK] rule={self.rule} ({self.rule_name}) line={self.line}\n"
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
    """Resolve the contract source: --contract flag > embedded block >
    companion <plan>.contract.json file.

    Returns (contract_dict_or_None, source_description).
    """
    if contract_flag:
        return load_contract_file(contract_flag), f"--contract {contract_flag}"

    embedded = extract_contract_from_plan(plan_text)
    if embedded is not None:
        return embedded, "embedded CONTRACT block"

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


def run_heuristic(plan_text: str, repo_root: Path) -> list[Finding]:
    """Run rules heuristically when no CONTRACT block is present.

    Per spec: all rules run as warnings (severity=WARNING), except
    rule 6 which always blocks. Returns findings.
    """
    findings: list[Finding] = []
    lines = plan_text.splitlines()

    # Rule 6 heuristic: look for gate-predicate prose without artifact refs.
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if any(kw in lower for kw in ("gate", "predicate", "verifies", "checks")):
            # Check if this line names a resolvable artifact + field path.
            if not re.search(r"[\w/]+\.(json|py)", line):
                findings.append(Finding(
                    rule=6, line=i,
                    claim=line.strip(),
                    artifact="(none)",
                    reason="gate predicate prose does not name a resolvable artifact",
                ))

    # Other rules in heuristic mode produce warnings only.
    # We scan for claim-shaped strings but do not block.
    for i, line in enumerate(lines, 1):
        # Rule 7 heuristic: referenced file paths
        for match in re.finditer(r"(?:tools|phase-\d)/[\w/.]+\.py", line):
            path = match.group(0)
            full = repo_root / path
            if not full.exists():
                findings.append(Finding(
                    rule=7, line=i,
                    claim=line.strip(),
                    artifact=path,
                    reason=f"file path '{path}' not found (heuristic warning)",
                    severity="WARNING",
                ))

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
        # Heuristic mode
        findings = run_heuristic(plan_text, repo_root)
        # In heuristic mode, only rule 6 blocks; others are warnings.
        blocks = [f for f in findings if f.severity == "BLOCK"]
        if blocks:
            return EXIT_BLOCK, findings, source
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

    Follows telemetry/SCHEMA.md conventions and §17.3 gitignore discipline.
    Writes to telemetry/runs.jsonl (already git-ignored per .gitignore)
    with tool="plan-lint" so rows are attributable without a new file
    that would need its own gitignore entry.
    """
    data_dir = os.environ.get("TELEMETRY_DATA_DIR", "telemetry")
    runs_path = Path(data_dir) / "runs.jsonl"
    runs_path.parent.mkdir(parents=True, exist_ok=True)

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
    with runs_path.open("a", encoding="utf-8") as f:
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
        if findings:
            print(f"PASS with {len(findings)} warning(s) — source: {source}")
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
