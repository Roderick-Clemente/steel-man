"""Config dataclass + parsers for the sprint loop.

The CLI takes flags + an optional JSON file. The JSON file is the
preferred human-maintained surface — it lives next to a pilot spec so
re-runs are reproducible (OPERATING-RULES §9: scripted, not manual).

The dataclass is the truth source. CLI/JSON parsers fill it. The runner
never reads a CLI flag or JSON key directly — everything goes through
``build_config``.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

# Make ``tools/`` importable as a package root so ``from sprint_loop...``
# resolves when invoked from anywhere. This matches the convention in
# ``tools/orchestrate-review.py`` (it does the same sys.path.insert).
_TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.state import (  # noqa: E402
    DEFAULT_ENABLED_TOOLS,
    Role,
    RoleAssignment,
)


# ── defaults ─────────────────────────────────────────────────────────────

DEFAULT_PLAN_REVIEWER = "grok-4.5"           # xAI family
DEFAULT_PLAN_REVIEWER_2 = "gemini-3.1-pro-preview"  # google family
DEFAULT_TEST_DESIGNER = "claude-opus-5"       # anthropic family
DEFAULT_EXECUTOR = "gpt-5.4-mini"            # openai family (cheap tier, §17.1 allowed)
DEFAULT_VALIDATORS = ["grok-4.5", "gemini-3.1-pro-preview"]

# Standing family map per tools/conventions/model-discipline.md
MODEL_FAMILY_MAP: dict[str, tuple[str, str]] = {
    # model_id: (provider, family)
    "claude-opus-5":       ("anthropic", "claude-family"),
    "claude-opus-4-8":     ("anthropic", "claude-family"),
    "gpt-5.4-mini":        ("openai", "openai-family"),
    "gpt-5.2":             ("openai", "openai-family"),
    "grok-4.5":            ("xai", "grok-family"),
    "gemini-3.1-pro-preview": ("google", "gemini-family"),
    "gemini-2.5-pro":      ("google", "gemini-family"),
    "glm-5.2":             ("zhipu", "glm-family"),
}


@dataclass
class Config:
    """All configurable knobs of the loop runner.

    CLI: ``python3 tools/sprint-loop.py --config <cfg.json> [overrides]``
    JSON: see ``examples/sprint-loop-config.json`` for the schema.

    The config dataclass is also serialised as the *initial*
    ``RunState`` for pause/resume.
    """

    # Required paths
    framework_root: str = ""
    pilot_root: str = ""
    pilot_python: str = ""

    # Optional paths
    config_path: str = ""                  # where this config was loaded from
    chunks_file: str = ""                  # path to chunks JSON (Phase 4.5.4)
    review_prompt_template: str = ""       # path to review-prompt template
    locked_test_locks_dir: str = ""        # defaults to phase-1/locks/
    evidence_output_dir: str = ""          # defaults to phase-4.5/build-evidence/<run-id>/
    security_allowlist: str = ""
    security_baseline: str = ""

    # Model assignments — see DEFAULT_* above for the standing picks.
    planner_model: str = "claude-opus-5"
    planner_auto_level: str = "medium"
    plan_reviewer_model: str = DEFAULT_PLAN_REVIEWER
    plan_reviewer_auto_level: str = "high"
    plan_reviewer_2_model: str = ""        # empty => single reviewer
    plan_reviewer_2_auto_level: str = "high"
    test_designer_model: str = DEFAULT_TEST_DESIGNER
    test_designer_auto_level: str = "medium"
    executor_model: str = DEFAULT_EXECUTOR
    executor_auto_level: str = "medium"

    # Validator panel — list of "model_id:provider:family[:label]" entries.
    validators: list[str] = field(default_factory=lambda: list(DEFAULT_VALIDATORS))
    validator_auto_level: str = "high"

    # Tuning
    max_review_rounds: int = 2
    retry_threshold: int = 1
    max_auto_retries: int = 2
    retry_delay_seconds: int = 5

    # CLI behaviour
    dry_run: bool = False
    skip_reconcile: bool = False
    create_pr: bool = False
    validation_backend: str = "local"
    signing_key_env: str = "EVIDENCE_SIGNING_KEY"

    # §17.6 outage override (must be recorded in phase-N/KNOWN-ISSUES.md)
    allow_test_author_collide: bool = False
    allow_single_family: bool = False

    # Optional input: pilot spec the planner reads from (free-form).
    pilot_spec_file: str = ""

    # Per the Operating Rules: prevent silent degradation. If True, on any
    # §7 reality-assertion failure the runner stops rather than guessing.
    fail_closed: bool = True

    # ── helpers ─────────────────────────────────────────────────────────

    def provider_family(self, model_id: str) -> tuple[str, str]:
        """Look up (provider, family) for a model id."""
        if model_id in MODEL_FAMILY_MAP:
            return MODEL_FAMILY_MAP[model_id]
        # Unknown model: refuse to fabricate (PRD §4 — provenance is curated, not inferred)
        return ("unknown", "unknown")

    def default_locks_dir(self) -> str:
        if self.locked_test_locks_dir:
            return self.locked_test_locks_dir
        return os.path.join(self.framework_root, "phase-1", "locks")

    def default_evidence_dir(self, run_id: str) -> str:
        if self.evidence_output_dir:
            return self.evidence_output_dir
        return os.path.join(self.framework_root, "phase-4.5", "build-evidence", run_id)

    def to_role_assignments(self) -> list[RoleAssignment]:
        """Materialise Config into the ``RoleAssignment`` shapes ``state.RunState`` stores."""
        out: list[RoleAssignment] = []
        pm, pfam = self.provider_family(self.planner_model)
        # Don't auto-fill provider family if planner is --auto (no model pinned);
        # the FamilyGuard re-runs post-resolution.
        out.append(RoleAssignment(
            role=Role.PLANNER,
            pinned_model_id=self.planner_model,
            pinned_family=pfam,
            pinned_provider=pm,
            auto_level=self.planner_auto_level or "medium",
            enabled_tools=DEFAULT_ENABLED_TOOLS[Role.PLANNER],
        ))

        prm, prf = self.provider_family(self.plan_reviewer_model)
        out.append(RoleAssignment(
            role=Role.PLAN_REVIEWER,
            pinned_model_id=self.plan_reviewer_model,
            pinned_family=prf,
            pinned_provider=prm,
            auto_level=self.plan_reviewer_auto_level or "high",
            enabled_tools=DEFAULT_ENABLED_TOOLS[Role.PLAN_REVIEWER],
        ))

        if self.plan_reviewer_2_model:
            pr2m, pr2f = self.provider_family(self.plan_reviewer_2_model)
            out.append(RoleAssignment(
                role=Role.PLAN_REVIEWER,  # same enum value; list-based deduplication in guard
                pinned_model_id=self.plan_reviewer_2_model,
                pinned_family=pr2f,
                pinned_provider=pr2m,
                auto_level=self.plan_reviewer_2_auto_level or "high",
                enabled_tools=DEFAULT_ENABLED_TOOLS[Role.PLAN_REVIEWER],
            ))

        tdm, tdf = self.provider_family(self.test_designer_model)
        out.append(RoleAssignment(
            role=Role.TEST_DESIGNER,
            pinned_model_id=self.test_designer_model,
            pinned_family=tdf,
            pinned_provider=tdm,
            auto_level=self.test_designer_auto_level or "medium",
            enabled_tools=DEFAULT_ENABLED_TOOLS[Role.TEST_DESIGNER],
        ))

        em, ef = self.provider_family(self.executor_model)
        out.append(RoleAssignment(
            role=Role.EXECUTOR,
            pinned_model_id=self.executor_model,
            pinned_family=ef,
            pinned_provider=em,
            auto_level=self.executor_auto_level or "medium",
            enabled_tools=DEFAULT_ENABLED_TOOLS[Role.EXECUTOR],
        ))

        # Validators come from the comma-separated list. Each entry is
        # model_id:provider:family[:label]; if provider/family are
        # missing, the family map fills them in.
        for entry in self.validators:
            parts = entry.strip().split(":")
            model_id = parts[0]
            provider = parts[1] if len(parts) > 1 else self.provider_family(model_id)[0]
            family = parts[2] if len(parts) > 2 else self.provider_family(model_id)[1]
            label = parts[3] if len(parts) > 3 else model_id
            out.append(RoleAssignment(
                role=Role.VALIDATOR,
                pinned_model_id=model_id,
                pinned_family=family,
                pinned_provider=provider,
                auto_level=self.validator_auto_level or "high",
                enabled_tools=DEFAULT_ENABLED_TOOLS[Role.VALIDATOR],
            ))

        return out

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ── parsers ──────────────────────────────────────────────────────────────

def build_config(argv: list[str] | None = None,
                 config_path_override: str | None = None) -> Config:
    """Build a Config from argv + (optional) JSON file.

    The JSON file is the canonical surface; CLI flags override specific
    keys for ad-hoc runs. Unknown JSON keys are *warned* (logged) but not
    rejected — forward-compatibility for additive schema changes.

    Returns a Config. Does not mutate outside ``Config``.
    """
    parser = argparse.ArgumentParser(
        prog="sprint-loop.py",
        description="Phase 4.5 sprint-loop runner — adversarial-sprint for Factory.",
    )
    parser.add_argument("--config", help="Path to JSON config file. Other flags override fields here.")
    parser.add_argument("--framework-root", default="",
                        help="Path to adversarial-sprint-dev (the loop runner's repo).")
    parser.add_argument("--pilot-root", default="",
                        help="Path to the pilot repo (e.g., quantum-bank--llms-txt-pilot).")
    parser.add_argument("--pilot-python", default="",
                        help="Python interpreter in the pilot venv (e.g., .venv/bin/python).")

    parser.add_argument("--chunks-file", default="",
                        help="JSON file with a list of chunk specs. If missing and "
                             "planner is run, the planner writes plan.md and chunking must "
                             "be driven by a subsequent --chunks-file pass.")

    parser.add_argument("--pilot-spec-file", default="",
                        help="Path to the pilot spec the planner reads (free-form markdown).")
    parser.add_argument("--review-prompt-template", default="",
                        help="Path to the review-prompt template (default: tools/sprint_loop/prompts/validator.md).")

    parser.add_argument("--planner-model", default="")
    parser.add_argument("--plan-reviewer-model", default="")
    parser.add_argument("--plan-reviewer-2-model", default="")
    parser.add_argument("--test-designer-model", default="")
    parser.add_argument("--executor-model", default="")
    parser.add_argument("--validators", default="",
                        help="Comma-separated model_ids (each may carry :provider:family:label).")

    parser.add_argument("--max-review-rounds", type=int, default=-1)
    parser.add_argument("--retry-threshold", type=int, default=-1)
    parser.add_argument("--max-auto-retries", type=int, default=-1)
    parser.add_argument("--retry-delay-seconds", type=int, default=-1)

    parser.add_argument("--dry-run", action="store_true",
                        help="Do not invoke droid exec or git commit; record planned actions.")
    parser.add_argument("--skip-reconcile", action="store_true",
                        help="Skip the human reconciliation gate (operator accepts ad-hoc).")
    parser.add_argument("--create-pr", action="store_true",
                        help="Attempt PR creation if the remote is configured. Default off — human gates merge per invariant #8.")
    parser.add_argument("--validation-backend", default="",
                        choices=["", "local", "ci"],
                        help="Track B backend. 'local' shells out to tools/orchestrate-review.py. 'ci' is a STUB per the Phase 4.5 prompt.")
    parser.add_argument("--signing-key-env", default="")

    parser.add_argument("--allow-test-author-collide", action="store_true",
                        help="§17.6 outage override only. Must be recorded in phase-N/KNOWN-ISSUES.md.")
    parser.add_argument("--allow-single-family", action="store_true",
                        help="Allow single-family validator panel. Mirrors orchestrate-review.py --allow-single-family. Use only with §17.6 fallback.")
    parser.add_argument("--fail-closed", dest="fail_closed", action="store_true", default=True)
    parser.add_argument("--no-fail-closed", dest="fail_closed", action="store_false",
                        help="Disable §7 fail-closed on reality-assertion failures. NOT recommended.")

    parser.add_argument("--security-allowlist", default="")
    parser.add_argument("--security-baseline", default="")

    args = parser.parse_args(argv)

    cfg = Config()
    cfg.config_path = config_path_override or args.config or ""

    # 1. Load JSON first (if present)
    if cfg.config_path:
        cfg = _merge_from_json(cfg, cfg.config_path)

    # 2. CLI overrides (only when flag is non-default / non-empty)
    overrides: dict[str, Any] = {
        "framework_root": args.framework_root,
        "pilot_root": args.pilot_root,
        "pilot_python": args.pilot_python,
        "chunks_file": args.chunks_file,
        "pilot_spec_file": args.pilot_spec_file,
        "review_prompt_template": args.review_prompt_template,
        "planner_model": args.planner_model,
        "plan_reviewer_model": args.plan_reviewer_model,
        "plan_reviewer_2_model": args.plan_reviewer_2_model,
        "test_designer_model": args.test_designer_model,
        "executor_model": args.executor_model,
        "validators": _parse_validators(args.validators) if args.validators else None,
        "validation_backend": args.validation_backend,
        "signing_key_env": args.signing_key_env,
        "security_allowlist": args.security_allowlist,
        "security_baseline": args.security_baseline,
    }
    for k, v in overrides.items():
        if v:  # empty string is "not set" for strings
            setattr(cfg, k, v)

    if args.max_review_rounds >= 0:
        cfg.max_review_rounds = args.max_review_rounds
    if args.retry_threshold >= 0:
        cfg.retry_threshold = args.retry_threshold
    if args.max_auto_retries >= 0:
        cfg.max_auto_retries = args.max_auto_retries
    if args.retry_delay_seconds >= 0:
        cfg.retry_delay_seconds = args.retry_delay_seconds

    if args.dry_run:
        cfg.dry_run = True
    if args.skip_reconcile:
        cfg.skip_reconcile = True
    if args.create_pr:
        cfg.create_pr = True
    if args.allow_test_author_collide:
        cfg.allow_test_author_collide = True
    if args.allow_single_family:
        cfg.allow_single_family = True
    cfg.fail_closed = args.fail_closed

    _validate_config(cfg)
    return cfg


def _parse_validators(s: str) -> list[str]:
    """Parse `--validators grok-4.5,gemini-3.1-pro-preview` into a list."""
    return [v.strip() for v in s.split(",") if v.strip()]


def _merge_from_json(cfg: Config, path: str) -> Config:
    """Overlay JSON keys onto Config; warn on unknown keys; raise on bad value types.

    Unknown keys are collected and the runner emits them as a warning at
    startup (caller does the log). The rationale: an additive schema
    bump should not break old configs that lacked the new field;
    removing a field should fail loudly.
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"ERROR: cannot load config {path}: {e}")

    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} must be a JSON object at the top level")

    known = {f.name for f in dataclasses.fields(Config)}
    unknown = sorted(set(data.keys()) - known)
    if unknown:
        # Warn but continue — see rationale above.
        print(f"WARNING: {path} has unknown keys (ignored): {unknown}", file=sys.stderr)

    for k, v in data.items():
        if k in known:
            current = getattr(cfg, k)
            # Type check: handled by dataclass types, but a brief sanity check helps.
            if not _safe_type_match(current, v):
                raise SystemExit(
                    f"ERROR: {path} key {k!r} has wrong type: expected "
                    f"{type(current).__name__}, got {type(v).__name__}"
                )
            setattr(cfg, k, v)

    return cfg


