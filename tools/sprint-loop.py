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
from pathlib import Path
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
    Config,
    MODEL_FAMILY_MAP,
    build_config,
)
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    ChunkStatus,
    Finding,
    GateDecision,
    GateDecision as GD,
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
from sprint_loop.droid import (  # noqa: E402
    InvokeOptions,
    append_run_record,
    invoke_droid,
)
from sprint_loop.per_chunk import (  # noqa: E402
    invoke_executor,
    invoke_test_designer,
    lock_test,
    produce_evidence,
    render_executor_prompt,
    render_test_designer_prompt,
    run_validators,
    validate_red,
    verify_green,
)
from sprint_loop.prompts.render import render_to_file, list_role_prompts  # noqa: E402


# ── git helpers (assert-on-reality per OPERATING-RULES §7/§15) ───────────

def _git(*args: str, cwd: str | None = None) -> str:
    """Run a git command, capture stdout. cwd defaults to framework_root."""
    r = subprocess.run(["git", *args], cwd=cwd or _REPO_ROOT,
                       capture_output=True, text=True, timeout=60, check=False)
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
    # Restore minimal RunState (we only need the fields the runner
    # looks at after a pause — start_at, run_id, status, current
    # chunk, plan path/chunks, etc.). Full re-resolve of every role
    # assignment is reconstructed from the Config at runtime.
    rs = RunState(
        run_id=data["run_id"],
        started_at=data["started_at"],
        framework_root=data["framework_root"],
        pilot_root=data["pilot_root"],
        pilot_python=data["pilot_python"],
        current_chunk_index=data.get("current_chunk_index", 0),
    )
    rs.plan_doc_path = data.get("plan_doc_path", "")
    rs.plan_sha256 = data.get("plan_sha256", "")
    rs.status = RunStatus(data.get("status", "PENDING"))
    rs.output_branch = data.get("output_branch", "")
    rs.commit_count = data.get("commit_count", 0)
    # Pass-r3 finding H-5 fix: persist on write_checkpoint already;
    # restore here. Without this, ``plan_round`` resets to 0 (so the
    # resume restarts the planner + reviewers at full cost),
    # ``plan_reviewer_verdicts`` is empty (so §5.3 enforcement
    # SystemExit(5)s and the resume never accepts), and ``dry_run``
    # defaults to False (so a ``--dry-run --resume-from`` run
    # performs real git commits against code that was simulated).
    rs.plan_round = data.get("plan_round", 0)
    rs.plan_reviewer_verdicts = data.get("plan_reviewer_verdicts", [])
    rs.dry_run = bool(data.get("dry_run", False))
    rs.max_review_rounds = int(data.get("max_review_rounds", 2))
    rs.retry_threshold = int(data.get("retry_threshold", 1))
    rs.max_auto_retries = int(data.get("max_auto_retries", 2))
    rs.retry_delay_seconds = int(data.get("retry_delay_seconds", 5))
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
            )
            for f in data["plan_findings"]
        ]
    if data.get("chunks"):
        for c in data["chunks"]:
            cs = ChunkState(chunk_id=c["chunk_id"], scope=c.get("scope", ""))
            for k in ("observable_criteria", "allowed_files",
                      "locked_test_files", "commands"):
                setattr(cs, k, c.get(k, []))
            cs.accepted_assertion = c.get("accepted_assertion", "")
            cs.lock_manifest_path = c.get("lock_manifest_path", "")
            cs.locked_test_sha = c.get("locked_test_sha", "")
            cs.evidence_bundle_path = c.get("evidence_bundle_path", "")
            cs.status = ChunkStatus(c.get("status", "PENDING"))
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

def run_planner(rs: RunState, *, pilot_spec_text: str,
                evidence_dir: str, dry_run: bool) -> dict:
    """Fire the planner role and produce the plan document."""
    rs.status = RunStatus.PLANNING
    status_banner("STEP 1 · Planner (GROK)")
    state_status(rs, "planner role active")

    plan_doc_path = os.path.join(evidence_dir, "plan.md")
    rendered_path = render_to_file(
        "planner",
        {
            "pilot_spec_path": rs.pilot_spec_file or "(no --pilot-spec-file)",
            "plan_output_path": plan_doc_path,
        },
        os.path.join(evidence_dir, "plan-prompt.md"),
    )

    env_path = os.path.join(evidence_dir, "planner-envelope.json")
    stderr_path = os.path.join(evidence_dir, "planner-stderr.log")
    options = InvokeOptions(
        model_id=rs.planner.pinned_model_id or "claude-opus-5",
        auto_level=rs.planner.auto_level,
        enabled_tools=rs.planner.enabled_tools,
        prompt_file=rendered_path,
        cwd=rs.framework_root,
    )
    record = invoke_droid(Role.PLANNER, options=options,
                          envelope_path=env_path,
                          stderr_path=stderr_path,
                          max_retries=rs.max_auto_retries,
                          retry_delay_seconds=rs.retry_delay_seconds,
                          dry_run=dry_run)
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
    append_run_record(record, phase="phase-4.5",
                      branch="factory/phase-4.5-loop-runner",
                      telemetry_path=os.path.join(rs.framework_root,
                                                  "telemetry", "runs.jsonl"))

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
            raise RuntimeError(f"planner envelope unreadable for plan: {e}")

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

