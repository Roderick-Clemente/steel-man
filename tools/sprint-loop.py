#!/usr/bin/env python3
"""Phase 4.5 — adversarial sprint loop runner.

This is the **entry point** for the command-orchestrated sprint
described in PRD §11 Phase 4.5. It wires together the five roles
(planner, plan reviewer, test designer, executor, validator) and the
two pause/resume gates (reconcile after planning, human-decision after
chunk-level disagreements).

The runner is **thin orchestration**: every "what does this step do"
is delegated to existing primitives (``tools/sprint_loop/*`` plus
``phase-1/scripts/*`` and ``phase-3.2/evidence/*``). The runner's NEW
work is:

  - State machine flow + status transitions
  - The **human reconcile gate** (stdin pause; reads accept / reject /
    amend)
  - Chunking input parsing
  - Retry / re-plan accounting
  - Branch + conventional-commits creation at the end (no
    auto-merge per invariant #8)
  - Telemetry row emission (one per droid invocation; the wrappers
    do that already — this orchestrator just appends the rows)

CLI:

    python3 tools/sprint-loop.py --config <cfg.json> [overrides]
        --dry-run             : simulate, no droid / no git
        --skip-reconcile      : bypass the human reconcile gate
        --create-pr           : try PR creation (default off — human gates)
        --validation-backend  : 'local' (default) or 'ci' (stub)
        --resume-from <path>  : resume from a checkpoint JSON
        --chunks-file <path>  : JSON file with the chunk list to drive

OPERATING-RULES applied (see tools/OPERATING-RULES.md for the full list):

  §7  : assert on reality — bundle signature / locked-SHA / pytest.
  §9  : this script is the default; RUN-COMMANDS.md is documentation,
        not a substitute.
  §10 : ``runs.jsonl`` rows written by the script, append-only.
  §11 : exit criteria checked, not assumed.
  §13 : executor prompt has the chunk spec, not the implementation.
  §14 : ``tools/run-with-model.sh`` wrapper for every droid call;
        ``tools/adapters/factory.py`` for envelope parsing.
  §15 : git history is reality — assert on the branch actually moved.
  §17 : refuse unbounded foundation programs; one bounded phase.
  §18 : compose existing primitives; build in chunks; fix ergonomic
        friction inline; review at the end.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

# Make ``tools/`` importable + ``adapters``+``sprint_loop`` packages
# resolvable. Same pattern as ``tools/orchestrate-review.py``.
_TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sprint_loop.config import (  # noqa: E402
    BUILD_EVIDENCE_DIR,
    MODEL_FAMILY_MAP,
    Config,
    build_config,
)
from sprint_loop.droid import (  # noqa: E402
    InvokeOptions,
    append_run_record,
    invoke_droid,
)
from sprint_loop.per_chunk import (  # noqa: E402
    FEEDBACK_SOURCE_GATE_REASON,
    FEEDBACK_SOURCE_VALIDATOR_FINDING,
    REJECTION_IMPLEMENTATION,
    REJECTION_TEST,
    archive_superseded_test,
    chunk_full_suite_command,
    classify_rejection,
    format_implementation_rejection_feedback,
    format_test_rejection_feedback,
    implementation_rejection_has_finding,
    invoke_executor,
    invoke_test_designer,
    lock_test,
    parse_accepted_assertion,
    produce_evidence,
    render_executor_prompt,
    render_test_designer_prompt,
    run_validators,
    validate_red,
    verify_green,
)
from sprint_loop.prompts.render import render_to_file  # noqa: E402
from sprint_loop.provenance import (  # noqa: E402
    _git_branch,
    _git_sha,
    run_provenance,
)
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    ChunkStatus,
    Finding,
    GateDecision,
    ReconcileDecision,
    Role,
    RoleAssignment,
    RunState,
    RunStatus,
    check_family_separation,
    hash_text,
    now_iso,
    validate_run_id,
)
from sprint_loop import vocab  # noqa: E402

# ── git helpers (assert-on-reality per OPERATING-RULES §7/§15) ───────────


def _git(*args: str, cwd: str | None = None) -> str:
    """Run a git command, capture stdout. cwd defaults to framework_root."""
    r = subprocess.run(
        ["git", *args],
        cwd=cwd or _REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git {args} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def _git_branch_exists(branch: str) -> bool:
    out = _git("branch", "--list", branch).strip()
    return bool(out)


# ── checkpoints (RunState pause/resume) ─────────────────────────────────


def write_checkpoint(rs: RunState, path: str) -> None:
    """Persist RunState to disk so the operator can resume later.

    Per Phase 4.5 PRD §11: durable runner. The checkpointer is the
    spine of "close the laptop, come back" — but we ALSO emit an
    honest narrative that the demo cannot claim that until pilots
    exercise the resume path. Until then this is a clean null.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(rs.to_json())


def load_checkpoint(path: str) -> RunState:
    if not os.path.isfile(path):
        raise SystemExit(f"--resume-from file missing: {path}")
    with open(path) as f:
        data = json.load(f)

    # Required constructor args.
    rs = RunState(
        run_id=data["run_id"],
        started_at=data["started_at"],
        framework_root=data["framework_root"],
        pilot_root=data["pilot_root"],
        pilot_python=data["pilot_python"],
    )

    # Field-driven restore: iterate dataclass fields so any future
    # RunState field round-trips automatically. Role assignments are
    # reconstructed from the Config at runtime; plan_findings and chunks
    # need special-case deserialization (nested dataclasses / enums).
    _SKIP = frozenset({
        # Required constructor args (already set above).
        "run_id", "started_at", "framework_root", "pilot_root", "pilot_python",
        # Role assignments: reconstructed from Config at runtime.
        "planner", "plan_reviewer", "plan_reviewer_2",
        "test_designer", "executor", "validators",
        # Complex nested types handled below.
        "plan_findings", "chunks",
    })
    _ENUM_MAP: dict[str, type] = {"status": RunStatus}

    for fld in dataclasses.fields(RunState):
        if fld.name in _SKIP or fld.name not in data:
            continue
        raw = data[fld.name]
        if fld.name in _ENUM_MAP:
            setattr(rs, fld.name, _ENUM_MAP[fld.name](raw))
        else:
            setattr(rs, fld.name, raw)

    # run_label: default to run_id when missing or empty.
    if not rs.run_label:
        rs.run_label = rs.run_id

    # plan_findings: nested Finding dataclasses.
    if data.get("plan_findings"):
        rs.plan_findings = [
            Finding(
                finding_id=f.get("finding_id", ""),
                severity=f.get("severity", ""),
                category=f.get("category", ""),
                claim=f.get("claim", ""),
                evidence=f.get("evidence", []),
                recommended_change=f.get("recommended_change", ""),
                source_role=f.get("source_role", "reviewer"),
                source_run_id=f.get("source_run_id", ""),
                source_model_id=f.get("source_model_id", ""),
                source_family=f.get("source_family", ""),
                first_seen_in_panel_position=f.get("first_seen_in_panel_position", 1),
                status=f.get("status", "open"),
                disposition_rationale=f.get("disposition_rationale", ""),
                plan_section=f.get("plan_section", ""),
                risk_if_ignored=f.get("risk_if_ignored", ""),
            )
            for f in data["plan_findings"]
        ]

    # chunks: field-driven restore mirroring the RunState approach.
    _CHUNK_SKIP = frozenset({"chunk_id", "scope", "findings", "verify_mode"})
    _CHUNK_ENUM_MAP: dict[str, type] = {"status": ChunkStatus}

    if data.get("chunks"):
        for c in data["chunks"]:
            cs = ChunkState(chunk_id=c["chunk_id"], scope=c.get("scope", ""))
            for fld in dataclasses.fields(ChunkState):
                if fld.name in _CHUNK_SKIP or fld.name not in c:
                    continue
                raw = c[fld.name]
                if fld.name in _CHUNK_ENUM_MAP:
                    setattr(cs, fld.name, _CHUNK_ENUM_MAP[fld.name](raw))
                elif fld.name == "gate_decision":
                    # gate_decision is GateDecision | None; serialized as
                    # a string value or null.
                    setattr(cs, fld.name, GateDecision(raw) if raw else None)
                else:
                    setattr(cs, fld.name, raw)
            # findings: nested Finding dataclasses, same shape as
            # plan_findings.
            if c.get("findings"):
                cs.findings = [
                    Finding(
                        finding_id=f.get("finding_id", ""),
                        severity=f.get("severity", ""),
                        category=f.get("category", ""),
                        claim=f.get("claim", ""),
                        evidence=f.get("evidence", []),
                        recommended_change=f.get("recommended_change", ""),
                        source_role=f.get("source_role", "reviewer"),
                        source_run_id=f.get("source_run_id", ""),
                        source_model_id=f.get("source_model_id", ""),
                        source_family=f.get("source_family", ""),
                        first_seen_in_panel_position=f.get(
                            "first_seen_in_panel_position", 1
                        ),
                        status=f.get("status", "open"),
                        disposition_rationale=f.get("disposition_rationale", ""),
                        plan_section=f.get("plan_section", ""),
                        risk_if_ignored=f.get("risk_if_ignored", ""),
                    )
                    for f in c["findings"]
                ]
            # verify_mode: inherit from run-level flag (deliberate OR).
            cs.verify_mode = bool(c.get("verify_mode", False)) or rs.verify_mode
            # A resume must not silently hand the test-design budget back:
            # the bounces already spent are part of the chunk's state.
            cs.rejection_kind = c.get("rejection_kind", "")
            cs.test_design_feedback = c.get("test_design_feedback", [])
            cs.test_design_retry_count = int(c.get("test_design_retry_count", 0))
            cs.rejection_feedback_source = c.get("rejection_feedback_source", "")
            rs.chunks.append(cs)

    return rs


# ── step functions ───────────────────────────────────────────────────────


def status_banner(title: str) -> None:
    print()
    print("=" * 64)
    print(f"  {title}")
    print("=" * 64)


def state_status(rs: RunState, what: str) -> None:
    print(f"  status: {rs.status.value} | chunk {rs.current_chunk_index}/{len(rs.chunks)} | {what}")


# ── steps: planner ───────────────────────────────────────────────────────

# The eight sections planner.md requires, in order. Each entry is the
# section NAME plus the alternative spellings a model plausibly emits
# for it; matching is on the name, never on our punctuation.
_PLAN_REQUIRED_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Sprint Metadata", ("sprint metadata",)),
    ("Objectives", ("objectives",)),
    ("Current state", ("current state",)),
    ("Risk assessment", ("risk assessment",)),
    ("Acceptance criteria", ("acceptance criteria",)),
    ("Test strategy", ("test strategy",)),
    ("Chunk plan", ("chunk plan", "chunks")),
    ("Open questions", ("open questions",)),
)

# Heuristic only: phrases a seat uses when it narrates having produced a
# document instead of producing one. Keep this list short — it exists to
# label a shape we have actually observed, not to police prose.
_PLAN_REPORT_MARKERS: tuple[str, ...] = (
    "successfully generated",
    "has been saved",
    "saved to the required location",
    "output artifact",
)

# A real §5.2 plan with eight sections and a per-chunk chunk plan does not
# fit in a few kilobytes. The plan observed on the failing run was ~1KB of
# chat summary; the genuine document the same seat composed was ~8.5KB.
# 3000 sits well clear of the summary and well under any real plan.
_PLAN_MIN_CHARS = 3000


def _plan_section_present(plan_md: str, aliases: tuple[str, ...]) -> bool:
    """True when any alias appears as a heading-ish line in ``plan_md``.

    Tolerant by design: accepts ATX headings (``## Objectives``),
    bold headings (``**Objectives**``), and numbered headings
    (``3. Current state / root cause / opportunity``), and matches on a
    prefix so a longer heading still counts.
    """
    for raw_line in plan_md.splitlines():
        line = raw_line.strip().lower()
        if not line:
            continue
        line = line.lstrip("#").strip()
        line = re.sub(r"^\d+[.)]\s*", "", line)
        line = line.replace("*", "").replace("_", "").replace("`", "").strip()
        line = line.rstrip(":").strip()
        for alias in aliases:
            if line.startswith(alias):
                return True
    return False


def _validate_plan_document(plan_md: str) -> list[str]:
    """Return human-readable problems with a candidate plan document.

    The planner seat is read-only by design (no write tool), so the only
    plan the runner can trust is the envelope ``result`` — the text the
    model actually emitted. A seat that believes it must write a file can
    fail that write and still close with "the document has been saved",
    at which point the runner happily hashes a chat summary as the plan
    and two cross-family reviewers burn a call each rejecting it. This
    check makes that shape fail here, loudly, instead of downstream.

    Empty list means the document is structurally plausible; this is a
    shape check, not a quality review — the reviewers do quality.
    """
    problems: list[str] = []

    missing = [
        name
        for name, aliases in _PLAN_REQUIRED_SECTIONS
        if not _plan_section_present(plan_md, aliases)
    ]
    if missing:
        problems.append("missing required section(s): " + ", ".join(missing))

    lowered = plan_md.lower()
    if missing and any(marker in lowered for marker in _PLAN_REPORT_MARKERS):
        problems.append("reads as a report about a plan rather than a plan")

    if len(plan_md) < _PLAN_MIN_CHARS:
        problems.append(
            f"too short to be a plan: {len(plan_md)} characters, "
            f"minimum {_PLAN_MIN_CHARS}"
        )

    return problems


_NO_AUTHORED_CHUNKS = "(none supplied — propose a chunking)"