def _safe_type_match(current: Any, value: Any) -> bool:
    """Coarse type check for Config dataclass fields."""
    if isinstance(current, bool):
        return isinstance(value, bool)
    if isinstance(current, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(current, str):
        return isinstance(value, str)
    if isinstance(current, list):
        return isinstance(value, list)
    return True  # unknown field type — accept


def _validate_config(cfg: Config) -> None:
    """Run-time validation of cross-field constraints."""

    if not cfg.framework_root:
        raise SystemExit("ERROR: --framework-root is required (or set framework_root in --config)")
    if not cfg.pilot_root:
        raise SystemExit("ERROR: --pilot-root is required (or set pilot_root in --config)")
    if not cfg.pilot_python:
        # Default to the system python3; the operator may pin via --pilot-python
        cfg.pilot_python = sys.executable
        print(f"NOTE: --pilot-python not set, defaulting to {cfg.pilot_python}", file=sys.stderr)

    if cfg.framework_root and not os.path.isdir(os.path.join(cfg.framework_root, "tools", "sprint_loop")):
        raise SystemExit(
            f"ERROR: framework_root {cfg.framework_root} does not contain "
            f"tools/sprint_loop/. Are you sure this is the adversarial-sprint-dev repo?"
        )

    if not cfg.validators:
        raise SystemExit("ERROR: at least one validator must be configured (PRD §17.2 needs a cross-family panel)")
    if cfg.max_review_rounds < 1:
        raise SystemExit("ERROR: --max-review-rounds must be >= 1 (PRD §5.3)")
    if cfg.retry_threshold < 0:
        raise SystemExit("ERROR: --retry-threshold must be >= 0")
    if cfg.max_auto_retries < 0:
        raise SystemExit("ERROR: --max-auto-retries must be >= 0")
    if cfg.retry_delay_seconds < 0:
        raise SystemExit("ERROR: --retry-delay-seconds must be >= 0")
    if cfg.validation_backend not in ("local", "ci"):
        raise SystemExit(f"ERROR: --validation-backend must be 'local' or 'ci' (got {cfg.validation_backend!r})")