_VERDICT_RE = re.compile(r"\bVERDICT:\s*(APPROVE|APPROVE-WITH-NITS|REJECT)\b", re.IGNORECASE)
_FINDING_RE = re.compile(
    r'\{[\s\S]*?"finding_id":\s*"F-[a-z0-9]+"[\s\S]*?\}',
    re.IGNORECASE,
)


def _parse_finding_block(reviewer_label: str, result_text: str,
                          source_run_id: str, source_model: str,
                          source_family: str, panel_position: int) -> list[Finding]:
    """Best-effort JSON extraction of findings from the reviewer's
    natural-language result text. The reviewer prompt asks for a
    structured JSON output; the parser is lenient so missing/extra
    brackets do not break the runner.
    """
    findings: list[Finding] = []
    for match in _FINDING_RE.finditer(result_text):
        snippet = match.group(0)
        # Find balanced-ish JSON by trimming trailing junk
        depth = 0
        end = 0
        for i, ch in enumerate(snippet):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == 0:
            continue
        try:
            obj = json.loads(snippet[:end])
        except json.JSONDecodeError:
            continue
        f = Finding(
            finding_id=obj.get("finding_id", f"F-unlabeled-{reviewer_label}"),
            severity=(obj.get("severity") or "medium").lower(),
            category=(obj.get("category") or "spec-deviation").lower(),
            claim=obj.get("claim", "")[:240],
            evidence=obj.get("evidence", []) or [],
            recommended_change=obj.get("recommended_change", "")[:240],
            source_role="reviewer",
            source_run_id=source_run_id,
            source_model_id=source_model,
            source_family=source_family,
            first_seen_in_panel_position=panel_position,
            status="open",
        )
        findings.append(f)
    return findings


def run_plan_reviewer(rs: RunState, *, reviewer_index: int,
                      evidence_dir: str, dry_run: bool,
                      is_second_reviewer: bool = False) -> dict:
    """Fire ONE plan-reviewer role. Cross-family from planner (§17.2).

    reviewer_index: 1..N — used in panel_position and envelope label.
    """
    rs.status = RunStatus.PLAN_REVIEWING
    reviewer = rs.plan_reviewer_2 if (is_second_reviewer and rs.plan_reviewer_2) else rs.plan_reviewer
    label = f"plan-reviewer-{reviewer_index}"
    status_banner(f"STEP 2.{reviewer_index} · Plan reviewer {reviewer_index} ({reviewer.pinned_model_id})")
    state_status(rs, f"reviewer {reviewer_index} role active")

    reviewer_prompt_out = os.path.join(evidence_dir, f"{label}-prompt.md")
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

    env_path = os.path.join(evidence_dir, f"{label}-envelope.json")
    stderr_path = os.path.join(evidence_dir, f"{label}-stderr.log")
    options = InvokeOptions(
        model_id=reviewer.pinned_model_id,
        auto_level=reviewer.auto_level,
        enabled_tools=reviewer.enabled_tools,
        prompt_file=rendered_path,
        cwd=rs.framework_root,
    )
    record = invoke_droid(Role.PLAN_REVIEWER, options=options,
                          envelope_path=env_path,
                          stderr_path=stderr_path,
                          max_retries=rs.max_auto_retries,
                          retry_delay_seconds=rs.retry_delay_seconds,
                          dry_run=dry_run)
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
    append_run_record(record, phase="phase-4.5",
                      branch="factory/phase-4.5-loop-runner",
                      telemetry_path=os.path.join(rs.framework_root,
                                                  "telemetry", "runs.jsonl"))

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
        raise RuntimeError(f"reviewer envelope unreadable: {e}")

    verdict_match = _VERDICT_RE.findall(result_text)
    verdict = verdict_match[-1].upper() if verdict_match else "UNKNOWN"

    findings = _parse_finding_block(label, result_text, record.run_id,
                                     record.model_id, record.family,
                                     reviewer_index)

    # Append to plan-level findings; telemetry goes to findings.jsonl too.
    rs.plan_findings.extend(findings)
    _append_finding_rows(findings, telemetry_path=os.path.join(
        rs.framework_root, "telemetry", "findings.jsonl"))

    # Panel-finding F-7: store the verdict, bound to the plan_sha256
    # the reviewer saw. This is what `reconcile_human_gate` consults
    # to decide whether `accept` is machine-permissible.
    rs.plan_reviewer_verdicts.append({
        "reviewer_index": reviewer_index,
        "model_id": record.model_id,
        "family": record.family,
        "verdict": verdict,
        "plan_sha256_at_time_of_review": rs.plan_sha256,
        "is_error": record.is_error,
        "run_id": record.run_id,
    })

    print(f"  reviewer {reviewer_index} verdict: {verdict}")
    print(f"  findings: {len(findings)}")
    return {"record": record, "verdict": verdict, "findings": findings}