def _format_authored_chunks(chunks_path: str | None) -> str:
    """Render the operator's authored chunks JSON as a markdown contract.

    Execution is driven entirely by this file, so a planner that never
    sees it invents chunk boundaries, file paths and locked tests that
    will never run — and the plan reviewers then audit the invention
    instead of the contract. Rendering it as markdown (rather than a
    JSON blob) is deliberate: the planner reads it as a contract to
    conform to.

    Returns the sentinel when no usable contract is available; this is
    a prompt-context helper and must never be the reason a run aborts.
    """
    if not chunks_path or not os.path.isfile(chunks_path):
        return _NO_AUTHORED_CHUNKS
    try:
        with open(chunks_path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _NO_AUTHORED_CHUNKS

    if isinstance(data, dict):
        chunks = data.get("chunks") or data.get("items") or []
    else:
        chunks = data
    if not isinstance(chunks, list) or not chunks:
        return _NO_AUTHORED_CHUNKS

    def _lines(label: str, value: Any) -> list[str]:
        if not value:
            return []
        out = [f"- **{label}**:"]
        if isinstance(value, dict):
            for key, item in value.items():
                if item:
                    out.append(f"  - {key}: `{item}`")
        elif isinstance(value, (list, tuple)):
            for item in value:
                out.append(f"  - `{item}`")
        else:
            out = [f"- **{label}**: `{value}`"]
        return out

    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            parts.append(f"### Chunk {index}\n\n- (unreadable chunk entry: `{chunk}`)")
            continue
        chunk_id = chunk.get("chunk_id") or chunk.get("id") or chunk.get("name") or f"chunk-{index}"
        body = [f"### {chunk_id}"]
        scope = chunk.get("scope") or chunk.get("name")
        if scope:
            body.append(f"- **Scope**: {scope}")
        criteria = chunk.get("observable_criteria") or chunk.get("criteria") or []
        if isinstance(criteria, str):
            criteria = [criteria]
        if criteria:
            body.append("- **Observable criteria**:")
            for item in criteria:
                body.append(f"  - {item}")
        body += _lines("allowed_files", chunk.get("allowed_files"))
        body += _lines("locked_test_files", chunk.get("locked_test_files"))
        body += _lines("commands", chunk.get("commands"))
        for key, label in (
            ("red_command", "RED command"),
            ("green_command", "GREEN command"),
            ("full_suite_command", "full-suite command"),
            ("lint_command", "lint command"),
            ("build_command", "build command"),
        ):
            body += _lines(label, chunk.get(key))
        if chunk.get("accepted_assertion"):
            body.append(f"- **accepted_assertion**: {chunk['accepted_assertion']}")
        if chunk.get("rollback"):
            body.append(f"- **rollback**: `{chunk['rollback']}`")
        parts.append("\n".join(body))

    header = (
        f"The operator authored {len(chunks)} chunk(s) in `{chunks_path}`. "
        f"This is the contract the runner executes verbatim."
    )
    return header + "\n\n" + "\n\n".join(parts)


_NO_PRIOR_FINDINGS = "(first round — no prior findings)"

# blocker|high are what §5.3 blocks acceptance on, so they lead.
_SEVERITY_ORDER = ("blocker", "high", "medium", "low")


def _format_prior_findings(findings: list[Finding]) -> str:
    """Render the previous review round's findings for the planner.

    Without this the looped planner regenerates a near-identical plan and
    the next round's reviewer calls are spent re-finding the same defects.
    Each entry carries the plan's claim AND ``risk_if_ignored`` because
    the claim alone reads as agreement; the risk is the thing to fix.

    Returns the sentinel on an empty list and never raises: this is
    prompt context and must not be why a run aborts.
    """
    try:
        rows = [f for f in (findings or []) if f is not None]
        if not rows:
            return _NO_PRIOR_FINDINGS

        def _key(item: tuple[int, Finding]) -> tuple[int, int]:
            index, finding = item
            sev = (finding.severity or "").lower()
            rank = _SEVERITY_ORDER.index(sev) if sev in _SEVERITY_ORDER else len(_SEVERITY_ORDER)
            return (rank, index)

        ordered = [f for _, f in sorted(enumerate(rows), key=_key)]
        blocking = sum(
            1 for f in ordered if (f.severity or "").lower() in ("blocker", "high")
        )
        parts = [
            f"A previous review round raised {len(ordered)} finding(s), "
            f"{blocking} of them blocker|high. They are listed "
            f"blocker|high first."
        ]
        for finding in ordered:
            body = [
                f"### {finding.finding_id or '(unlabelled)'} — "
                f"{(finding.severity or 'unknown').lower()} / "
                f"{(finding.category or 'unknown').lower()}"
            ]
            if finding.source_model_id:
                body.append(f"- **Raised by**: {finding.source_model_id}")
            if finding.plan_section:
                body.append(f"- **Plan section**: {finding.plan_section}")
            if finding.claim:
                body.append(f"- **The plan claimed**: {finding.claim}")
            if finding.risk_if_ignored:
                body.append(f"- **Risk if ignored**: {finding.risk_if_ignored}")
            if finding.evidence:
                body.append("- **Evidence**:")
                for item in finding.evidence:
                    body.append(f"  - {item}")
            if finding.recommended_change:
                body.append(f"- **Recommended change**: {finding.recommended_change}")
            parts.append("\n".join(body))
        return "\n\n".join(parts)
    except Exception:
        return _NO_PRIOR_FINDINGS


def run_planner(rs: RunState, *, pilot_spec_text: str, evidence_dir: str, dry_run: bool) -> dict:
    """Fire the planner role and produce the plan document."""
    rs.status = RunStatus.PLANNING
    status_banner("STEP 1 · Planner (GROK)")
    state_status(rs, "planner role active")

    rnd = rs.plan_round
    plan_doc_path = os.path.join(evidence_dir, f"plan-r{rnd}.md")
    rendered_path = render_to_file(
        "planner",
        {
            "pilot_spec_path": rs.pilot_spec_file or "(no --pilot-spec-file)",
            "plan_output_path": plan_doc_path,
            "authored_chunks": _format_authored_chunks(rs.chunks_file),
            "prior_findings": _format_prior_findings(rs.plan_findings),
        },
        os.path.join(evidence_dir, f"plan-prompt-r{rnd}.md"),
    )

    # A finding is raised against one plan_sha256. The plan about to be
    # produced replaces the one they were raised against, so they become
    # "superseded" (§5.3 binds findings to the exact plan hash). They stay
    # on rs.plan_findings — the audit trail and the next round's prompt
    # need them — but they must stop counting toward the §5.3 open
    # blocker|high ledger, or round 2 could never be accepted no matter
    # what the planner fixed, and the re-review would be spent for
    # nothing.
    for prior in rs.plan_findings:
        if prior.status == "open":
            prior.status = "superseded"
            prior.disposition_rationale = (
                f"superseded: raised against the plan reviewed in round "
                f"{rs.plan_round - 1}, which this round replaces"
            )

    env_path = os.path.join(evidence_dir, f"planner-envelope-r{rnd}.json")
    stderr_path = os.path.join(evidence_dir, f"planner-stderr-r{rnd}.log")
    options = InvokeOptions(
        model_id=rs.planner.pinned_model_id or "claude-opus-5",
        auto_level=rs.planner.auto_level,
        enabled_tools=rs.planner.enabled_tools,
        prompt_file=rendered_path,
        cwd=rs.framework_root,
        timeout_seconds=rs.per_call_timeout_seconds or 1800,
    )
    record = invoke_droid(
        Role.PLANNER,
        options=options,
        envelope_path=env_path,
        stderr_path=stderr_path,
        max_retries=rs.max_auto_retries,
        retry_delay_seconds=rs.retry_delay_seconds,
        dry_run=dry_run,
    )
    # Resolved attribution
    rs.planner.resolved_model_id = record.model_id
    rs.planner.resolved_provider = record.provider
    rs.planner.resolved_family = record.family
    rs.planner.num_turns = record.num_turns
    rs.planner.input_tokens = record.input_tokens
    rs.planner.output_tokens = record.output_tokens
    rs.planner.duration_ms = record.duration_ms
    rs.planner.is_error = record.is_error
    rs.planner.envelope_path = record.envelope_path
    rs.planner.run_id = record.run_id
    record.provenance = run_provenance(rs)
    record.run_label = rs.run_label
    record.phase_step = vocab.PHASE_PLAN
    append_run_record(
        record,
        phase="phase-4.5",
        branch=_git_branch(rs.framework_root),
        telemetry_path=os.path.join(rs.framework_root, "telemetry", "runs.jsonl"),
    )

    if not dry_run and record.is_error:
        raise RuntimeError(
            f"planner invocation failed; envelope at {record.envelope_path}; "
            f"stderr at {record.stderr_path}; aborting before any droid "
            f"writes a plan"
        )

    if dry_run:
        # Synthesize a deterministic plan markdown so downstream steps
        # have the right shape without a real planner.
        plan_md = (
            "# Sprint plan (dry-run)\n\n"
            "## Sprint Metadata\n- Sprint: phase-4.5-loop-runner (dry-run)\n"
            "- Status: planning\n\n"
            "## Objectives\n- Validate the loop runner end-to-end.\n\n"
            "## Chunks\n- chunk-1: simulate a single acceptance slice.\n\n"
            "PLAN_HASH: <computed-by-runner>\n"
        )
    else:
        # Read the result text from the planner's envelope and persist
        # to plan_doc_path. The planner should have produced a complete
        # document — we store the full envelope result as the source of
        # truth (it is what the reviewer reads).
        try:
            with open(record.envelope_path) as f:
                env = json.load(f)
            plan_md = env.get("result") or ""
        except (OSError, json.JSONDecodeError) as e:
            raise RuntimeError(f"planner envelope unreadable for plan: {e}") from None

        problems = _validate_plan_document(plan_md)
        if problems:
            raise RuntimeError(
                "planner returned text that is not a plan document; refusing "
                "to hash-bind it and spend cross-family review on it. "
                "Problems: "
                + "; ".join(problems)
                + f". The planner has no file-writing tool, so its final "
                f"message IS the plan — a seat that tried to write a file "
                f"may have reported success while that write failed, and "
                f"this is what the runner actually received. Envelope: "
                f"{record.envelope_path}; stderr: {record.stderr_path}; "
                f"intended plan path: {plan_doc_path}. (Accepting a summary "
                f"as the plan is the silent-green defect shape.)"
            )

    os.makedirs(os.path.dirname(plan_doc_path) or ".", exist_ok=True)
    with open(plan_doc_path, "w") as f:
        f.write(plan_md)
    plan_sha = hash_text(plan_md)
    rs.plan_doc_path = plan_doc_path
    rs.plan_sha256 = plan_sha
    print(f"  plan written: {plan_doc_path}")
    print(f"  plan sha256:  {plan_sha}")
    return {"record": record, "plan_doc_path": plan_doc_path, "plan_sha256": plan_sha}


# ── steps: plan reviewer ─────────────────────────────────────────────────

_VERDICT_RE = re.compile(
    vocab.tagged_line_pattern("VERDICT", vocab.PLAN_REVIEW_VERDICTS),
    re.IGNORECASE | re.MULTILINE,
)
# Executor results follow the same last-tagged-line discipline as verdicts.
# Parsing all supported signals prevents an earlier example or superseded
# result from overriding the executor's final protocol line.
_EXECUTOR_RESULT_RE = re.compile(
    vocab.tagged_line_pattern("RESULT", vocab.EXECUTOR_RESULT_SIGNALS),
    re.IGNORECASE | re.MULTILINE,
)
_FINDING_ID_RE = re.compile(
    r'"finding_id"\s*:\s*"F-[a-z0-9]+"',
    re.IGNORECASE,
)

# Cap for the two fields the next planner round must act on
# (``risk_if_ignored``, ``recommended_change``). Generous on purpose:
# these are fed back into the planner prompt verbatim, so the cap exists
# only to stop a runaway seat from blowing up the prompt, not to fit a
# terminal line.
_FINDING_ACTIONABLE_MAX = 1200


def _is_spec_or_test_blocked(result_text: str) -> bool:
    """True when the executor's last RESULT line is SPEC_OR_TEST_BLOCKED.

    The executor emits this when it believes the locked test is
    contradictory or the spec is unimplementable (see
    ``tools/sprint_loop/prompts/executor.md``). Narrating the token or
    superseding an earlier blocked result with ``RESULT: GREEN`` does not
    block the chunk.
    """
    results = _EXECUTOR_RESULT_RE.findall(result_text or "")
    return bool(results) and results[-1].upper() == vocab.RESULT_SPEC_OR_TEST_BLOCKED


def _parse_finding_block(
    reviewer_label: str,
    result_text: str,
    source_run_id: str,
    source_model: str,
    source_family: str,
    panel_position: int,
) -> list[Finding]:
    """Best-effort JSON extraction of findings from the reviewer's
    natural-language result text. The reviewer prompt asks for a
    structured JSON output; the parser is lenient so missing/extra
    brackets do not break the runner.

    KI-4: a naive brace counter drops any finding whose string values
    contain unbalanced braces (e.g. a ``{{chunk_spec}`` template
    literal quoted in an evidence entry) — grok's HIGH F-3a91c2 was
    silently lost this way, letting §5.3 pass vacuously. raw_decode
    is string-aware, so braces inside JSON strings cannot desync it.

    Extraction policy (review finding F-d4e5f6): each "finding_id"
    occurrence anchors its NEAREST enclosing parseable object, and
    results dedupe by finding_id string (first occurrence wins). A
    wrapper object that repeats a child's finding_id therefore cannot
    double-count severity into the §5.3 ledger.
    """
    findings: list[Finding] = []
    decoder = json.JSONDecoder()
    seen_starts: set[int] = set()
    seen_ids: set[str] = set()
    for match in _FINDING_ID_RE.finditer(result_text):
        # Walk back through candidate opening braces until one parses
        # as a JSON object that spans this "finding_id" occurrence.
        start = result_text.rfind("{", 0, match.start())
        obj = None
        while start >= 0:
            try:
                candidate, end = decoder.raw_decode(result_text, start)
            except json.JSONDecodeError:
                candidate, end = None, -1
            if isinstance(candidate, dict) and end > match.end() and "finding_id" in candidate:
                obj = candidate
                break
            start = result_text.rfind("{", 0, start)
        if obj is None or start in seen_starts:
            continue
        fid = obj.get("finding_id")
        if isinstance(fid, str) and fid in seen_ids:
            continue
        seen_starts.add(start)
        if isinstance(fid, str):
            seen_ids.add(fid)
        f = Finding(
            finding_id=obj.get("finding_id", f"F-unlabeled-{reviewer_label}"),
            severity=(obj.get("severity") or "medium").lower(),
            category=(obj.get("category") or "spec-deviation").lower(),
            claim=(obj.get("claim") or "")[:240],
            evidence=obj.get("evidence", []) or [],
            # 240 was enough for a display snippet but not for text a
            # looped planner has to act on: the next round's prompt
            # carries these two verbatim, and a sentence clipped
            # mid-clause is an instruction the planner cannot execute.
            recommended_change=(obj.get("recommended_change") or "")[:_FINDING_ACTIONABLE_MAX],
            source_role="reviewer",
            source_run_id=source_run_id,
            source_model_id=source_model,
            source_family=source_family,
            first_seen_in_panel_position=panel_position,
            status="open",
            plan_section=(obj.get("plan_section") or "")[:240],
            risk_if_ignored=(obj.get("risk_if_ignored") or "")[:_FINDING_ACTIONABLE_MAX],
        )
        findings.append(f)
    return findings


def run_plan_reviewer(
    rs: RunState,
    *,
    reviewer_index: int,
    evidence_dir: str,
    dry_run: bool,
    is_second_reviewer: bool = False,
) -> dict:
    """Fire ONE plan-reviewer role. Cross-family from planner (§17.2).

    reviewer_index: 1..N — used in panel_position and envelope label.
    """
    rs.status = RunStatus.PLAN_REVIEWING
    reviewer = (
        rs.plan_reviewer_2 if (is_second_reviewer and rs.plan_reviewer_2) else rs.plan_reviewer
    )
    label = f"plan-reviewer-{reviewer_index}"
    status_banner(
        f"STEP 2.{reviewer_index} · Plan reviewer {reviewer_index} ({reviewer.pinned_model_id})"
    )
    state_status(rs, f"reviewer {reviewer_index} role active")

    rnd = rs.plan_round
    reviewer_prompt_out = os.path.join(evidence_dir, f"{label}-r{rnd}-prompt.md")
    rendered_path = render_to_file(
        "plan-reviewer",
        {
            "plan_doc_path": rs.plan_doc_path,
            "pilot_spec_path": rs.pilot_spec_file or "(no spec)",
            "panel_position": str(reviewer_index),
        },
        reviewer_prompt_out,
    )

    # PRD §17 invariant (single-blind): the second reviewer should NOT
    # see the first reviewer's output. The runner does NOT inject the
    # prior findings into the prompt; the test on that is in KNOWN-ISSUES.

    env_path = os.path.join(evidence_dir, f"{label}-r{rnd}-envelope.json")
    stderr_path = os.path.join(evidence_dir, f"{label}-r{rnd}-stderr.log")
    options = InvokeOptions(
        model_id=reviewer.pinned_model_id,
        auto_level=reviewer.auto_level,
        enabled_tools=reviewer.enabled_tools,
        prompt_file=rendered_path,
        cwd=rs.framework_root,
        timeout_seconds=rs.per_call_timeout_seconds or 1800,
    )
    record = invoke_droid(
        Role.PLAN_REVIEWER,
        options=options,
        envelope_path=env_path,
        stderr_path=stderr_path,
        max_retries=rs.max_auto_retries,
        retry_delay_seconds=rs.retry_delay_seconds,
        dry_run=dry_run,
    )
    reviewer.resolved_model_id = record.model_id
    reviewer.resolved_provider = record.provider
    reviewer.resolved_family = record.family
    reviewer.num_turns = record.num_turns
    reviewer.input_tokens = record.input_tokens
    reviewer.output_tokens = record.output_tokens
    reviewer.duration_ms = record.duration_ms
    reviewer.is_error = record.is_error
    reviewer.envelope_path = record.envelope_path
    reviewer.run_id = record.run_id
    record.provenance = run_provenance(rs)
    record.run_label = rs.run_label
    record.phase_step = vocab.PHASE_PLAN_REVIEW
    append_run_record(
        record,
        phase="phase-4.5",
        branch=_git_branch(rs.framework_root),
        telemetry_path=os.path.join(rs.framework_root, "telemetry", "runs.jsonl"),
    )

    if not dry_run and record.is_error:
        raise RuntimeError(
            f"plan reviewer {reviewer_index} invocation failed; envelope "
            f"at {record.envelope_path}; aborting. (Quiet failure here is "
            f"the §1 silent-green defect shape — refuse and surface.)"
        )

    try:
        with open(record.envelope_path) as f:
            env = json.load(f)
        result_text = env.get("result") or ""
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"reviewer envelope unreadable: {e}") from None

    verdict_match = _VERDICT_RE.findall(result_text)
    verdict = verdict_match[-1].upper() if verdict_match else "UNKNOWN"

    findings = _parse_finding_block(
        label, result_text, record.run_id, record.model_id, record.family, reviewer_index
    )

    # Append to plan-level findings; telemetry goes to findings.jsonl too.
    rs.plan_findings.extend(findings)
    _append_finding_rows(
        findings, telemetry_path=os.path.join(rs.framework_root, "telemetry", "findings.jsonl")
    )

    # Panel-finding F-7: store the verdict, bound to the plan_sha256
    # the reviewer saw. This is what `reconcile_human_gate` consults
    # to decide whether `accept` is machine-permissible.
    rs.plan_reviewer_verdicts.append(
        {
            "reviewer_index": reviewer_index,
            "model_id": record.model_id,
            "family": record.family,
            "verdict": verdict,
            "plan_sha256_at_time_of_review": rs.plan_sha256,
            "is_error": record.is_error,
            "run_id": record.run_id,
        }
    )

    print(f"  reviewer {reviewer_index} verdict: {verdict}")
    print(f"  findings: {len(findings)}")
    return {"record": record, "verdict": verdict, "findings": findings}


