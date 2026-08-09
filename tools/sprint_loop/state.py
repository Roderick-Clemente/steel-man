"""Pure data-class state machine for the sprint loop.

No subprocess calls, no I/O side effects beyond writing/reading the
checkpoint JSON. This module is the truth source for the loop's states,
roles, and family-separation rules; everything else (orchestrator,
per-chunk inner loop, backends) reads from here.

The state model is intentionally narrow:

  ``RunState``       — one per ``sprint-loop.py`` invocation
  ``ChunkState``     — one per chunk within the run
  ``Role``           — enum of the five roles the loop coordinates
  ``FamilyGuard``    — pure-function check on family separation (PRD §17.2)

Other modules may serialise ``RunState`` to JSON for pause/resume, but only
this module owns the schema.
"""
from __future__ import annotations

import enum
import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


# ── roles ────────────────────────────────────────────────────────────────

class Role(str, enum.Enum):
    """The five roles the loop coordinates. Mirrors PRD §7.

    Strings are stable contract values written to
    ``telemetry/runs.jsonl:role`` (see ``telemetry/SCHEMA.md``). Do not
    rename without bumping the schema version.
    """
    PLANNER = "planner"
    PLAN_REVIEWER = "reviewer"
    TEST_DESIGNER = "test-designer"
    EXECUTOR = "executor"
    VALIDATOR = "validator"


# Seats where §17.2 separation binds. The planner and executor MAY use
# --auto (record resolved model + family); the reviewer and validator MUST
# be pinned to enforce the family invariant. Test-designer's seat
# separation is invariant #1 with executor per PRD §17.6.
SEPARATION_BINDING_ROLES: frozenset[Role] = frozenset({
    Role.PLAN_REVIEWER,
    Role.TEST_DESIGNER,
    Role.VALIDATOR,
})

# Per-role default --enabled-tools allowlists (PRD §17.5).
DEFAULT_ENABLED_TOOLS: dict[Role, str] = {
    Role.PLANNER:         "Read,Glob,Grep,LS,Execute",
    Role.PLAN_REVIEWER:   "Read,Glob,Grep,LS,Execute",
    Role.TEST_DESIGNER:   "Read,Glob,Grep,LS,Edit,Create,ApplyPatch,MultiEdit,Execute",
    Role.EXECUTOR:        "Read,Glob,Grep,LS,Edit,Create,ApplyPatch,MultiEdit,Execute",
    Role.VALIDATOR:       "Read,Glob,Grep,LS,Execute",
}


# ── run-level status ─────────────────────────────────────────────────────

class RunStatus(str, enum.Enum):
    """The run-level status field.

    Status is what the operator sees on stdout; the per-chunk
    ``ChunkStatus`` is what controls flow control.
    """
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    PLAN_REVIEWING = "PLAN_REVIEWING"
    AWAITING_RECONCILIATION = "AWAITING_RECONCILIATION"   # human gate
    CHUNKING = "CHUNKING"
    CHUNKING_DONE = "CHUNKING_DONE"
    RUNNING_CHUNKS = "RUNNING_CHUNKS"
    AWAITING_HUMAN_DECISION = "AWAITING_HUMAN_DECISION"  # human gate per chunk
    COMMITTING = "COMMITTING"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    PAUSED = "PAUSED"  # pause/resume checkpoint written