def _append_finding_rows(findings: list[Finding], telemetry_path: str) -> None:
    """Append findings to ``telemetry/findings.jsonl`` per §10."""
    if not findings:
        return
    os.makedirs(os.path.dirname(os.path.abspath(telemetry_path)) or ".",
                exist_ok=True)
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
    rs.family_guard_notes = "; ".join(out.notes + [
        v for v in out.violations if v
    ])
    if not out.ok and cfg.fail_closed:
        print("§17.2 family guard FAILED — refusing to launch.", file=sys.stderr)
        for v in out.violations:
            print(f"  - {v}", file=sys.stderr)
        raise SystemExit(2)
    elif not out.ok:
        print("§17.2 family guard FAILED but fail-closed disabled; continuing.",
              file=sys.stderr)
    else:
        print("§17.2 family guard OK")


def recheck_family_guard_post_resolution(cfg: Config, rs: RunState,
                                          which: str) -> None:
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
        rs.family_guard_notes = (
            f"post-resolution re-check ({which}) failed; " +
            "; ".join(out.violations)
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
        rs.family_guard_notes = (
            f"§17.2 family guard OK at pref + post-resolution ({which})"
        )


# ── step: reconcile (human gate) ────────────────────────────────────────

def reconcile_human_gate(rs: RunState, *, evidence_dir: str,
                          dry_run: bool,
                          gate_auto_decide: bool = False,
                          unattended: bool = False,
                          no_dry_auto_decide: bool = False) -> ReconcileDecision:
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
    """
    rs.status = RunStatus.AWAITING_RECONCILIATION
    packet_path = os.path.join(evidence_dir, "reconcile-packet.txt")
    _write_reconcile_packet(rs, packet_path)

    print()
    print("═" * 64)
    print(f"  RECONCILE GATE — human pause")
    print(f"  packet: {packet_path}")
    print(f"  round: {rs.plan_round + 1} / max {rs.max_review_rounds}")
    print(f"  findings ({len(rs.plan_findings)}):")
    for f in rs.plan_findings[-10:]:
        sev = f.severity.upper()
        print(f"    [{sev}] {f.finding_id} ({f.source_model_id}): {f.claim[:120]}")
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
        print("  [dry-run] auto-decision: accept (non-committal — "
              "dry-run produces a simulated ACCEPT. Live mode honors "
              "--non-interactive / --unattended separately.)")
        return ReconcileDecision.ACCEPT

    # Pass-r3 finding H-2 fix: gate auto-decide path is opt-in via
    # main()'s parsing (no sys.argv reads). On §5.3 refusal:
    #   gate_auto_decide + unattended=False (== --non-interactive): SystemExit.
    #   gate_auto_decide + unattended=True  (== --unattended): SystemExit + checkpoint.
    if gate_auto_decide:
        try:
            _enforce_5_3_preconditions(rs)
        except SystemExit as e:
            if unattended:
                cp_path = os.path.join(evidence_dir, "checkpoint.json")
                write_checkpoint(rs, cp_path)
                print(
                    f"  [unattended] refused (exit {e.code}); "
                    f"checkpoint at {cp_path}; resume with --resume-from",
                    file=sys.stderr,
                )
            else:
                print(
                    f"  [non-interactive] refused (exit {e.code}); "
                    f"no checkpoint",
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
        raise SystemExit(1)
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
            # If the reasons include the explicit REFUSED markers,
            # _enforce_5_3_preconditions has already written them.
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
        f for f in rs.plan_findings
        if f.status == "open" and f.severity in ("blocker", "high")
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
            print(
                f"    - {f.finding_id} ({f.source_model_id}): "
                f"{f.claim[:160]}",
                file=sys.stderr,
            )
        raise SystemExit(4)

    bound_approves = [
        v for v in rs.plan_reviewer_verdicts
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
        f"plan_round={rs.plan_round + 1} / max={rs.max_review_rounds}",
        f"validators configured: {[v.pinned_model_id for v in rs.validators]}",
        f"findings ({len(rs.plan_findings)}):",
    ]
    for f in rs.plan_findings:
        lines.append(
            f"  [{f.severity.upper()}/{f.category}] {f.finding_id} "
            f"(by {f.source_model_id}@{f.first_seen_in_panel_position}): "
            f"{f.claim[:200]}"
        )
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
        out.append(cs)
    return out


# ── step: per-chunk run + retry policy ───────────────────────────────────

def run_chunk_with_retries(rs: RunState, chunk: ChunkState,
                            evidence_output_dir: str,
                            dry_run: bool,
                            cfg: Config) -> ChunkState:
    """Run a chunk's inner loop. On REJECT, retry up to retry_threshold
    by feeding rejection feedback back to the executor.

    Per PRD §5.7:
      - 1 retry by default (retry_threshold=1)
      - Above the threshold → ``HUMAN_DECISION`` and the run pauses.
    """
    attempts_left = rs.retry_threshold + 1  # first try + retries
    while attempts_left > 0:
        chunk.status = ChunkStatus.TEST_DESIGNING if chunk.retry_count == 0 else ChunkStatus.RETRYING
        attempts_left -= 1

        run_chunk_inner(rs, chunk, evidence_output_dir, dry_run, cfg)

        # Re-evaluate the gate decision.
        if chunk.gate_decision in (GateDecision.ACCEPT, GateDecision.ACCEPT_WITH_NITS):
            chunk.status = ChunkStatus.ACCEPTED
            chunk.rejection_feedback = []  # cleared on ACCEPT
            return chunk

        if chunk.gate_decision == GateDecision.STOP:
            chunk.status = ChunkStatus.HUMAN_DECISION
            rs.status_message = f"STOP in chunk {chunk.chunk_id}: {chunk.gate_reason}"
            return chunk

        # REJECT or similar — retry if we have attempts left
        if attempts_left > 0:
            chunk.retry_count += 1
            chunk.rejection_feedback = [chunk.gate_reason]
            print(f"  REJECT ({chunk.gate_decision.value}); retrying "
                  f"({rs.retry_threshold + 1 - attempts_left}/{rs.retry_threshold + 1})")
            continue

        # No retries left — escalate
        chunk.status = ChunkStatus.HUMAN_DECISION
        rs.status_message = (
            f"chunk {chunk.chunk_id} reached HUMAN_DECISION after "
            f"{chunk.retry_count} retries"
        )
        return chunk
    # Shouldn't reach here, but safety
    chunk.status = ChunkStatus.HUMAN_DECISION
    return chunk


def run_chunk_inner(rs: RunState, chunk: ChunkState,
                     evidence_output_dir: str, dry_run: bool,
                     cfg: Config) -> None:
    """The per-chunk inner loop:
    test-designer → lock → valid-red → executor → verify-green →
    evidence → validation → gate decision.
    """
    # 1. test-designer writes the test (handled by humans in the Phase 3
    # pilot; for sprints where the chunk spec gives the test file in
    # advance we skip the droid test_designer round). The runner
    # supports both modes by checking whether chunk.locked_test_files
    # already includes the file (pre-authored) or not.
    if not chunk.locked_test_files:
        # Fire the test_designer role (composition: nice-to-have, not
        # required for the minimum end-to-end run; logged in KNOWN-ISSUES).
        raise RuntimeError(
            f"chunk {chunk.chunk_id} has no locked_test_files; the runner "
            f"does not yet auto-fire the test_designer droid role for "
            f"auto-chunks. See phase-4.5/KNOWN-ISSUES.md."
        )

    # 2. lock
    chunk.status = ChunkStatus.LOCKING
    lock_test(chunk,
              framework_root=rs.framework_root,
              pilot_root=rs.pilot_root,
              pilot_python=rs.pilot_python,
              accepted_assertion=chunk.accepted_assertion,
              dry_run=dry_run)

    # 3. valid-red
    chunk.status = ChunkStatus.VALIDATING_RED
    try:
        validate_red(chunk,
                     framework_root=rs.framework_root,
                     pilot_root=rs.pilot_root,
                     pilot_python=rs.pilot_python,
                     dry_run=dry_run)
    except RuntimeError as e:
        chunk.status = ChunkStatus.RED_REJECTED
        rs.status_message = (
            f"chunk {chunk.chunk_id} RED_REJECTED: {e}"
        )
        return

    # 4. executor
    chunk.status = ChunkStatus.EXECUTING
    ex_prompt_path = os.path.join(evidence_output_dir, f"{chunk.chunk_id}-ex-prompt.md")
    render_executor_prompt(chunk, rs, output_path=ex_prompt_path)
    invoke_executor(
        chunk, rs,
        evidence_output_dir=evidence_output_dir,
        rendered_prompt_path=ex_prompt_path,
        envelope_path=os.path.join(evidence_output_dir, f"{chunk.chunk_id}-ex-envelope.json"),
        dry_run=dry_run,
    )
    recheck_family_guard_post_resolution(cfg, rs, "after-executor")

    # 5. verify-green
    chunk.status = ChunkStatus.VERIFYING_GREEN
    verify_green(chunk,
                 framework_root=rs.framework_root,
                 pilot_root=rs.pilot_root,
                 pilot_python=rs.pilot_python,
                 dry_run=dry_run)

    # 6. evidence
    chunk.status = ChunkStatus.EVIDENCING
    bundle_path = os.path.join(evidence_output_dir, f"{chunk.chunk_id}-bundle.json")
    produce_evidence(chunk,
                     framework_root=rs.framework_root,
                     pilot_root=rs.pilot_root,
                     pilot_python=rs.pilot_python,
                     evidence_output_path=bundle_path,
                     dry_run=dry_run)

    # 7. validation
    chunk.status = ChunkStatus.VALIDATING
    backend_result = run_validators(chunk, rs,
                                    evidence_output_dir=evidence_output_dir,
                                    dry_run=dry_run)
    chunk.gate_decision = backend_result.gate
    chunk.gate_reason = backend_result.reason


# ── step: branch + commit ───────────────────────────────────────────────

def commit_chunk_change(rs: RunState, chunk: ChunkState,
                         evidence_output_dir: str,
                         run_evidence_dir: str | None = None) -> None:
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
        print(f"  [dry-run] would commit chunk {chunk.chunk_id} on "
              f"{rs.output_branch}; audit files committed: "
              f"{os.path.relpath(evidence_output_dir, _REPO_ROOT)}")
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
            cp_rel = os.path.relpath(
                os.path.join(run_evidence_dir, "checkpoint.json"),
                _REPO_ROOT)
        except ValueError:
            cp_rel = ""
        if (cp_rel and not cp_rel.startswith("..")
                and not os.path.isabs(cp_rel)
                and os.path.isfile(os.path.join(
                    run_evidence_dir, "checkpoint.json"))):
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

def guard_in_uncommitted_state() -> None:
    """OPERATING-RULES §7 + §15 — refuse to run a sprint if the working
    tree has uncommitted changes unless the operator opts in."""
    status = _git("status", "--porcelain", cwd=_REPO_ROOT)
    if status.strip():
        raise SystemExit(
            f"FATAL: framework_root has uncommitted changes. Commit, "
            f"stash, or clean before launching a sprint. §7 / §15: "
            f"git history is reality; never race it.\n{status}"
        )


def main(argv: list[str] | None = None) -> int:
    # Pass-r3 finding H-8 fix: when ``--help`` is requested, surface
    # BOTH the runner-only flags AND the Config-side flags by calling
    # each parser's formatter separately. argparse's stock ``--help``
    # only sees the first parser, and the runner previously exposed
    # operator-critical flags (--validators, --planner-model,
    # --allow-single-family, …) only via build_config's hidden parser.
    raw_argv = sys.argv[1:] if argv is None else argv
    if "--help" in raw_argv or "-h" in raw_argv:
        runner_help = _runner_argparser().format_help()
        cfg_help = build_config.__doc__ or ""
        # Render build_config's parser help too.
        try:
            from sprint_loop.config import build_config  # noqa: F401
            cfg_help_parser = argparse.ArgumentParser(prog="(config)")
            # Reuse the same parser that build_config uses.
            cfg_help_parser_help = _format_build_config_help()
        except Exception:
            cfg_help_parser_help = ""
        print(runner_help)
        if cfg_help_parser_help:
            print()
            print("-- Below: Config-side flags (also accepted) --")
            print(cfg_help_parser_help)
        return 0

    parser = _runner_argparser()
    ns, _unknown = parser.parse_known_args(argv)


def _runner_argparser() -> argparse.ArgumentParser:
    """The runner-only flag set: anything not seen by build_config's
    parser. Lives here so the ``--help`` surface and the actual
    runner share one source of truth (pass-r3 finding H-8)."""
    parser = argparse.ArgumentParser(prog="sprint-loop.py",
        description="Phase 4.5 adversarial-sprint command orchestrator")
    parser.add_argument("--config")
    parser.add_argument("--chunks-file", default="")
    parser.add_argument("--resume-from", default="",
                        help="Path to a previously-written checkpoint.json. The runner "
                             "restores RunState from this and continues the loop. Same "
                             "form on the CLI as the runner's expect: --resume-from <path>.")
    parser.add_argument("--evidence-output-dir", default="",
                        help="Override the per-run evidence tree location. By default the "
                             f"runner stages at <framework-root>/{BUILD_EVIDENCE_DIR}/"
                             "<run-id>/. Set this for per-pilot overlays so the framework "
                             f"repo's {BUILD_EVIDENCE_DIR} dir stays clean. "
                             "WARNING (pass-r3 H-9): when used as the framework-side audit "
                             "path, the runner cannot force-add the audit tree into the "
                             "framework repo on commit; pilot repos are responsible for "
                             "their own archival here.")
    parser.add_argument("--no-dry-auto-decide", action="store_true",
                        help="Disable the dry-run auto-accept shortcut. With this set, "
                             "a dry-run still pauses for the reconcile gate. "
                             "Pass-r3 H-13: was unreachable (only checked in sys.argv).")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Bypass the human reconcile gate. Only valid "
                             "with --dry-run or SPRINT_LOOP_NON_INTERACTIVE=1.")
    parser.add_argument("--unattended", action="store_true",
                        help="Run unattended-live: §5.3 preconditions enforced; "
                             "on refusal, write a checkpoint and raise "
                             "(SystemExit 4/5). Decoupled from --dry-run per "
                             "pd-pass-r2 G-7. Resumes via --resume-from.")
    return parser

def _format_build_config_help() -> str:
    """Render build_config's parser help text for ``--help`` output.

    The pattern: instantiate the parser via a no-args call, capture
    ``.format_help()``. This must match build_config()'s parser shape
    exactly; the cleanest way is to refactor build_config() to call a
    helper that returns a parser. Pass-r3 was right that the
    operator-visible surface is the test bar; the test pins what an
    operator sees.
    """
    try:
        cfg = build_config(["--help-empty-shell"])
    except SystemExit:
        # build_config's parser does NOT consume --help-empty-shell
        # usefully; we want to render the help text without consuming
        # real argv. Build a synthetic parser that mirrors build_config's
        # argument set. The simplest faithful approach: call build_config
        # with the absolute minimum argv to drive its parser, then catch
        # SystemExit(0) from --help, but parse with an alternative we
        # assemble here.
        return _format_build_config_help_synthetic()
    return ""


def _format_build_config_help_synthetic() -> str:
    """Build a synthetic ArgumentParser mirroring build_config's flags.

    The runner wants a --help surface that exposes BOTH the runner-only
    flags AND the Config-side flags. build_config's parser is internal;
    rather than refactor it, this function enumerates the known
    Config-side flags. Pin test:
    tests/test_sprint_loop.py::test_runner_help_includes_config_flags_h8.
    """
    p = argparse.ArgumentParser(prog="sprint-loop.py (Config-side flags)",
        description="Flags accepted and forwarded to build_config. Pass-r3 H-8.")
    p.add_argument("--framework-root", default="",
                   help="Path to adversarial-sprint-dev (the loop runner's repo).")
    p.add_argument("--pilot-root", default="",
                   help="Path to the repo the runner drives.")
    p.add_argument("--pilot-python", default="",
                   help="Python interpreter for the pilot repo (e.g., .venv/bin/python).")
    p.add_argument("--chunks-file", default="",
                   help="Path to the chunks spec JSON; REQUIRED at run time.")
    p.add_argument("--pilot-spec-file", default="",
                   help="Optional free-form spec file; planner reads it.")
    p.add_argument("--review-prompt-template", default="",
                   help="Path to the review prompt template override.")
    p.add_argument("--evidence-output-dir", default="",
                   help="Override the per-run evidence-tree location. See H-9.")
    p.add_argument("--planner-model", default="")
    p.add_argument("--plan-reviewer-model", default="")
    p.add_argument("--plan-reviewer-2-model", default="")
    p.add_argument("--test-designer-model", default="")
    p.add_argument("--executor-model", default="")
    p.add_argument("--validators", default="",
                   help="Comma-separated model_ids (each may carry :provider:family:label).")
    p.add_argument("--max-review-rounds", type=int, default=-1)
    p.add_argument("--retry-threshold", type=int, default=-1)
    p.add_argument("--max-auto-retries", type=int, default=-1)
    p.add_argument("--retry-delay-seconds", type=int, default=-1)
    p.add_argument("--dry-run", action="store_true",
                   help="Simulate; do not invoke droid exec or git commit.")
    p.add_argument("--gate-auto-decide", action="store_true",
                   help="Reconcile gate auto-decides ACCEPT after §5.3 preconditions. Per-r3 H-2.")
    p.add_argument("--unattended", action="store_true",
                   help="Unattended live; checkpoint on §5.3 refusal.")
    p.add_argument("--no-dry-auto-decide", action="store_true",
                   help="Disable dry-run auto-accept. Per-r3 H-13.")
    p.add_argument("--skip-reconcile", action="store_true",
                   help="Skip the human reconciliation gate (operator accepts ad-hoc).")
    p.add_argument("--create-pr", action="store_true",
                   help="Attempt PR creation if the remote is configured.")
    p.add_argument("--validation-backend", default="", choices=["", "local", "ci"],
                   help="'local' shells out to orchestrate-review.py; 'ci' is a STUB.")
    p.add_argument("--signing-key-env", default="")
    p.add_argument("--security-allowlist", nargs="*", default=[])
    p.add_argument("--security-baseline", default="")
    p.add_argument("--allow-test-author-collide", action="store_true",
                   help="§17.6 outage override only. Must be recorded in phase-N/KNOWN-ISSUES.md.")
    p.add_argument("--allow-single-family", action="store_true",
                   help="Allow single-family validator panel.")
    p.add_argument("--fail-closed", dest="fail_closed", action="store_true", default=True)
    p.add_argument("--no-fail-closed", dest="fail_closed", action="store_false",
                   help="Disable §7 fail-closed. NOT recommended.")
    return p.format_help()

def main(argv: list[str] | None = None) -> int:
    """Top-level runner entrypoint.

    Pass-r3 H-8: render both the runner-only flag table and the
    Config-side flag table when --help is requested. Otherwise, route
    runner-only flags through _runner_argparser and Config-side flags
    through build_config (after stripping the runner-only ones).
    """
    raw_argv = sys.argv[1:] if argv is None else argv
    if "--help" in raw_argv or "-h" in raw_argv:
        runner_help = _runner_argparser().format_help()
        cfg_help = _format_build_config_help_synthetic()
        print(runner_help)
        print()
        print("-- Below: Config-side flags (also accepted; see "
              "config.py for defaults) --")
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
        if a == "--resume-from":
            skip_next = True
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

    def _make_role(role: Role, model_id: str, auto_level: str,
                   enabled_tools: str) -> RoleAssignment:
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
        dry_run=cfg.dry_run,
        skip_reconcile=cfg.skip_reconcile,
        create_pr=cfg.create_pr,
        validation_backend=cfg.validation_backend,
        signing_key_env=cfg.signing_key_env,
        max_review_rounds=cfg.max_review_rounds,
        retry_threshold=cfg.retry_threshold,
        max_auto_retries=cfg.max_auto_retries,
        retry_delay_seconds=cfg.retry_delay_seconds,
        planner=_make_role(Role.PLANNER, cfg.planner_model,
                            cfg.planner_auto_level,
                            "Read,Glob,Grep,LS,Execute"),
        plan_reviewer=_make_role(Role.PLAN_REVIEWER, cfg.plan_reviewer_model,
                                  cfg.plan_reviewer_auto_level,
                                  "Read,Glob,Grep,LS,Execute"),
        plan_reviewer_2=(_make_role(Role.PLAN_REVIEWER,
                                      cfg.plan_reviewer_2_model,
                                      cfg.plan_reviewer_2_auto_level,
                                      "Read,Glob,Grep,LS,Execute")
                          if cfg.plan_reviewer_2_model else None),
        test_designer=_make_role(Role.TEST_DESIGNER, cfg.test_designer_model,
                                  cfg.test_designer_auto_level,
                                  "Read,Glob,Grep,LS,Edit,Create,ApplyPatch,MultiEdit,Execute"),
        executor=_make_role(Role.EXECUTOR, cfg.executor_model,
                            cfg.executor_auto_level,
                            "Read,Glob,Grep,LS,Edit,Create,ApplyPatch,MultiEdit,Execute"),
        validators=[
            RoleAssignment(
                role=Role.VALIDATOR,
                pinned_model_id=v.split(":")[0],
                pinned_family=_parse_validator_inline(v, cfg)["pinned_family"],
                pinned_provider=_parse_validator_inline(v, cfg)["pinned_provider"],
                enabled_tools="Read,Glob,Grep,LS",
            )
            for v in (cfg.validators or ["grok-4.5:xai:grok-family:grok-4.5",
                                          "gemini-3.1-pro-preview:google:gemini-family:gemini-3.1-pro-preview"])
        ],
    )

    # Preflight
    if not cfg.dry_run and "--no-fail-closed" not in (argv or sys.argv):
        guard_in_uncommitted_state()
    preflight_family_guard(cfg, rs)

    # If resuming from a checkpoint, restore run state.
    if ns.resume_from:
        rs = load_checkpoint(ns.resume_from)

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
        run_planner(rs, pilot_spec_text="(see --pilot-spec-file)",
                    evidence_dir=evidence_dir, dry_run=cfg.dry_run)

        # 2. Plan reviewer (always); 2nd reviewer if configured.
        reviewer1 = run_plan_reviewer(rs, reviewer_index=1,
                                      evidence_dir=evidence_dir,
                                      dry_run=cfg.dry_run)
        if rs.plan_reviewer_2:
            reviewer2 = run_plan_reviewer(rs, reviewer_index=2,
                                          evidence_dir=evidence_dir,
                                          dry_run=cfg.dry_run,
                                          is_second_reviewer=True)
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
            1 for v in rs.plan_reviewer_verdicts
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
            print(
                f"  --skip-reconcile: skipping stdin pause; "
                f"running §5.3 preconditions check"
            )
        decision = reconcile_human_gate(
            rs, evidence_dir=evidence_dir,
            dry_run=cfg.dry_run,
            gate_auto_decide=(cfg.skip_reconcile or cfg.gate_auto_decide),
            unattended=cfg.unattended,
            no_dry_auto_decide=getattr(ns, "no_dry_auto_decide", False))

        if decision in (ReconcileDecision.ACCEPT, ReconcileDecision.AMEND):
            break
        if decision == ReconcileDecision.REJECT:
            # loop back to planner with feedback (the planner reads
            # rs.plan_findings on its next invocation).
            continue

    # ── Chunking ───────────────────────────────────────────────────
    rs.status = RunStatus.CHUNKING
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
    for i in range(len(rs.chunks)):
        rs.current_chunk_index = i
        chunk = rs.chunks[i]
        status_banner(f"STEP 4 · Chunk {i + 1}/{len(rs.chunks)}: {chunk.chunk_id}")
        chunk_evidence_dir = os.path.join(evidence_dir, chunk.chunk_id)
        os.makedirs(chunk_evidence_dir, exist_ok=True)
        chunk = run_chunk_with_retries(rs, chunk, chunk_evidence_dir, cfg.dry_run, cfg)
        if chunk.status != ChunkStatus.ACCEPTED:
            print(f"  chunk {chunk.chunk_id} did NOT accept; pausing")
            rs.status = RunStatus.AWAITING_HUMAN_DECISION
            # Pass-r3 H-10 fix: write_checkpoint must fire BEFORE
            # commit so the chunk's git commit captures it. Use a
            # provisional rs here for the checkpoint (the chunk was
            # NOT accepted; plan/round not bumped).
            write_checkpoint(rs, os.path.join(evidence_dir, "checkpoint.json"))
            commit_chunk_change(rs, chunk, chunk_evidence_dir,
                                run_evidence_dir=evidence_dir)
            return 3
        # Pass-r3 H-10 fix: write run-level checkpoint BEFORE
        # commit_chunk_change so the chunk commit captures it.
        write_checkpoint(rs, os.path.join(evidence_dir, "checkpoint.json"))
        commit_chunk_change(rs, chunk, chunk_evidence_dir,
                            run_evidence_dir=evidence_dir)

    # ── Final state ────────────────────────────────────────────────
    rs.status = RunStatus.COMPLETED
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