def _append_disposition_rows(rs: RunState, findings: list[Finding],
                             disposition: str, reason: str,
                             telemetry_path: str) -> None:
    """Append ``dispositions.jsonl`` rows (SCHEMA.md §dispositions).

    A force-accept override IS a disposition: the operator saw the finding
    and chose to proceed. Recording it here is what makes
    findings-upheld-vs-overridden queryable; left only in the checkpoint
    prose, reviewer precision cannot be measured at all.
    """
    if not findings:
        return
    os.makedirs(os.path.dirname(os.path.abspath(telemetry_path)) or ".",
                exist_ok=True)
    prov = run_provenance(rs)
    with open(telemetry_path, "a") as f:
        for finding in findings:
            row = {
                "schema_version": "v3",
                "ts": now_iso(),
                "finding_id": finding.finding_id,
                "phase": "phase-4.5",
                "disposition": disposition,
                "disposition_reason": reason,
                "disposition_commit_sha": prov["pilot_head"],
                "disposition_model_id": "(operator)",
                "disposition_at": now_iso(),
                "severity": finding.severity,
                "category": finding.category,
                "source_run_id": finding.source_run_id,
                "source_model_id": finding.source_model_id,
                "run_label": prov["run_label"],
                "framework_sha": prov["framework_sha"],
                "plan_sha256": prov["plan_sha256"],
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_run_summary_row(rs: RunState, exit_code: int,
                           telemetry_path: str) -> None:
    """One ``role="run"`` row per run: how far it got and how it ended.

    Per-call rows cannot answer "where do runs die"; that needs a
    run-level record. Emitted on every exit path, including refusals.
    """
    sev_counts: dict[str, int] = {}
    for f in rs.plan_findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
    prov = run_provenance(rs)
    row = {
        "schema_version": "v3",
        "ts": now_iso(),
        "run_id": f"r-run-{int(time.time() * 1000)}",
        "phase": "phase-4.5",
        "branch": prov["framework_branch"],
        "role": "run",
        "model_id": "(n/a)",
        "provider": "(n/a)",
        "family": "(n/a)",
        "exit_code": exit_code,
        "run_status": rs.status.value if rs.status else "UNKNOWN",
        "status_message": rs.status_message,
        "reached_phase_step": rs.reached_phase_step,
        "findings_total": len(rs.plan_findings),
        "findings_by_severity": sev_counts,
        "plan_reviewer_verdicts": [
            {"model_id": v.get("model_id"), "verdict": v.get("verdict"),
             "bound_to_plan": v.get("plan_sha256_at_time_of_review") == rs.plan_sha256}
            for v in rs.plan_reviewer_verdicts
        ],
        "chunk_statuses": [
            {"chunk_id": c.chunk_id,
             "status": c.status.value if c.status else None,
             "gate_decision": c.gate_decision.value if c.gate_decision else None,
             "retry_count": c.retry_count}
            for c in rs.chunks
        ],
        "force_accept_disposition": rs.force_accept_disposition,
        # A test-design cycle and an executor-retry cycle cost different
        # seats, so counting them together makes seat/model comparisons
        # wrong. ``chunk_statuses[].retry_count`` is the executor budget;
        # these rows carry the test-design budget beside it. Additive —
        # v1/v2 readers ignore the keys.
        "test_design_retries_total": sum(c.test_design_retry_count for c in rs.chunks),
        "reject_cycles_by_chunk": [
            {"chunk_id": c.chunk_id,
             "executor_retry_count": c.retry_count,
             "test_design_retry_count": c.test_design_retry_count,
             "last_rejection_kind": c.rejection_kind,
             "executor_feedback_source": c.rejection_feedback_source}
            for c in rs.chunks
        ],
    }
    row.update(prov)
    os.makedirs(os.path.dirname(os.path.abspath(telemetry_path)) or ".",
                exist_ok=True)
    with open(telemetry_path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_finding_rows(findings: list[Finding], telemetry_path: str) -> None:
    """Append findings to ``telemetry/findings.jsonl`` per §10."""
    if not findings:
        return
    os.makedirs(os.path.dirname(os.path.abspath(telemetry_path)) or ".", exist_ok=True)
    with open(telemetry_path, "a") as f:
        for finding in findings:
            row = {
                "schema_version": "v2",
                "ts": now_iso(),
                "finding_id": finding.finding_id,
                "phase": "phase-4.5",
                "surface": finding.evidence[0] if finding.evidence else "(no-evidence)",
                "category": finding.category,
                "severity": finding.severity,
                "source_role": finding.source_role,
                "source_run_id": finding.source_run_id,
                "source_model_id": finding.source_model_id,
                "source_family": finding.source_family,
                "panel_size_at_surfacing": 2,
                "first_seen_in_panel_position": finding.first_seen_in_panel_position,
                "raw_text_first_240": finding.claim[:240],
                "plan_section": finding.plan_section,
                "risk_if_ignored": finding.risk_if_ignored,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ── step: preflight family guard ─────────────────────────────────────────


def preflight_family_guard(cfg: Config, rs: RunState) -> None:
    """Run the §17.2 family-guard preflight; halt on violation."""
    assignments = cfg.to_role_assignments()
    # Augment with the resolved values from any prior runs (re-running
    # the guard post-resolution surfaces silent admissions).
    out = check_family_separation(
        *assignments,
        allow_test_author_collide=cfg.allow_test_author_collide,
        allow_single_family=cfg.allow_single_family,
    )
    rs.family_guard_passed = out.ok
    rs.family_guard_notes = "; ".join(out.notes + [v for v in out.violations if v])
    if not out.ok and cfg.fail_closed:
        print("§17.2 family guard FAILED — refusing to launch.", file=sys.stderr)
        for v in out.violations:
            print(f"  - {v}", file=sys.stderr)
        raise SystemExit(2)
    elif not out.ok:
        print("§17.2 family guard FAILED but fail-closed disabled; continuing.", file=sys.stderr)
    else:
        print("§17.2 family guard OK")


def recheck_family_guard_post_resolution(cfg: Config, rs: RunState, which: str) -> None:
    """Re-run §17.2 guard with *resolved* families substituted in.

    Panel-finding F-2: FamilyGuardOutcome's docstring promised a
    post-resolution re-check that did not exist. This implements
    it: after the planner + reviewer(s) + executor have resolved
    their actual model/family, the guard runs again so a model
    that the operator *configured* but the channel *resolved to*
    a different family still gets the §4/§17.2 fail-closed treatment.

    `which` is one of: "after-plan-review" | "after-executor".
    """
    assignments = rs.all_role_assignments()
    # Substitute resolved_family for the planner + reviewers + executor
    # wherever that role has one bound to a family OTHER than the
    # curated map's projection. This catches the operator-vs-resolved
    # mismatch shape.
    out = check_family_separation(
        *assignments,
        allow_test_author_collide=cfg.allow_test_author_collide,
        allow_single_family=cfg.allow_single_family,
    )
    if not out.ok:
        rs.family_guard_passed = False
        rs.family_guard_notes = f"post-resolution re-check ({which}) failed; " + "; ".join(
            out.violations
        )
        if cfg.fail_closed:
            print(
                f"§17.2 family guard FAILED post-resolution ({which}) — refusing.",
                file=sys.stderr,
            )
            for v in out.violations:
                print(f"  - {v}", file=sys.stderr)
            raise SystemExit(2)
        print(
            f"§17.2 family guard FAILED post-resolution ({which}); "
            f"fail-closed disabled; continuing.",
            file=sys.stderr,
        )
    else:
        rs.family_guard_passed = True
        rs.family_guard_notes = f"§17.2 family guard OK at pref + post-resolution ({which})"


# ── finding rendering ────────────────────────────────────────────────────


def _clip(text: str, limit: int) -> str:
    """One-line, length-capped rendering of reviewer prose."""
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def _format_finding_for_human(
    finding: Finding,
    *,
    detailed: bool = False,
    indent: str = "    ",
) -> str:
    """Render one finding so a reader cannot mistake it for an approval.

    A reviewer finding carries both the plan's assertion (``claim``) and
    the defect (``risk_if_ignored``). Printing the claim alone produces
    lines that read as praise under a REFUSED banner — observed live,
    where "The second command is a 'wider backend suite' regression
    gate" was rendered as the reason the gate refused. The risk leads;
    the claim is labelled as the plan's words, not the reviewer's.

    ``risk_if_ignored`` is empty on findings from older runs and from
    seats that do not emit it, so ``claim`` remains the fallback.
    """
    inner = indent + "  "
    sev = finding.severity.upper()
    if detailed and finding.category:
        sev = f"{sev}/{finding.category}"
    head = f"{indent}[{sev}] {finding.finding_id}"
    if finding.source_model_id:
        head += f" ({finding.source_model_id})"
    if finding.plan_section:
        head += f" in {_clip(finding.plan_section, 80)}"
    if finding.status and finding.status != "open":
        # Only open findings block §5.3, so a non-open one listed next to
        # open ones must say which it is.
        head += f" [{finding.status}]"
    lines = [head]
    risk_width = 400 if detailed else 200
    if finding.risk_if_ignored:
        lines.append(f"{inner}risk: {_clip(finding.risk_if_ignored, risk_width)}")
        if detailed and finding.claim:
            lines.append(f"{inner}plan claims: {_clip(finding.claim, 200)}")
    else:
        # No risk field: say "finding", never "risk", so the fallback
        # line is not read as a risk statement the reviewer never made.
        lines.append(f"{inner}finding: {_clip(finding.claim, risk_width)}")
    if detailed and finding.recommended_change:
        lines.append(f"{inner}fix: {_clip(finding.recommended_change, 300)}")
    return "\n".join(lines)


# ── step: reconcile (human gate) ────────────────────────────────────────


def _apply_force_accept_disposition(
    rs: RunState,
    *,
    exit_code: int,
    force_accept_reason: str,
    checkpoint_path: str | None = None,
) -> None:
    """Record an explicit operator disposition for a §5.3 force-accept override.

    Builds the audit record (which findings were overridden + the operator's
    reason), stamps it on ``RunState``, appends telemetry rows, and surfaces
    the disposition to stderr. If ``checkpoint_path`` is set, the disposition
    is also persisted to a checkpoint before the gate proceeds — the caller
    decides whether this override branch is resumable.
    """
    open_blockers = [
        f for f in rs.plan_findings
        if f.status == "open" and f.severity in ("blocker", "high")
    ]
    disposition_lines = [
        f"FORCE-ACCEPT DISPOSITION — {now_iso()}",
        f"Operator reason: {force_accept_reason or '(not provided)'}",
        f"§5.3 refusal code: {exit_code}",
    ]
    if exit_code == 4:
        disposition_lines.append(
            f"Overridden blocker|high findings ({len(open_blockers)}):"
        )
        for f in open_blockers:
            disposition_lines.extend(
                _format_finding_for_human(f, detailed=True, indent="  ").splitlines()
            )
    elif exit_code == 5:
        disposition_lines.append(
            "Overridden: no reviewer APPROVE bound to current plan_sha256."
        )
    rs.force_accept = True
    rs.force_accept_reason = force_accept_reason
    rs.force_accept_disposition = "\n".join(disposition_lines)
    _append_disposition_rows(
        rs,
        open_blockers,
        "overridden",
        force_accept_reason or "(not provided)",
        os.path.join(rs.framework_root, "telemetry", "dispositions.jsonl"),
    )
    print(
        f"  [force-accept] §5.3 refused (exit {exit_code}); "
        f"operator override active. Disposition recorded.",
        file=sys.stderr,
    )
    for line in disposition_lines:
        print(f"    {line}", file=sys.stderr)
    if checkpoint_path:
        write_checkpoint(rs, checkpoint_path)


def reconcile_human_gate(
    rs: RunState,
    *,
    evidence_dir: str,
    dry_run: bool,
    gate_auto_decide: bool = False,
    unattended: bool = False,
    no_dry_auto_decide: bool = False,
    force_accept: bool = False,
    force_accept_reason: str = "",
) -> ReconcileDecision:
    """Pause for the human operator's reconciliation decision.

    PRD §5.3 + §6: the loop runner pauses here and reads ``stdin``.
    Per OPERATING-RULES §11 + §9 — the reconcile gate is the operator
    seat, NOT a thing the script decides.

    Wire format (stdin, single line):
        accept
        reject  [<reason>]
        amend   [<reason>]
    Empty input = abort.

    Pass-r3 findings H-2 / H-13 / H-14: the four flags are read from
    explicit parameters, NOT from ``sys.argv``. main() sets them from
    parsed argv + env vars before the call. The contract:

    - ``dry_run=True``: simulated ACCEPT. The gate rubber-stamps the
      dry-run as a witness; the per-chunk pipeline still runs in
      simulated mode. Override via ``--no-dry-auto-decide`` to make
      a dry-run actually pause for human input.
    - ``gate_auto_decide=True``: bypass the stdin pause; §5.3
      preconditions still run. Used by ``--non-interactive``,
      ``--unattended``, ``--skip-reconcile``, ``--gate-auto-decide``.
    - ``unattended=True``: same as gate_auto_decide, but on §5.3
      refusal write a checkpoint at
      ``<evidence_dir>/checkpoint.json`` and SystemExit(4/5).
      Operator resumes via ``--resume-from``.
    - ``force_accept=True`` (unattended only): when §5.3 preconditions
      refuse (open blocker|high findings), record an explicit operator
      disposition in the checkpoint and proceed with ACCEPT instead of
      refusing. The disposition captures which findings were overridden
      and the operator's reason, preserving the audit trail. This is
      the "operator overrides the gate" escape hatch — it must be
      deliberately set and carries an auditable record.
    """
    rs.status = RunStatus.AWAITING_RECONCILIATION
    packet_path = os.path.join(evidence_dir, "reconcile-packet.txt")
    _write_reconcile_packet(rs, packet_path)

    print()
    print("═" * 64)
    print("  RECONCILE GATE — human pause")
    print(f"  packet: {packet_path}")
    # main() increments plan_round before the round runs, so it is
    # already 1-based by the time the gate reports it.
    print(f"  round: {rs.plan_round} / max {rs.max_review_rounds}")
    print(f"  findings ({len(rs.plan_findings)}):")
    for f in rs.plan_findings[-10:]:
        print(_format_finding_for_human(f))
    print()
    print("  ── plan_doc ──")
    print(f"    path: {rs.plan_doc_path}")
    print(f"    sha256: {rs.plan_sha256}")
    print()
    print("  Decision (single line on stdin):")
    print("    accept                       — accept the plan, proceed to chunking")
    print("    reject  <reason>             — reject; loop back to planner")
    print("    amend   <reason>             — approve with intent to amend; treated as accept+note")
    print("    (empty / EOF = abort)")
    print("═" * 64)

    if dry_run and not no_dry_auto_decide:
        print(
            "  [dry-run] auto-decision: accept (non-committal — "
            "dry-run produces a simulated ACCEPT. Live mode honors "
            "--non-interactive / --unattended separately.)"
        )
        return ReconcileDecision.ACCEPT

    # Pass-r3 finding H-2 fix: gate auto-decide path is opt-in via
    # main()'s parsing (no sys.argv reads). On §5.3 refusal:
    #   gate_auto_decide + unattended=False (== --non-interactive): SystemExit.
    #   gate_auto_decide + unattended=True  (== --unattended): SystemExit + checkpoint.
    if gate_auto_decide:
        try:
            _enforce_5_3_preconditions(rs)
        except SystemExit as e:
            # --force-accept override: when the operator has
            # explicitly set --force-accept in unattended mode, the
            # gate records an explicit disposition (which findings
            # were overridden + the operator's reason) and proceeds
            # with ACCEPT. The disposition is stamped on the RunState
            # so the checkpoint captures it (§11 audit trail).
            if force_accept and unattended and e.code in (4, 5):
                _apply_force_accept_disposition(
                    rs,
                    exit_code=e.code,
                    force_accept_reason=force_accept_reason,
                    checkpoint_path=os.path.join(evidence_dir, "checkpoint.json"),
                )
                return ReconcileDecision.ACCEPT

            if unattended and e.code == 4:
                # §5.3 forbids ACCEPTING a plan with open blocker|high
                # findings; it does not forbid iterating. Refusing on
                # the first refusal spent one of the configured review
                # rounds and then quit, so an ordinary adversarial cycle
                # — plan, get findings, revise, re-review — could never
                # complete unattended. REJECT loops the planner, which
                # reads rs.plan_findings on its next invocation.
                open_bh = len(
                    [
                        f for f in rs.plan_findings
                        if f.status == "open" and f.severity in ("blocker", "high")
                    ]
                )
                if rs.plan_round < rs.max_review_rounds:
                    rs.status_message = (
                        f"reject: §5.3 refused with {open_bh} open blocker|high "
                        f"finding(s) at review round {rs.plan_round} of "
                        f"{rs.max_review_rounds}; looping the planner"
                    )
                    print(
                        f"  [unattended] §5.3 refused (exit 4) with {open_bh} open "
                        f"blocker|high finding(s) at review round {rs.plan_round} "
                        f"of {rs.max_review_rounds}; rounds remain, so the plan is "
                        f"REJECTED back to the planner (looping is not accepting).",
                        file=sys.stderr,
                    )
                    return ReconcileDecision.REJECT
                cp_path = os.path.join(evidence_dir, "checkpoint.json")
                write_checkpoint(rs, cp_path)
                print(
                    f"  [unattended] §5.3 refused (exit 4) with {open_bh} open "
                    f"blocker|high finding(s); review rounds exhausted "
                    f"(round {rs.plan_round} of {rs.max_review_rounds}); "
                    f"checkpoint at {cp_path}; resume with --resume-from",
                    file=sys.stderr,
                )
            elif unattended:
                cp_path = os.path.join(evidence_dir, "checkpoint.json")
                write_checkpoint(rs, cp_path)
                print(
                    f"  [unattended] refused (exit {e.code}); "
                    f"checkpoint at {cp_path}; resume with --resume-from",
                    file=sys.stderr,
                )
            else:
                print(
                    f"  [non-interactive] refused (exit {e.code}); no checkpoint",
                    file=sys.stderr,
                )
            raise
        print(
            f"  [{'unattended' if unattended else 'non-interactive'}] "
            f"§5.3 preconditions met; auto-decision: accept"
        )
        return ReconcileDecision.ACCEPT

    try:
        line = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  abort.")
        raise SystemExit(1) from None
    if not line:
        print("  abort.")
        raise SystemExit(1)

    head, _, rest = line.partition(" ")
    head = head.lower()
    if head == "accept":
        # Panel-finding F-7: machine-check §5.3 convergence preconditions
        # BEFORE honoring ``accept``. Without this, the human seat is a
        # rubber stamp — Phase 0's KNOWN silent-green defect.
        try:
            _enforce_5_3_preconditions(rs)
        except SystemExit as e:
            if force_accept and e.code in (4, 5):
                _apply_force_accept_disposition(
                    rs,
                    exit_code=e.code,
                    force_accept_reason=force_accept_reason,
                )
                return ReconcileDecision.ACCEPT
            raise
        return ReconcileDecision.ACCEPT
    if head == "amend":
        rs.status_message = f"amend: {rest}".strip()
        return ReconcileDecision.AMEND
    if head == "reject":
        rs.status_message = f"reject: {rest}".strip()
        return ReconcileDecision.REJECT
    print(f"  unknown decision {head!r}; treating as abort")
    raise SystemExit(1)


# ── §5.3 machine-check helpers (panel-finding F-7) ───────────────────────


def _enforce_5_3_preconditions(rs: RunState) -> None:
    """Refuse ``accept`` while §5.3 convergence preconditions fail.

    Two checks (panel-finding F-7):
      1. zero open blocker|high findings (status='open')
      2. at least one reviewer verdict=APPROVE bound to the current
         plan_sha256 (the §5.3 "exact plan hash" rule)

    Raises SystemExit(4) for open blocker|high, SystemExit(5) for
    no bound APPROVE, SystemExit(0) on success (no exception =
    preconditions met; the gate returns ReconcileDecision.ACCEPT
    either way).
    """
    open_blocker_or_high = [
        f for f in rs.plan_findings if f.status == "open" and f.severity in ("blocker", "high")
    ]
    if open_blocker_or_high:
        print(
            f"  REFUSED: {len(open_blocker_or_high)} open blocker|high "
            f"finding(s); §5.3 forbids accepting the plan while "
            f"blocker|high are open. Use 'amend <reason>' to record an "
            f"explicit disposition, or 'reject' to loop the planner.",
            file=sys.stderr,
        )
        for f in open_blocker_or_high:
            print(_format_finding_for_human(f, detailed=True), file=sys.stderr)
        raise SystemExit(4)

    bound_approves = [
        v
        for v in rs.plan_reviewer_verdicts
        if v["verdict"] in ("APPROVE", "APPROVE-WITH-NITS")
        and v["plan_sha256_at_time_of_review"] == rs.plan_sha256
    ]
    if not bound_approves:
        print(
            f"  REFUSED: no reviewer returned APPROVE bound to "
            f"plan_sha256={rs.plan_sha256[:16]}… §5.3 requires at "
            f"least one APPROVE against the current plan hash. "
            f"Use 'amend <reason>' or 'reject'.",
            file=sys.stderr,
        )
        raise SystemExit(5)


def _write_reconcile_packet(rs: RunState, path: str) -> None:
    """Write the reconciliation packet the operator reads."""
    lines = [
        f"RECONCILE PACKET — run_id={rs.run_id}",
        f"started_at={rs.started_at}",
        f"plan_doc={rs.plan_doc_path}",
        f"plan_sha256={rs.plan_sha256}",
        f"plan_round={rs.plan_round} / max={rs.max_review_rounds}",
        f"validators configured: {[v.pinned_model_id for v in rs.validators]}",
        f"findings ({len(rs.plan_findings)}):",
    ]
    for f in rs.plan_findings:
        lines.append(_format_finding_for_human(f, detailed=True, indent="  "))
    if not rs.plan_findings:
        lines.append("  (no findings — clean null per PRD §13)")
    lines.append("")
    lines.append("Decision: accept | reject [<reason>] | amend [<reason>]")
    with open(path, "w") as f:
        f.write("\n".join(lines))


# ── step: chunking ───────────────────────────────────────────────────────


def load_chunks(rs: RunState, chunks_file: str) -> list[ChunkState]:
    """Read the chunks JSON file and materialise the chunk list."""
    if not os.path.isfile(chunks_file):
        raise SystemExit(f"--chunks-file not found: {chunks_file}")
    with open(chunks_file) as f:
        data = json.load(f)
    if isinstance(data, dict):
        # Allow {"chunks": [...]} envelope
        chunks = data.get("chunks") or data.get("items") or []
    else:
        chunks = data
    if not isinstance(chunks, list):
        raise SystemExit(f"--chunks-file must be a list or {{'chunks': [...]}}: {chunks_file}")
    out: list[ChunkState] = []
    for c in chunks:
        cs = ChunkState(
            chunk_id=c["chunk_id"],
            scope=c["scope"],
            observable_criteria=c.get("observable_criteria", []),
            allowed_files=c.get("allowed_files", []),
            locked_test_files=c.get("locked_test_files", []),
            commands=c.get("commands", []),
            rollback=c.get("rollback", ""),
        )
        # ``accepted_assertion`` is the predicate phrase used by
        # ``validate_red.py`` and ``verify-green.py``. If the chunk
        # spec doesn't surface it explicitly, we use the first observable
        # criterion as the default — but the orchestrator's tests cover
        # this default.
        cs.accepted_assertion = c.get("accepted_assertion") or (
            cs.observable_criteria[0] if cs.observable_criteria else cs.scope
        )
        # Per-chunk verify_mode: set from the chunk JSON if present,
        # otherwise inherit from the global Config.verify_mode flag.
        cs.verify_mode = bool(c.get("verify_mode", False)) or rs.verify_mode
        out.append(cs)
    return out


# ── step: per-chunk run + retry policy ───────────────────────────────────


def run_chunk_with_retries(
    rs: RunState, chunk: ChunkState, evidence_output_dir: str, dry_run: bool, cfg: Config
) -> ChunkState:
    """Run a chunk's inner loop. On REJECT, retry up to retry_threshold
    by feeding rejection feedback back to the executor.

    Per PRD §5.7:
      - 1 retry by default (retry_threshold=1)
      - Above the threshold → ``HUMAN_DECISION`` and the run pauses.

    ``REJECT_TEST`` is routed to the test-designer instead, on its own
    budget of ``retry_threshold`` bounces: an inadequate locked test is
    not the executor's failure, so a test-design cycle must not spend the
    executor's retries, and it must still be bounded rather than looping
    while the panel keeps rejecting each regenerated test.
    """
    attempts_left = rs.retry_threshold + 1  # first try + retries
    # Bounces already spent (e.g. before a pause/resume) stay spent.
    test_design_bounces_left = max(0, rs.retry_threshold - chunk.test_design_retry_count)
    while attempts_left > 0:
        chunk.status = (
            ChunkStatus.TEST_DESIGNING if chunk.retry_count == 0 else ChunkStatus.RETRYING
        )
        attempts_left -= 1

        run_chunk_inner(rs, chunk, evidence_output_dir, dry_run, cfg)

        # Re-evaluate the gate decision.
        if chunk.gate_decision in (GateDecision.ACCEPT, GateDecision.ACCEPT_WITH_NITS):
            chunk.status = ChunkStatus.ACCEPTED
            chunk.rejection_feedback = []  # cleared on ACCEPT
            # rejection_feedback_source persists: it records what the last
            # retry's prompt carried, so the run summary can answer "did
            # feeding the finding help?" even after the chunk accepts.
            return chunk

        if chunk.gate_decision == GateDecision.STOP:
            chunk.status = ChunkStatus.HUMAN_DECISION
            rs.status_message = f"STOP in chunk {chunk.chunk_id}: {chunk.gate_reason}"
            return chunk

        # SPEC_OR_TEST_BLOCKED: the executor claims the contract itself
        # is at fault. This is NOT a retryable rejection — retrying the
        # executor burns credits on an impossible task. Return the chunk
        # immediately so the caller writes a checkpoint and exits with
        # the distinct BLOCKED code.
        if chunk.status == ChunkStatus.BLOCKED:
            return chunk

        # REJECT or similar — retry if we have attempts left.
        # gate_decision can still be None when the chunk never reached the
        # validation gate (e.g. RED_REJECTED); report the status instead of
        # dereferencing None.
        decision_label = (chunk.gate_decision.value if chunk.gate_decision
                          else f"NO-GATE/{chunk.status.value}")

        if chunk.rejection_kind == REJECTION_TEST:
            # Test-directed rejection: the test-designer runs again, and
            # the round is charged to the test-design budget rather than
            # the executor's (hence attempts_left is restored).
            # Clear any stale implementation feedback so a previous
            # REJECT_IMPLEMENTATION's findings do not bleed into the
            # executor's prompt on a later test-design round.
            chunk.rejection_feedback = []
            chunk.rejection_feedback_source = ""
            if test_design_bounces_left > 0:
                test_design_bounces_left -= 1
                chunk.test_design_retry_count += 1
                attempts_left += 1
                chunk.status = ChunkStatus.RETRYING
                print(
                    f"  REJECT_TEST ({decision_label}); routing to the "
                    f"test-designer, bounce "
                    f"{chunk.test_design_retry_count}/{rs.retry_threshold}"
                )
                continue
            chunk.status = ChunkStatus.HUMAN_DECISION
            rs.status_message = (
                f"chunk {chunk.chunk_id} reached HUMAN_DECISION: test-design "
                f"retry budget exhausted after {chunk.test_design_retry_count} "
                f"regeneration(s) — the validator panel returned REJECT_TEST "
                f"against every locked test. The chunk spec and the test it "
                f"asks for are the thing to reconcile, not the code: "
                f"{chunk.gate_reason or '(no gate reason)'}"
            )
            return chunk
        if attempts_left > 0:
            chunk.retry_count += 1
            # rejection_feedback was already set by run_chunk_inner when
            # the validator panel rejected the implementation (carrying
            # the rejecting seats' own finding text). Only fall back to
            # the gate reason when no validator classification ran — e.g.
            # RED_REJECTED, which sets gate_decision=REJECT before the
            # validation step and never reaches the formatter.
            if not chunk.rejection_feedback:
                chunk.rejection_feedback = [chunk.gate_reason or rs.status_message]
                chunk.rejection_feedback_source = FEEDBACK_SOURCE_GATE_REASON
            print(
                f"  REJECT ({decision_label}); retrying "
                f"({rs.retry_threshold + 1 - attempts_left}/{rs.retry_threshold + 1})"
            )
            continue

        # No retries left — escalate
        chunk.status = ChunkStatus.HUMAN_DECISION
        rs.status_message = (
            f"chunk {chunk.chunk_id} reached HUMAN_DECISION after {chunk.retry_count} retries"
        )
        return chunk
    # Shouldn't reach here, but safety
    chunk.status = ChunkStatus.HUMAN_DECISION
    return chunk


def _read_pilot_spec_text(rs: RunState) -> str:
    """Return the pilot spec text for role prompts, or a placeholder."""
    if rs.pilot_spec_file:
        try:
            with open(rs.pilot_spec_file) as f:
                return f.read()
        except OSError:
            pass
    return "(no pilot spec file configured)"


def run_chunk_inner(
    rs: RunState, chunk: ChunkState, evidence_output_dir: str, dry_run: bool, cfg: Config
) -> None:
    """The per-chunk inner loop:
    test-designer → lock → valid-red → executor → verify-green →
    evidence → validation → gate decision.
    """
    # 1. test-designer writes the test. The chunk spec must NAME the
    # locked test file; a chunk with no named file is unspecifiable
    # (nothing to lock, nothing to grep for the accepted assertion).
    if not chunk.locked_test_files:
        raise RuntimeError(
            f"chunk {chunk.chunk_id} has no locked_test_files; the chunk "
            f"spec must name the test file the test_designer is to "
            f"author. See phase-4.5/KNOWN-ISSUES.md."
        )

    # A test-directed rejection (REJECT_TEST) from the previous round
    # means the locked test does not lock what the chunk claims. The
    # response is to regenerate the test — re-running the executor
    # against the same inadequate test cannot fix that. The superseded
    # test is archived out of the pilot tree, which is what makes the
    # auto-fire path below re-author it.
    redesign_round = chunk.rejection_kind == REJECTION_TEST
    implementation_retry_round = chunk.rejection_kind == REJECTION_IMPLEMENTATION
    chunk.rejection_kind = ""
    if redesign_round:
        moved = archive_superseded_test(
            chunk,
            rs,
            evidence_output_dir=evidence_output_dir,
            round_index=chunk.test_design_retry_count,
        )
        print(
            f"  REJECT_TEST → routing back to the test-designer for "
            f"{chunk.chunk_id}; superseded evidence preserved: "
            f"{sorted(moved.values()) or '(nothing to archive)'}"
        )

    # The named file may be pre-authored by a human (skip the droid
    # round) or may not exist yet (fire the test_designer). dry_run
    # short-circuits: invoke_test_designer writes no file under
    # dry_run, and lock_test / validate_red synthesize their results
    # without touching disk, so there is nothing to author — except on
    # a redesign round, where the whole point of the round is the
    # designer call.
    test_file_abs = os.path.join(rs.pilot_root, chunk.locked_test_files[0])
    if redesign_round or (not dry_run and not os.path.isfile(test_file_abs)):
        chunk.status = ChunkStatus.TEST_DESIGNING
        rs.reached_phase_step = "test-design"
        td_prompt_path = os.path.join(evidence_output_dir, f"{chunk.chunk_id}-td-prompt.md")
        td_envelope_path = os.path.join(
            evidence_output_dir, f"{chunk.chunk_id}-td-envelope.json"
        )
        render_test_designer_prompt(
            chunk, rs, _read_pilot_spec_text(rs), output_path=td_prompt_path
        )
        td_result = invoke_test_designer(
            chunk,
            rs,
            evidence_output_dir=evidence_output_dir,
            rendered_prompt_path=td_prompt_path,
            envelope_path=td_envelope_path,
            dry_run=dry_run,
            phase_step=(
                vocab.PHASE_TEST_DESIGN_RERUN
                if redesign_round
                else vocab.PHASE_TEST_DESIGN
            ),
        )
        # Parse the ACCEPTED_ASSERTION from the designer's result text.
        # The chunk spec may already carry one (from chunks_file); the
        # designer's emit overrides it — the designer is the authority
        # on what phrase appears in the test it just wrote.
        parsed = parse_accepted_assertion(td_result.get("result_text", ""))
        if parsed:
            chunk.accepted_assertion = parsed
        elif not chunk.accepted_assertion:
            print(
                f"  [warn] test-designer for chunk {chunk.chunk_id} did "
                f"not emit ACCEPTED_ASSERTION and no assertion was "
                f"pre-set; lock_test / validate_red will use the chunk "
                f"scope as a fallback.",
                file=sys.stderr,
            )

        if not dry_run and (
            not os.path.isfile(test_file_abs) or os.path.getsize(test_file_abs) == 0
        ):
            raise RuntimeError(
                f"test_designer for chunk {chunk.chunk_id} reported no error "
                f"but wrote no locked test at {test_file_abs} — refusing to "
                f"lock a missing test (silent-green is the defect shape). "
                f"Envelope: {td_envelope_path}; stderr: "
                f"{os.path.join(evidence_output_dir, 'stderr-test-designer.log')}"
            )

    # 2. lock
    chunk.status = ChunkStatus.LOCKING
    lock_test(
        chunk,
        framework_root=rs.framework_root,
        pilot_root=rs.pilot_root,
        pilot_python=rs.pilot_python,
        accepted_assertion=chunk.accepted_assertion,
        dry_run=dry_run,
    )

    # 3. valid-red
    chunk.status = ChunkStatus.VALIDATING_RED
    rs.reached_phase_step = "red-gate"
    already_green = False
    try:
        validate_red(
            chunk,
            framework_root=rs.framework_root,
            pilot_root=rs.pilot_root,
            pilot_python=rs.pilot_python,
            dry_run=dry_run,
        )
    except RuntimeError as e:
        if chunk.verify_mode or redesign_round or implementation_retry_round:
            # A verify-and-harden chunk, a regenerated test, and an
            # implementation retry may all be GREEN at HEAD. In particular,
            # REJECT_IMPLEMENTATION happens only after verify_green succeeds,
            # so GREEN is the required starting state for its retry rather
            # than an invalid RED to route elsewhere. Confirm GREEN before
            # relaxing the gate; every other validate-red failure remains a
            # refusal.
            relaxation = (
                "implementation-retry"
                if implementation_retry_round
                else "test-redesign"
                if redesign_round
                else "verify-mode"
            )
            print(
                f"  [{relaxation}] validate_red raised: {e}. "
                f"Checking whether the test is already GREEN at HEAD "
                f"(expected existing implementation → verify-and-harden pass).",
                file=sys.stderr,
            )
            try:
                verify_green(chunk,
                             framework_root=rs.framework_root,
                             pilot_root=rs.pilot_root,
                             pilot_python=rs.pilot_python,
                             dry_run=dry_run)
                already_green = True
                print(
                    f"  [{relaxation}] test already GREEN at HEAD for "
                    f"chunk {chunk.chunk_id}; executor will run as "
                    f"verify-and-harden pass.",
                    file=sys.stderr,
                )
            except RuntimeError:
                # verify_green also failed — the test is broken for a
                # reason other than "already passing." This is still
                # RED_REJECTED, even in verify mode.
                chunk.status = ChunkStatus.RED_REJECTED
                rs.status_message = (
                    f"chunk {chunk.chunk_id} RED_REJECTED ({relaxation}): "
                    f"test not RED and not GREEN — {e}"
                )
                chunk.gate_decision = GateDecision.REJECT
                chunk.gate_reason = rs.status_message
                return
        else:
            chunk.status = ChunkStatus.RED_REJECTED
            rs.status_message = (
                f"chunk {chunk.chunk_id} RED_REJECTED: {e}"
            )
            chunk.gate_decision = GateDecision.REJECT
            chunk.gate_reason = rs.status_message
            return

    # 4. executor. Skipped on a redesign round whose regenerated test is
    # already GREEN: the rejection was against the test, the
    # implementation under review is unchanged, and it already satisfies
    # the new contract — so there is nothing for the most expensive seat
    # in the pipeline to do. A regenerated test that is RED still needs it.
    if redesign_round and already_green:
        print(
            f"  [reject-test] regenerated test is already GREEN against the "
            f"preserved implementation for chunk {chunk.chunk_id}; skipping "
            f"the executor seat and re-validating."
        )
    else:
        chunk.status = ChunkStatus.EXECUTING
        rs.reached_phase_step = "execute"
        ex_prompt_path = os.path.join(evidence_output_dir, f"{chunk.chunk_id}-ex-prompt.md")
        render_executor_prompt(chunk, rs, output_path=ex_prompt_path,
                               verify_and_harden=already_green or chunk.verify_mode)
        ex_result = invoke_executor(
            chunk,
            rs,
            evidence_output_dir=evidence_output_dir,
            rendered_prompt_path=ex_prompt_path,
            envelope_path=os.path.join(evidence_output_dir, f"{chunk.chunk_id}-ex-envelope.json"),
            dry_run=dry_run,
        )
        recheck_family_guard_post_resolution(cfg, rs, "after-executor")

        # SPEC_OR_TEST_BLOCKED: the executor claims the locked test is
        # contradictory or the spec is unimplementable. This is NOT a
        # REJECT_IMPLEMENTATION — it is a claim that the contract itself
        # is at fault. Do NOT call verify_green (it would crash with
        # RuntimeError: GREFUSED against an empty/unchanged diff), do NOT
        # retry the executor, and do NOT produce evidence or validate.
        # The claim must be adjudicated by the operator or routed to the
        # test-designer; the runner exits with a distinct code so that
        # routing is automatable.
        if _is_spec_or_test_blocked(ex_result.get("result_text") or ""):
            chunk.status = ChunkStatus.BLOCKED
            chunk.gate_decision = GateDecision.REJECT
            ex_envelope = os.path.join(
                evidence_output_dir, f"{chunk.chunk_id}-ex-envelope.json"
            )
            chunk.gate_reason = (
                f"SPEC_OR_TEST_BLOCKED: executor claims the locked test or "
                f"spec is unimplementable for chunk {chunk.chunk_id}. "
                f"Rationale in the executor envelope: {ex_envelope}. "
                f"This claim must be adjudicated by the operator or routed "
                f"to the test-designer — do NOT retry the executor."
            )
            rs.status_message = chunk.gate_reason
            print(
                f"  [BLOCKED] {chunk.gate_reason}",
                file=sys.stderr,
            )
            return

    # 5. verify-green
    chunk.status = ChunkStatus.VERIFYING_GREEN
    rs.reached_phase_step = "verify-green"
    verify_green(
        chunk,
        framework_root=rs.framework_root,
        pilot_root=rs.pilot_root,
        pilot_python=rs.pilot_python,
        dry_run=dry_run,
    )

    # 6. evidence
    chunk.status = ChunkStatus.EVIDENCING
    bundle_path = os.path.join(evidence_output_dir, f"{chunk.chunk_id}-bundle.json")
    # Derived once and threaded to both steps: the validation step re-produces
    # the bundle at the same path, so if the two disagree about the regression
    # command the second production silently wins.
    full_suite_command = chunk_full_suite_command(chunk)
    produce_evidence(
        chunk,
        framework_root=rs.framework_root,
        pilot_root=rs.pilot_root,
        pilot_python=rs.pilot_python,
        evidence_output_path=bundle_path,
        dry_run=dry_run,
        full_suite_command=full_suite_command,
    )

    # 7. validation
    chunk.status = ChunkStatus.VALIDATING
    rs.reached_phase_step = "validate"
    backend_result = run_validators(
        chunk,
        rs,
        evidence_output_dir=evidence_output_dir,
        dry_run=dry_run,
        full_suite_command=full_suite_command,
    )
    chunk.gate_decision = backend_result.gate
    chunk.gate_reason = backend_result.reason
    # The gate collapses every REJECT* verdict to one REJECT; which seat
    # the rejection is directed at survives only in the per-validator
    # verdicts, so classify here and let run_chunk_with_retries route on it.
    validators = getattr(backend_result, "validators", [])
    chunk.rejection_kind = classify_rejection(validators)
    if chunk.rejection_kind == REJECTION_TEST:
        chunk.test_design_feedback = [format_test_rejection_feedback(backend_result)]
    elif chunk.rejection_kind == REJECTION_IMPLEMENTATION:
        chunk.rejection_feedback = [format_implementation_rejection_feedback(backend_result)]
        chunk.rejection_feedback_source = (
            FEEDBACK_SOURCE_VALIDATOR_FINDING
            if implementation_rejection_has_finding(backend_result)
            else FEEDBACK_SOURCE_GATE_REASON
        )


# ── step: branch + commit ───────────────────────────────────────────────


def commit_chunk_change(
    rs: RunState, chunk: ChunkState, evidence_output_dir: str, run_evidence_dir: str | None = None
) -> None:
    """One commit per accepted chunk on the output branch.

    Operator rule (OPERATING-RULES §18 / AGENTS.md): commits are the
    baton across agents / humans. The runner never ``git push`` (per
    safety guidance; the human gates push). It never ``git merge`` —
    invariant #8: the system may create a branch, local commits, and
    a PR; a human approves the merge.
    """
    if rs.dry_run:
        # Dry-run: log the would-be commit, do not mutate the framework
        # repo's history. PRD §18 / §11: a "did the chunk land" demo
        # requires real commits, but a build-the-loop demo does not —
        # the real commits happen on the pilot repo under the executor's
        # own work; the framework-side commits are the audit trail
        # staged by this function.
        rs.commit_count += 1
        rs.output_branch = rs.output_branch or f"factory/sprint-{rs.run_id}-dry-run"
        print(
            f"  [dry-run] would commit chunk {chunk.chunk_id} on "
            f"{rs.output_branch}; audit files committed: "
            f"{os.path.relpath(evidence_output_dir, _REPO_ROOT)}"
        )
        return

    if not rs.output_branch:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        rs.output_branch = f"factory/sprint-{rs.run_id}-{ts}"
        # Refuse to launch if we're not on a clean working tree (the
        # state-machine guard already verified this, but we double-check).
        if _git_branch_exists(rs.output_branch):
            print(f"  branch {rs.output_branch} already exists; using it")
        else:
            _git("checkout", "-b", rs.output_branch, cwd=_REPO_ROOT)

    # Pass-r3 finding H-9: only stage the evidence tree when it
    # LIVES INSIDE _REPO_ROOT. When the operator passes
    # --evidence-output-dir to redirect the audit tree outside the
    # framework (per-pilot overlay pattern), the runner cannot
    # force-add it into framework git. The pilot repo is responsible
    # for its own archival in that case; we print the warning so the
    # audit trail is not silently dropped.
    stage_paths: list[str] = []
    try:
        rel = os.path.relpath(evidence_output_dir, _REPO_ROOT)
    except ValueError:
        rel = ""
    if rel and not rel.startswith("..") and not os.path.isabs(rel):
        stage_paths.append(rel)
    else:
        print(
            f"  [H-9] evidence_output_dir {evidence_output_dir!r} is "
            f"OUTSIDE framework_root {_REPO_ROOT!r}; not staging into "
            f"the framework branch. The pilot repo is responsible "
            f"for archiving this evidence.",
            file=sys.stderr,
        )

    # Pass-r3 finding H-10: also stage the run-level checkpoint.json
    # if it lives inside _REPO_ROOT. The Definition of Done says the
    # checkpoint is committed to the audit branch; without this, it
    # sits in an ignored directory and the operator's Step 6
    # ("read checkpoint.json from the audit branch") fails. The
    # checkpoint is written by main() AFTER run_chunk_with_retries;
    # we stage whatever exists at this commit time and trust the
    # follow-up write to land in the next chunk's commit.
    if run_evidence_dir:
        try:
            cp_rel = os.path.relpath(os.path.join(run_evidence_dir, "checkpoint.json"), _REPO_ROOT)
        except ValueError:
            cp_rel = ""
        if (
            cp_rel
            and not cp_rel.startswith("..")
            and not os.path.isabs(cp_rel)
            and os.path.isfile(os.path.join(run_evidence_dir, "checkpoint.json"))
        ):
            stage_paths.append(cp_rel)
    for p in stage_paths:
        # Force-add because .gitignore excludes the evidence dir by
        # design — the per-chunk evidence tree is *transient runtime
        # audit trail* on first run, but the runner *needs* the audit
        # trail to be replayable from git history per OPERATING-RULES
        # §1 ("commits are the baton"). Without `-f`, the live
        # path crashes with "fatal: pathspec ... did not match any
        # files" the moment the first chunk tries to commit (this
        # was panel-finding G-10). Pinning this with a live-path
        # test in tests/test_sprint_loop.py::test_commit_chunk_force_adds_evidence.
        _git("add", "-f", p, cwd=_REPO_ROOT)

    # KI-3: with evidence_output_dir outside framework_root (the
    # supported [H-9] per-pilot overlay pattern) nothing is staged,
    # and an unconditional `git commit` dies on "nothing to commit"
    # AFTER the whole loop has already succeeded. Skip the audit
    # commit instead; the [H-9] warning above already told the
    # operator the pilot repo owns archival in this layout.
    if not stage_paths:
        print(
            f"  chunk {chunk.chunk_id}: nothing staged in framework_root; "
            f"skipping audit commit (evidence lives outside the framework "
            f"repo — see [H-9] warning above).",
            file=sys.stderr,
        )
        return

    # Review finding F-7c8d9e: stage_paths being non-empty does not
    # guarantee the index changed — `git add -f` of paths identical to
    # HEAD stages nothing, and the unconditional commit dies on
    # "nothing to commit" exactly like the empty-stage_paths case.
    # Ask the index, not the path list.
    staged = _git("diff", "--cached", "--name-only", cwd=_REPO_ROOT)
    if not staged.strip():
        print(
            f"  chunk {chunk.chunk_id}: staged paths are identical to "
            f"HEAD; nothing to commit, skipping audit commit.",
            file=sys.stderr,
        )
        return

    body = (
        f"Phase 4.5 chunk '{chunk.chunk_id}' accepted\n\n"
        f"Model: {rs.executor.resolved_model_id or rs.executor.pinned_model_id} "
        f"(providerLock: {rs.executor.resolved_provider or rs.executor.pinned_provider}, "
        f"apiProviderLock: {rs.executor.resolved_provider or rs.executor.pinned_provider})\n"
        f"Role: executor\n"
        f"Gate: {chunk.gate_decision.value if chunk.gate_decision else 'UNKNOWN'}\n"
        f"Telemetry-row: telemetry/runs.jsonl:{rs.executor.run_id}\n"
    )
    _git("commit", "-m", body, cwd=_REPO_ROOT)
    rs.commit_count += 1
    print(f"  chunk {chunk.chunk_id} committed on {rs.output_branch}")


# ── main flow ────────────────────────────────────────────────────────────


def guard_in_uncommitted_state(evidence_dir: str = "") -> None:
    """OPERATING-RULES §7 + §15 — refuse to run a sprint if the working
    tree has uncommitted changes unless the operator opts in.

    Scoped to the case the guard can actually protect. What it protects
    against is ``commit_chunk_change`` sweeping unrelated dirty state into
    an audit commit. That commit only happens when the evidence tree lives
    *inside* ``_REPO_ROOT``; with a per-pilot overlay the evidence dir sits
    outside it, nothing is staged and the audit commit is skipped entirely
    (finding H-9 / KI-3). Refusing in that layout blocks a run over a
    hazard that cannot occur, and the only escape hatch on offer
    (``--no-fail-closed``) also disables the §17.2 family guard's
    fail-closed refusal — trading away the guard that does bind.
    """
    status = _git("status", "--porcelain", cwd=_REPO_ROOT)
    if not status.strip():
        return

    if evidence_dir:
        try:
            rel = os.path.relpath(os.path.abspath(evidence_dir), _REPO_ROOT)
        except ValueError:  # different drive; certainly outside
            rel = ".."
        if rel.startswith(".."):
            print(
                f"  [§7] framework_root has uncommitted changes, but the "
                f"evidence tree is outside it ({evidence_dir}); no audit "
                f"commit will be staged here, so the run proceeds. The "
                f"pilot repo owns its own archival.",
                file=sys.stderr,
            )
            return

    raise SystemExit(
        f"FATAL: framework_root has uncommitted changes and the evidence "
        f"tree lives inside it, so an audit commit would sweep them up. "
        f"Commit, stash, or clean before launching a sprint. §7 / §15: "
        f"git history is reality; never race it.\n{status}"
    )


def _runner_argparser() -> argparse.ArgumentParser:
    """The runner-only flag set: anything not seen by build_config's
    parser. Lives here so the ``--help`` surface and the actual
    runner share one source of truth (pass-r3 finding H-8)."""
    parser = argparse.ArgumentParser(
        prog="sprint-loop.py", description="Phase 4.5 adversarial-sprint command orchestrator"
    )
    parser.add_argument("--config")
    parser.add_argument("--chunks-file", default="")
    parser.add_argument(
        "--resume-from",
        default="",
        help="Path to a previously-written checkpoint.json. The runner "
        "restores RunState from this and continues the loop. Same "
        "form on the CLI as the runner's expect: --resume-from <path>.",
    )
    parser.add_argument(
        "--evidence-output-dir",
        default="",
        help="Override the per-run evidence tree location. By default the "
        f"runner stages at <framework-root>/{BUILD_EVIDENCE_DIR}/"
        "<run-id>/. Set this for per-pilot overlays so the framework "
        f"repo's {BUILD_EVIDENCE_DIR} dir stays clean. "
        "WARNING (pass-r3 H-9): when used as the framework-side audit "
        "path, the runner cannot force-add the audit tree into the "
        "framework repo on commit; pilot repos are responsible for "
        "their own archival here.",
    )
    parser.add_argument(
        "--no-dry-auto-decide",
        action="store_true",
        help="Disable the dry-run auto-accept shortcut. With this set, "
        "a dry-run still pauses for the reconcile gate. "
        "Pass-r3 H-13: was unreachable (only checked in sys.argv).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Bypass the human reconcile gate. Only valid "
        "with --dry-run or SPRINT_LOOP_NON_INTERACTIVE=1.",
    )
    parser.add_argument(
        "--unattended",
        action="store_true",
        help="Run unattended-live: §5.3 preconditions enforced; "
        "on refusal, write a checkpoint and raise "
        "(SystemExit 4/5). Decoupled from --dry-run per "
        "pd-pass-r2 G-7. Resumes via --resume-from.",
    )
    parser.add_argument("--verify-mode", action="store_true",
                        help="Relax the §5.3 'no RED at HEAD' requirement. When the "
                             "chunk scope says 'changes already exist, verify and "
                             "harden,' the runner accepts that as a valid starting "
                             "state. The executor becomes a verify-and-harden pass.")
    parser.add_argument("--force-accept", action="store_true",
                        help="In unattended mode, override the §5.3 reconcile gate "
                             "refusal. Records an explicit operator disposition in "
                             "the checkpoint and proceeds with ACCEPT.")
    parser.add_argument("--run-label", default="",
                        help="Experiment arm / run label stamped on every telemetry "
                             "row of this run (SCHEMA.md v3 ``run_label``). "
                             "Defaults to the run_id.")
    return parser


def _format_build_config_help_synthetic() -> str:
    """Build a synthetic ArgumentParser mirroring build_config's flags.

    The runner wants a --help surface that exposes BOTH the runner-only
    flags AND the Config-side flags. build_config's parser is internal;
    rather than refactor it, this function enumerates the known
    Config-side flags. Pin test:
    tests/test_sprint_loop.py::test_runner_help_includes_config_flags_h8.
    """
    p = argparse.ArgumentParser(
        prog="sprint-loop.py (Config-side flags)",
        description="Flags accepted and forwarded to build_config. Pass-r3 H-8.",
    )
    p.add_argument(
        "--framework-root",
        default="",
        help="Path to adversarial-sprint-dev (the loop runner's repo).",
    )
    p.add_argument("--pilot-root", default="", help="Path to the repo the runner drives.")
    p.add_argument(
        "--pilot-python",
        default="",
        help="Python interpreter for the pilot repo (e.g., .venv/bin/python).",
    )
    p.add_argument(
        "--chunks-file", default="", help="Path to the chunks spec JSON; REQUIRED at run time."
    )
    p.add_argument(
        "--pilot-spec-file", default="", help="Optional free-form spec file; planner reads it."
    )
    p.add_argument(
        "--review-prompt-template", default="", help="Path to the review prompt template override."
    )
    p.add_argument(
        "--evidence-output-dir",
        default="",
        help="Override the per-run evidence-tree location. See H-9.",
    )
    p.add_argument("--planner-model", default="")
    p.add_argument("--plan-reviewer-model", default="")
    p.add_argument("--plan-reviewer-2-model", default="")
    p.add_argument("--test-designer-model", default="")
    p.add_argument("--executor-model", default="")
    p.add_argument(
        "--validators",
        default="",
        help="Comma-separated model_ids (each may carry :provider:family:label).",
    )
    p.add_argument("--max-review-rounds", type=int, default=-1)
    p.add_argument("--retry-threshold", type=int, default=-1)
    p.add_argument("--max-auto-retries", type=int, default=-1)
    p.add_argument("--retry-delay-seconds", type=int, default=-1)
    p.add_argument(
        "--dry-run", action="store_true", help="Simulate; do not invoke droid exec or git commit."
    )
    p.add_argument(
        "--gate-auto-decide",
        action="store_true",
        help="Reconcile gate auto-decides ACCEPT after §5.3 preconditions. Per-r3 H-2.",
    )
    p.add_argument(
        "--unattended", action="store_true", help="Unattended live; checkpoint on §5.3 refusal."
    )
    p.add_argument("--verify-mode", action="store_true",
                   help="Relax §5.3 'no RED at HEAD'; verify-and-harden pass.")
    p.add_argument("--force-accept", action="store_true",
                   help="Override §5.3 reconcile refusal in unattended mode.")
    p.add_argument("--per-call-timeout-seconds", type=int, default=-1,
                   help="Override the per-droid-exec call timeout (default: 1800s).")
    p.add_argument(
        "--no-dry-auto-decide",
        action="store_true",
        help="Disable dry-run auto-accept. Per-r3 H-13.",
    )
    p.add_argument(
        "--skip-reconcile",
        action="store_true",
        help="Skip the human reconciliation gate (operator accepts ad-hoc).",
    )
    p.add_argument(
        "--create-pr", action="store_true", help="Attempt PR creation if the remote is configured."
    )
    p.add_argument(
        "--validation-backend",
        default="",
        choices=["", "local", "ci"],
        help="'local' shells out to orchestrate-review.py; 'ci' is a STUB.",
    )
    p.add_argument("--signing-key-env", default="")
    p.add_argument("--security-allowlist", nargs="*", default=[])
    p.add_argument("--security-baseline", default="")
    p.add_argument(
        "--allow-test-author-collide",
        action="store_true",
        help="§17.6 outage override only. Must be recorded in phase-N/KNOWN-ISSUES.md.",
    )
    p.add_argument(
        "--allow-single-family", action="store_true", help="Allow single-family validator panel."
    )
    p.add_argument("--fail-closed", dest="fail_closed", action="store_true", default=True)
    p.add_argument(
        "--no-fail-closed",
        dest="fail_closed",
        action="store_false",
        help="Disable §7 fail-closed. NOT recommended.",
    )
    return p.format_help()


# The RunState of the in-flight run, so the exit wrapper can emit the
# run-summary row after ``_main_inner`` has unwound (including on
# SystemExit / uncaught exceptions). None until argv parsing succeeds.
_CURRENT_RUN_STATE: RunState | None = None


def main(argv: list[str] | None = None) -> int:
    """Top-level runner entrypoint.

    Thin wrapper around ``_main_inner`` whose only job is to guarantee
    one ``role="run"`` telemetry row per run, on every exit path. A
    refusal that leaves no row is invisible to the funnel, which is
    exactly the "where do runs die" question the row exists to answer.
    """
    global _CURRENT_RUN_STATE
    _CURRENT_RUN_STATE = None
    exit_code = 1
    try:
        exit_code = _main_inner(argv)
        return exit_code
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 1
        raise
    except Exception:
        exit_code = 1
        raise
    finally:
        rs = _CURRENT_RUN_STATE
        if rs is not None:
            try:
                append_run_summary_row(
                    rs, exit_code,
                    os.path.join(rs.framework_root, "telemetry", "runs.jsonl"),
                )
            except Exception as tel_err:  # noqa: BLE001
                # Telemetry must never mask the run's real outcome.
                print(f"  [telemetry] run-summary row not written: {tel_err}",
                      file=sys.stderr)


def _main_inner(argv: list[str] | None = None) -> int:
    """Runner body; see ``main`` for the exit-path wrapper.

    Pass-r3 H-8: render both the runner-only flag table and the
    Config-side flag table when --help is requested. Otherwise, route
    runner-only flags through _runner_argparser and Config-side flags
    through build_config (after stripping the runner-only ones).
    """
    global _CURRENT_RUN_STATE
    raw_argv = sys.argv[1:] if argv is None else argv
    if "--help" in raw_argv or "-h" in raw_argv:
        runner_help = _runner_argparser().format_help()
        cfg_help = _format_build_config_help_synthetic()
        print(runner_help)
        print()
        print("-- Below: Config-side flags (also accepted; see config.py for defaults) --")
        print(cfg_help)
        return 0

    parser = _runner_argparser()
    ns, _unknown = parser.parse_known_args(argv)

    # ``build_config`` has its own complete parser; strip the runner-only
    # flags so it doesn't reject them. (--dry-run, --non-interactive, etc.
    # are conceptually owned by the orchestrator's flow control, not the
    # Config dataclass — except they ARE Config fields now per pass-r3 H-2,
    # so we leave them on the argv chain in the same form.)
    # Strip ``=`` form first; then drop the consumed peer token for the
    # space-separated form (pass-r3 finding H-4).
    peer_argv: list[str] = []
    skip_next = False
    for a in raw_argv:
        if skip_next:
            skip_next = False
            continue
        if a in ("--resume-from", "--run-label"):
            skip_next = True
            continue
        if a.startswith("--resume-from=") or a.startswith("--run-label="):
            continue
        peer_argv.append(a)
    cfg = build_config(peer_argv)
    # CLI-flag overrides
    if ns.chunks_file:
        cfg.chunks_file = ns.chunks_file
    if ns.dry_run:
        cfg.dry_run = True
    if ns.non_interactive:
        # pass-r3 finding H-2 fix: --non-interactive MUST NOT coerce
        # cfg.dry_run to True (which short-circuits every model
        # invocation + git commit). It only sets gate_auto_decide so
        # the reconcile gate auto-accepts without an operator prompt.
        cfg.gate_auto_decide = True
    if ns.unattended and cfg.unattended is False:
        # main's --unattended flag (if set) overrides; build_config's
        # --unattended is also honored.
        cfg.unattended = True
        cfg.gate_auto_decide = True
    if ns.evidence_output_dir:
        cfg.evidence_output_dir = ns.evidence_output_dir

    run_id = f"r-phase45-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    validate_run_id(run_id)

    def _make_role(
        role: Role, model_id: str, auto_level: str, enabled_tools: str
    ) -> RoleAssignment:
        return RoleAssignment(
            role=role,
            pinned_model_id=model_id,
            pinned_family=cfg.provider_family(model_id)[1],
            pinned_provider=cfg.provider_family(model_id)[0],
            auto_level=auto_level,
            enabled_tools=enabled_tools,
        )

    rs = RunState(
        run_id=run_id,
        started_at=now_iso(),
        framework_root=cfg.framework_root,
        pilot_root=cfg.pilot_root,
        pilot_python=cfg.pilot_python or sys.executable,
        pilot_spec_file=cfg.pilot_spec_file,
        chunks_file=cfg.chunks_file,
        dry_run=cfg.dry_run,
        skip_reconcile=cfg.skip_reconcile,
        unattended=cfg.unattended,
        run_label=ns.run_label or run_id,
        create_pr=cfg.create_pr,
        validation_backend=cfg.validation_backend,
        signing_key_env=cfg.signing_key_env,
        max_review_rounds=cfg.max_review_rounds,
        retry_threshold=cfg.retry_threshold,
        max_auto_retries=cfg.max_auto_retries,
        retry_delay_seconds=cfg.retry_delay_seconds,
        per_call_timeout_seconds=cfg.per_call_timeout_seconds,
        verify_mode=cfg.verify_mode,
        force_accept=cfg.force_accept,
        force_accept_reason=cfg.force_accept_reason,
        planner=_make_role(
            Role.PLANNER, cfg.planner_model, cfg.planner_auto_level, "Read,Glob,Grep,LS,Execute"
        ),
        plan_reviewer=_make_role(
            Role.PLAN_REVIEWER,
            cfg.plan_reviewer_model,
            cfg.plan_reviewer_auto_level,
            "Read,Glob,Grep,LS,Execute",
        ),
        plan_reviewer_2=(
            _make_role(
                Role.PLAN_REVIEWER,
                cfg.plan_reviewer_2_model,
                cfg.plan_reviewer_2_auto_level,
                "Read,Glob,Grep,LS,Execute",
            )
            if cfg.plan_reviewer_2_model
            else None
        ),
        test_designer=_make_role(
            Role.TEST_DESIGNER,
            cfg.test_designer_model,
            cfg.test_designer_auto_level,
            "Read,Glob,Grep,LS,Edit,Create,Execute",
        ),
        executor=_make_role(
            Role.EXECUTOR,
            cfg.executor_model,
            cfg.executor_auto_level,
            "Read,Glob,Grep,LS,Edit,Create,Execute",
        ),
        validators=[
            RoleAssignment(
                role=Role.VALIDATOR,
                pinned_model_id=v.split(":")[0],
                pinned_family=_parse_validator_inline(v, cfg)["pinned_family"],
                pinned_provider=_parse_validator_inline(v, cfg)["pinned_provider"],
                enabled_tools="Read,Glob,Grep,LS",
            )
            for v in (
                cfg.validators
                or [
                    "grok-4.5:xai:grok-family:grok-4.5",
                    "gemini-3.1-pro-preview:google:gemini-family:gemini-3.1-pro-preview",
                ]
            )
        ],
    )
    _CURRENT_RUN_STATE = rs

    # Preflight
    if not cfg.dry_run and "--no-fail-closed" not in (argv or sys.argv):
        guard_in_uncommitted_state(cfg.default_evidence_dir(rs.run_id))
    preflight_family_guard(cfg, rs)

    # If resuming from a checkpoint, restore run state.
    if ns.resume_from:
        rs = load_checkpoint(ns.resume_from)
        if ns.run_label:
            rs.run_label = ns.run_label
        _CURRENT_RUN_STATE = rs

    # Per-chunk evidence dir
    evidence_dir = cfg.default_evidence_dir(rs.run_id)
    os.makedirs(evidence_dir, exist_ok=True)

    # ── Plan → Review → Reconcile loop ──────────────────────────────
    while True:
        rs.plan_round += 1
        if rs.plan_round > rs.max_review_rounds:
            print(
                f"  max_review_rounds ({rs.max_review_rounds}) exceeded — "
                f"escalating. Per PRD §5.3: at exhaustion, hand off to "
                f"a human with a concise decision packet."
            )
            rs.status = RunStatus.AWAITING_HUMAN_DECISION
            write_checkpoint(rs, os.path.join(evidence_dir, "checkpoint.json"))
            return 2

        # 1. Planner
        rs.reached_phase_step = "planner"
        run_planner(
            rs,
            pilot_spec_text="(see --pilot-spec-file)",
            evidence_dir=evidence_dir,
            dry_run=cfg.dry_run,
        )

        # 2. Plan reviewer (always); 2nd reviewer if configured.
        rs.reached_phase_step = "plan-review"
        reviewer1 = run_plan_reviewer(
            rs, reviewer_index=1, evidence_dir=evidence_dir, dry_run=cfg.dry_run
        )
        if rs.plan_reviewer_2:
            reviewer2 = run_plan_reviewer(
                rs,
                reviewer_index=2,
                evidence_dir=evidence_dir,
                dry_run=cfg.dry_run,
                is_second_reviewer=True,
            )
        else:
            reviewer2 = None

        # Panel-finding F-2: re-run family-guard with the *resolved*
        # families of planner + reviewer(s) substituted. The recheck
        # implements what FamilyGuardOutcome's docstring claimed but
        # the preflight-only implementation did not deliver — a model
        # that the operator *configured* but the channel *resolved
        # to* a different family still gets the §4/§17.2 fail-closed
        # treatment.
        recheck_family_guard_post_resolution(cfg, rs, "after-plan-review")

        # Sanity print so the operator sees the verdict storage the
        # reconcile gate will consult (panel-finding F-7).
        bound_approves = sum(
            1
            for v in rs.plan_reviewer_verdicts
            if v["verdict"] in ("APPROVE", "APPROVE-WITH-NITS")
            and v["plan_sha256_at_time_of_review"] == rs.plan_sha256
        )
        print(
            f"  reviewer verdicts bound to current plan_sha256: "
            f"{bound_approves}/{len(rs.plan_reviewer_verdicts)} APPROVE"
        )

        # Silence unused-variable lint — reviewer1/reviewer2 are
        # diagnostics; the source of truth lives on rs.plan_reviewer_verdicts.
        _ = (reviewer1, reviewer2)

        # 3. Reconcile gate. Pass-r3 chunk-13 cleanup: --skip-reconcile,
        # --non-interactive, and --unattended all collapse to
        # gate_auto_decide=… via parameters passed through; only
        # --skip-reconcile additionally prints a louder banner.
        if cfg.skip_reconcile:
            print("  --skip-reconcile: skipping stdin pause; running §5.3 preconditions check")
        rs.reached_phase_step = "reconcile"
        decision = reconcile_human_gate(
            rs,
            evidence_dir=evidence_dir,
            dry_run=cfg.dry_run,
            gate_auto_decide=(cfg.skip_reconcile or cfg.gate_auto_decide),
            unattended=cfg.unattended,
            no_dry_auto_decide=getattr(ns, "no_dry_auto_decide", False),
            force_accept=cfg.force_accept,
            force_accept_reason=cfg.force_accept_reason,
        )

        if decision in (ReconcileDecision.ACCEPT, ReconcileDecision.AMEND):
            break
        if decision == ReconcileDecision.REJECT:
            # loop back to planner with feedback (the planner reads
            # rs.plan_findings on its next invocation).
            continue

    # ── Chunking ───────────────────────────────────────────────────
    rs.status = RunStatus.CHUNKING
    rs.reached_phase_step = "chunking"
    if not cfg.chunks_file:
        # For now require a chunks file. Auto-chunking via the planner
        # is a follow-on (KNOWN-ISSUES).
        # Pass-r3 H-7 fix: the operator-facing entrypoint
        # (``<PILOT_REPO>/.adversarial-sprint/bin/run-sprint``) sets
        # --chunks-file to ``$OVERLAY_DIR/chunks.json`` by default;
        # this FATAL message is for debug invocation only.
        raise SystemExit(
            "FATAL: --chunks-file is required. The runner does not "
            "yet auto-extract chunks from the planner's plan document. "
            "For per-pilot use, copy templates/overlay/sprint-loop-chunks-example.template.json "
            "into <PILOT_REPO>/.adversarial-sprint/chunks.json and invoke "
            "<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --chunks-file <path>."
        )
    rs.chunks = load_chunks(rs, cfg.chunks_file)
    rs.status = RunStatus.CHUNKING_DONE
    print(f"  loaded {len(rs.chunks)} chunk(s) from {cfg.chunks_file}")

    # ── Per-chunk loop ─────────────────────────────────────────────
    rs.status = RunStatus.RUNNING_CHUNKS
    rs.reached_phase_step = "chunk-execution"
    for i in range(len(rs.chunks)):
        rs.current_chunk_index = i
        chunk = rs.chunks[i]
        status_banner(f"STEP 4 · Chunk {i + 1}/{len(rs.chunks)}: {chunk.chunk_id}")
        chunk_evidence_dir = os.path.join(evidence_dir, chunk.chunk_id)
        os.makedirs(chunk_evidence_dir, exist_ok=True)
        chunk = run_chunk_with_retries(rs, chunk, chunk_evidence_dir, cfg.dry_run, cfg)
        if chunk.status == ChunkStatus.BLOCKED:
            # SPEC_OR_TEST_BLOCKED: the executor claims the locked test or
            # spec is unimplementable. Checkpoint and exit with a distinct
            # code (6) so the operator can route it to adjudication or the
            # test-designer rather than treating it as a retryable failure.
            print(
                f"  chunk {chunk.chunk_id} BLOCKED (SPEC_OR_TEST_BLOCKED); "
                f"exiting with code 6"
            )
            rs.status = RunStatus.AWAITING_HUMAN_DECISION
            write_checkpoint(rs, os.path.join(evidence_dir, "checkpoint.json"))
            commit_chunk_change(rs, chunk, chunk_evidence_dir, run_evidence_dir=evidence_dir)
            return 6
        if chunk.status != ChunkStatus.ACCEPTED:
            print(f"  chunk {chunk.chunk_id} did NOT accept; pausing")
            rs.status = RunStatus.AWAITING_HUMAN_DECISION
            # Pass-r3 H-10 fix: write_checkpoint must fire BEFORE
            # commit so the chunk's git commit captures it. Use a
            # provisional rs here for the checkpoint (the chunk was
            # NOT accepted; plan/round not bumped).
            write_checkpoint(rs, os.path.join(evidence_dir, "checkpoint.json"))
            commit_chunk_change(rs, chunk, chunk_evidence_dir, run_evidence_dir=evidence_dir)
            return 3
        # Pass-r3 H-10 fix: write run-level checkpoint BEFORE
        # commit_chunk_change so the chunk commit captures it.
        write_checkpoint(rs, os.path.join(evidence_dir, "checkpoint.json"))
        commit_chunk_change(rs, chunk, chunk_evidence_dir, run_evidence_dir=evidence_dir)

    # ── Final state ────────────────────────────────────────────────
    rs.status = RunStatus.COMPLETED
    rs.reached_phase_step = "completed"
    write_checkpoint(rs, os.path.join(evidence_dir, "checkpoint.json"))
    print()
    print("═" * 64)
    print(f"  COMPLETED · run_id={rs.run_id}")
    print(f"  branch: {rs.output_branch or '(none — dry-run?)'}")
    print(f"  commits: {rs.commit_count}")
    print(f"  evidence: {evidence_dir}")
    print("═" * 64)
    return 0


def _parse_validator_inline(entry: str, cfg: Config) -> dict:
    """Parser for ``--validators "model_id:provider:family:label"`` entries.

    Panel-finding F-3: previously took ``family`` verbatim from the
    inline declaration, defeating the curated-map rule. Now requires
    the inline ``family`` to match the curated map's projection
    when the model is in MODEL_FAMILY_MAP, and refuses when the
    model is not in the curated map at all (regardless of inline).
    """
    parts = entry.strip().split(":")
    model_id = parts[0]
    curated_provider, curated_family = cfg.provider_family(model_id)
    # If model_id is curated, the inline family (if given) must equal
    # the curated family. Per §4 provenance is curated—not declared.
    if model_id in MODEL_FAMILY_MAP:  # curate presence test (cfg.provider_family
        # already returns ("unknown","unknown") for unmapped)
        if len(parts) > 2 and parts[2] and parts[2] != curated_family:
            raise SystemExit(
                f"validator {entry!r} declares family '{parts[2]}' but "
                f"the curated MODEL_FAMILY_MAP assigns '{curated_family}' "
                f"to model {model_id!r}. PRD §4 forbids provenance bypass; "
                f"OMIT the inline family to use the curated value, or ADD "
                f"{model_id} → ({curated_provider!r}, {curated_family!r}) "
                f"to tools/sprint_loop/config.py MODEL_FAMILY_MAP."
            )
        provider = parts[1] if len(parts) > 1 else curated_provider
        family = curated_family
    else:
        # Unmapped model: refuse closed per §4, regardless of inline fields.
        # (Inline fields here are an attempt to claim provenance we don't have.)
        if len(parts) > 2 and parts[2]:
            raise SystemExit(
                f"validator {entry!r} declares family '{parts[2]}' but "
                f"{model_id!r} is not in MODEL_FAMILY_MAP. PRD §4 forbids "
                f"provenance by declaration; add the model to "
                f"tools/sprint_loop/config.py MODEL_FAMILY_MAP first."
            )
        raise SystemExit(
            f"validator {entry!r}: model {model_id!r} is not in MODEL_FAMILY_MAP. "
            f"PRD §4 forbids provenance by declaration; add the model to "
            f"tools/sprint_loop/config.py MODEL_FAMILY_MAP first."
        )
    return {"pinned_family": family, "pinned_provider": provider}


if __name__ == "__main__":
    sys.exit(main())