class ReconcileDecision(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    AMEND = "amend"


class GateDecision(str, enum.Enum):
    """Per-chunk gate verdict — mirrors ``tools/orchestrate-review.py:step6_gate_decision``."""
    ACCEPT = "ACCEPT"
    ACCEPT_WITH_NITS = "ACCEPT-WITH-NITS"
    REJECT = "REJECT"
    HUMAN_DECISION = "HUMAN_DECISION"
    STOP = "STOP"
    ERROR = "ERROR"


# ── chunk-level status ───────────────────────────────────────────────────

class ChunkStatus(str, enum.Enum):
    PENDING = "PENDING"
    TEST_DESIGNING = "TEST_DESIGNING"
    LOCKING = "LOCKING"
    VALIDATING_RED = "VALIDATING_RED"
    RED_REJECTED = "RED_REJECTED"
    EXECUTING = "EXECUTING"
    VERIFYING_GREEN = "VERIFYING_GREEN"
    EVIDENCING = "EVIDENCING"
    VALIDATING = "VALIDATING"
    ACCEPTED = "ACCEPTED"
    RETRYING = "RETRYING"
    HUMAN_DECISION = "HUMAN_DECISION"
    SKIPPED = "SKIPPED"


# ── chunk state ──────────────────────────────────────────────────────────

@dataclass
class Finding:
    """One finding row from a review pass. Mirrors telemetry schema's
    findings.jsonl row shape (subset — schema is the source of truth for
    the on-disk format; this is the in-memory shape)."""
    finding_id: str
    severity: str               # blocker|high|medium|low
    category: str               # semantic|factual|test-gap|scope|operability|style
    claim: str
    evidence: list[str]
    recommended_change: str
    source_role: str            # validator|reviewer
    source_run_id: str
    source_model_id: str
    source_family: str
    first_seen_in_panel_position: int = 1
    status: str = "open"        # open|accepted|rejected|superseded
    disposition_rationale: str = ""

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class ChunkState:
    """Mutable state for one chunk.

    The chunk state machine has its own status enum (ChunkStatus) so a
    run-level STOP doesn't preempt an in-progress chunk — the chunk
    handles STOP at the next gate decision propagation step.
    """
    chunk_id: str
    scope: str
    observable_criteria: list[str] = field(default_factory=list)
    allowed_files: list[str] = field(default_factory=list)
    locked_test_files: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    rollback: str = ""
    status: ChunkStatus = ChunkStatus.PENDING
    retry_count: int = 0
    accepted_assertion: str = ""
    lock_manifest_path: str = ""
    locked_test_sha: str = ""
    evidence_bundle_path: str = ""
    evidence_source: str = "bundle"  # "bundle" | "in-session"
    gate_decision: GateDecision | None = None
    gate_reason: str = ""
    rejection_feedback: list[str] = field(default_factory=list)  # fed back to executor
    findings: list[Finding] = field(default_factory=list)

    # The five run-ids inside one chunk
    test_designer_run_id: str = ""
    executor_run_id: str = ""
    validator_run_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # enums -> strings for JSON
        d["status"] = self.status.value
        d["gate_decision"] = self.gate_decision.value if self.gate_decision else None
        return d


# ── run-level state ──────────────────────────────────────────────────────

@dataclass
class RoleAssignment:
    """One role's model + family + provider discipline.

    Even roles that may use --auto (planner, executor) MUST resolve to a
    specific model ID after the run (PRD §17.1 attribution). The
    ``resolved_*`` fields are populated post-run from the envelope; they
    may equal ``pinned_*`` (when --model is used) or differ (when the
    Factory auto-router picked something — the collision guard then
    swaps a colliding reviewer per §17.1 rule 3).
    """
    role: Role
    pinned_model_id: str = ""
    pinned_family: str = ""
    pinned_provider: str = ""
    auto_level: str = "medium"
    enabled_tools: str = ""
    fallback_model_id: str = ""          # §17.1 collision-guard fallback
    fallback_family: str = ""
    resolved_model_id: str = ""          # populated post-run from envelope
    resolved_family: str = ""
    resolved_provider: str = ""
    num_turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    is_error: bool = False
    envelope_path: str = ""
    run_id: str = ""

    def to_distinct_families_for_guard(self) -> str:
        """Return the family currently bound to this role. Empty if not yet resolved."""
        return self.resolved_family or self.pinned_family


@dataclass
class RunState:
    """Top-level run state. Serialised to JSON for pause/resume."""

    run_id: str
    started_at: str                       # ISO-8601 UTC
    framework_root: str
    pilot_root: str
    pilot_python: str

    # Configured models (from --config or defaults)
    planner: RoleAssignment = field(default_factory=lambda: RoleAssignment(
        role=Role.PLANNER,
        auto_level="medium",
        enabled_tools=DEFAULT_ENABLED_TOOLS[Role.PLANNER],
    ))
    plan_reviewer: RoleAssignment = field(default_factory=lambda: RoleAssignment(
        role=Role.PLAN_REVIEWER,
        auto_level="high",
        enabled_tools=DEFAULT_ENABLED_TOOLS[Role.PLAN_REVIEWER],
    ))
    plan_reviewer_2: RoleAssignment | None = None  # optional 2nd reviewer
    test_designer: RoleAssignment = field(default_factory=lambda: RoleAssignment(
        role=Role.TEST_DESIGNER,
        auto_level="medium",
        enabled_tools=DEFAULT_ENABLED_TOOLS[Role.TEST_DESIGNER],
    ))
    executor: RoleAssignment = field(default_factory=lambda: RoleAssignment(
        role=Role.EXECUTOR,
        auto_level="medium",
        enabled_tools=DEFAULT_ENABLED_TOOLS[Role.EXECUTOR],
    ))
    validators: list[RoleAssignment] = field(default_factory=list)  # cross-family panel

    # Tuning
    max_review_rounds: int = 2           # PRD §5.3 default
    retry_threshold: int = 1             # PRD §5.7 cap for executor reject
    max_auto_retries: int = 2            # transient API failure retries
    retry_delay_seconds: int = 5

    # Status flow
    status: RunStatus = RunStatus.PENDING
    status_message: str = ""

    # Plan artifacts
    plan_doc_path: str = ""
    plan_sha256: str = ""
    plan_findings: list[Finding] = field(default_factory=list)
    plan_round: int = 0

    # Panel-finding F-7: store each reviewer's verdict, bound to the
    # plan_sha256 it was issued against. ``reconcile_human_gate``
    # consults this list before accepting the plan — the §5.3
    # converge rule: at least one APPROVE bound to current
    # plan_sha256 + zero open blocker|high findings.
    plan_reviewer_verdicts: list[dict] = field(default_factory=list)

    # Chunks (filled after reconcile accepts)
    chunks: list[ChunkState] = field(default_factory=list)
    current_chunk_index: int = 0

    # Final artifacts
    output_branch: str = ""
    commit_count: int = 0
    final_telemetry_path: str = ""

    # CLI behaviour flags (configurable)
    dry_run: bool = False
    skip_reconcile: bool = False
    create_pr: bool = False
    validation_backend: str = "local"    # local|ci (Track B)
    signing_key_env: str = "EVIDENCE_SIGNING_KEY"

    # Inputs the runner reads across pauses
    pilot_spec_file: str = ""
    signing_key: str = ""

    # Track which submission keys the family guard accepted — once any role's
    # family becomes known post-run, the guard re-runs to confirm nothing
    # collides that wasn't allowed to.
    family_guard_passed: bool = False
    family_guard_notes: str = ""

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def current_chunk(self) -> ChunkState | None:
        if 0 <= self.current_chunk_index < len(self.chunks):
            return self.chunks[self.current_chunk_index]
        return None

    def all_role_assignments(self) -> list[RoleAssignment]:
        out = [self.planner, self.plan_reviewer]
        if self.plan_reviewer_2 is not None:
            out.append(self.plan_reviewer_2)
        out.append(self.test_designer)
        out.append(self.executor)
        out.extend(self.validators)
        return out

    # Serialisation -------------------------------------------------------

    def to_json(self) -> str:
        d = asdict(self)
        # role enum -> value string in nested dataclasses
        for k in ("planner", "plan_reviewer", "plan_reviewer_2", "test_designer", "executor"):
            v = d.get(k)
            if isinstance(v, dict):
                v["role"] = v["role"]
        for v in d.get("validators", []):
            if isinstance(v, dict):
                v["role"] = v["role"]
        d["status"] = self.status.value
        return json.dumps(d, ensure_ascii=False, indent=2)


# ── family guard ─────────────────────────────────────────────────────────

@dataclass
class FamilyGuardOutcome:
    """Result of the §17.2 family-separation check.

    The runner calls this before any droid exec (preflight) and again
    after planner/executor have resolved (`--auto` may surface a family
    we did not pin). Structural enforcement — never assume the operator
    remembered the rule.
    """
    ok: bool
    violations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.notes.append(msg)


def check_family_separation(
    *assignments: RoleAssignment,
    allow_test_author_collide: bool = False,
    allow_single_family: bool = False,
) -> FamilyGuardOutcome:
    """PRD §17.2 separation check at preflight time.

    Rules:
      - planner family != plan_reviewer family
      - plan_reviewer families are mutually distinct (if 2nd reviewer is set)
      - test_designer family != executor family (default — see §17.6)
      - each validator family != executor family
      - at least one validator family that is in
        {planner_family, test_designer_family, executor_family}-distinct
      - **any role on a separation-bearing seat must have a known family.**
        PRD §4: provenance is curated, not inferred; "unknown cannot
        satisfy a hard separation constraint — it stops the run rather
        than being optimistically admitted." (Silently letting an
        unknown model through is the silent-green defect shape of §17.2.)

    ``allow_test_author_collide=True`` is **only** for the §17.6 outage
    fallback. The operator must have recorded the outage in
    ``phase-N/KNOWN-ISSUES.md`` for the loop runner to accept the flag —
    the higher-level orchestrator enforces that; this function does not
    check KNOWN-ISSUES (it's pure). Document the override in telemetry.

    ``allow_single_family=True`` mirrors
    ``tools/orchestrate-review.py --allow-single-family`` — the run-level
    override. It is logged but not auto-accepted.
    """
    out = FamilyGuardOutcome(ok=True)

    if not assignments:
        out.ok = False
        out.violations.append("family_separation_check: no role assignments provided")
        return out

    # PRD §4: provenance is curated, not inferred; "unknown cannot satisfy
    # a hard separation constraint — it stops the run rather than being
    # optimistically admitted." This applies to EVERY role, not just
    # binding seats. The §17.2 collision logic below compares families by
    # string equality; if one side is "unknown" and the other is, say,
    # "grok-family", they trivially differ — the rule passes silently
    # but the invariant is void because we couldn't actually verify
    # separation. Two-passes-of-comparison business rules cannot rescue
    # a missing provenance entry. Stop here.
    for a in assignments:
        family = a.to_distinct_families_for_guard()
        if family == "unknown":
            label = a.pinned_model_id or a.resolved_model_id or "<unlabeled>"
            out.violations.append(
                f"§4: role {a.role.value} uses model {label!r} with "
                f"family='unknown'. The curated MODEL_FAMILY_MAP does not "
                f"list this model; per PRD §4, provenance is curated, not "
                f"inferred, and unknown cannot satisfy a hard separation "
                f"constraint. Add the model to tools/sprint_loop/config.py "
                f"MODEL_FAMILY_MAP with (provider, family), then re-run. "
                f"Silent admission is the same defect shape as a silent "
                f"green per §7."
            )

    by_role: dict[Role, RoleAssignment] = {a.role: a for a in assignments}

    def fam(a: RoleAssignment) -> str:
        return a.to_distinct_families_for_guard()

    # planner vs EACH plan_reviewer (not just by_role[PLAN_REVIEWER], which
    # overwrites when 2 reviewers are configured — panel-finding F-1).
    # `by_role` still captures the singleton seats (td/ex/validator) but
    # for multi-seat roles (PLAN_REVIEWER, VALIDATOR) we compare against
    # every assignment with that role.
    planner = next((a for a in assignments if a.role is Role.PLANNER), None)

    # planner vs each plan_reviewer — guard against silent overwriting.
    if planner and fam(planner):
        for reviewer in (a for a in assignments if a.role is Role.PLAN_REVIEWER):
            if not fam(reviewer):
                continue
            if fam(planner) == fam(reviewer):
                out.violations.append(
                    f"§17.2: planner family '{fam(planner)}' == plan_reviewer "
                    f"family '{fam(reviewer)}' "
                    f"(reviewer model: {reviewer.pinned_model_id!r}) "
                    f"— same family is not independence"
                )

    # two reviewers must be different families from each other
    seen_reviewer_families: set[str] = set()
    for a in (x for x in assignments if x.role is Role.PLAN_REVIEWER):
        if not fam(a):
            continue
        if fam(a) in seen_reviewer_families:
            out.violations.append(
                f"§17.2: two plan reviewers share family '{fam(a)}' — "
                f"two reviewers in the same family is not a panel"
            )
        seen_reviewer_families.add(fam(a))

    # test_designer != executor (unless §17.6 override)
    td = by_role.get(Role.TEST_DESIGNER)
    ex = by_role.get(Role.EXECUTOR)
    if td and ex and fam(td) and fam(ex):
        if fam(td) == fam(ex) and not allow_test_author_collide:
            out.violations.append(
                f"§17.2: test_designer family '{fam(td)}' == executor family "
                f"'{fam(ex)}' — invariant #1 binds (see §17.6 for outage-only override)"
            )

    # validator != executor
    validators = [a for a in assignments if a.role == Role.VALIDATOR]
    validator_families: set[str] = set()
    for v in validators:
        if ex and fam(v) and fam(v) == fam(ex):
            out.violations.append(
                f"§17.2: validator '{v.pinned_model_id or v.resolved_model_id}' "
                f"family '{fam(v)}' == executor family '{fam(ex)}' — "
                f"colliding family voids the independence control"
            )
        if fam(v):
            validator_families.add(fam(v))

    # Cross-family validator panel: need >= 2 distinct families unless allowed
    if validators and len(validator_families) < 2 and not allow_single_family:
        out.violations.append(
            f"§17.2: validator panel has {len(validator_families)} distinct "
            f"families (need >= 2 for a fail-closed cross-family panel). "
            f"Use allow_single_family=True per the §17.6 fallback ONLY."
        )

    out.ok = not out.violations
    return out


# ── helpers ──────────────────────────────────────────────────────────────

_FAMILY_HASH_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def validate_run_id(rid: str) -> str:
    """Validate run_id is safe to write to filenames and JSON lines.

    Empty is OK (means "auto-generate"); anything else must match the
    safe pattern or it is rejected. Rejecting malformed run_ids before
    they hit filenames prevents path traversal via crafted ids.
    """
    if not rid:
        return ""
    if not _ID_RE.match(rid):
        raise ValueError(
            f"run_id {rid!r} contains unsafe characters (must be "
            f"[A-Za-z0-9._-] and 1-80 chars)"
        )
    return rid


def hash_text(text: str) -> str:
    """Stable SHA-256 of a UTF-8 string. Used for plan-hash and lock-manifest."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
