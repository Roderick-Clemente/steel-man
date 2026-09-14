"""Per-chunk inner loop.

This module is **the** orchestration of one chunk's full ADR loop:

  test-designer  →  lock.py        →  valid-red.py
        ↓
  executor       →  verify-green.py
        ↓
  local_backend.py (signed EvidenceBundle)
        ↓
  LocalBackend.validate → gate decision
        ↓
  REJECT_IMPLEMENTATION? → feedback to executor, retry up to retry_threshold
  REJECT_TEST?           → feedback to test-designer, regenerate the locked
                           test, re-establish RED; bounded by the same
                           threshold on its own budget
  ACCEPT?  → next chunk (or branch+commit when last chunk)

Composition discipline (OPERATING-RULES §14): every external call in
this module is ``subprocess.run`` against an existing script under
``tools/``, ``phase-1/scripts/``, or ``phase-3.2/evidence/``. The only
exceptions are:

  - `droid exec` (via ``tools/sprint_loop.droid.invoke_droid``)
  - ``tools/orchestrate-review.py`` (via ``tools/sprint_loop.backends.LocalBackend``)

Truth assertion (OPERATING-RULES §7):

  - Lock-manifest SHA is read from the manifest file, not from a tool's
    stdout (which could be cached / spoofed).
  - ``verify-green.py`` exit is checked but ALSO the bundle's
    ``locked_test_sha_observed`` cross-checked against the lock manifest —
    both must agree before claiming GREEN.
  - The bundle's HMAC signature is verified against the same key the
    backend used; an unsigned bundle = STOP.

Telemetry (OPERATING-RULES §10):

  Every ``droid exec`` invocation runs through ``invoke_droid`` and
  emits one ``runs.jsonl`` row. Subprocess calls to non-droid scripts
  (lock.py, valid-red.py, verify-green.py, local_backend.py) emit
  no telemetry row — the orchestrator's invocation envelope does.
  That's by design: droid's role in the loop is what we measure.

Retry policy (PRD §5.7):

  REJECT from the validator → feedback fed back to executor, retry up
  to ``retry_threshold`` (default 1 per PRD §5.7). Above threshold →
  ``HUMAN_DECISION`` and the chunk pauses (the orchestrator handles
  the human gate).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

# Make tools/ importable
_TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.backends import BackendResult, LocalBackend  # noqa: E402
from sprint_loop.config import phase_path  # noqa: E402
from sprint_loop.droid import (  # noqa: E402
    InvokeOptions,
    RunRecord,
    append_run_record,
    invoke_droid,
)
from sprint_loop.prompts.render import render_to_file  # noqa: E402
from sprint_loop.provenance import _git_branch, _git_sha, run_provenance  # noqa: E402
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    Role,
    RunState,
    hash_text,
)

# ── subprocess helpers ──────────────────────────────────────────────────


def _run_step(
    cmd: list[str], label: str, cwd: str | None = None, timeout: int = 120
) -> subprocess.CompletedProcess:
    """Generic subprocess runner; surfaces exit, stderr, stdout. Label
    goes into error messages so a stop at step N is debuggable.
    """
    try:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"per_chunk step '{label}' timed out after {timeout}s: {cmd[:3]}..."
        ) from e


# ── lock step ────────────────────────────────────────────────────────────


def lock_test(
    chunk: ChunkState,
    *,
    framework_root: str,
    pilot_root: str,
    pilot_python: str,
    accepted_assertion: str,
    dry_run: bool = False,
) -> dict:
    """Run ``phase-1/scripts/lock.py`` for the chunk's test file.

    Returns the manifest dict; also stamps ``chunk.lock_manifest_path``
    and ``chunk.locked_test_sha``.

    OPERATING-RULES §7: reads the manifest from disk after
    ``lock.py`` succeeds; never trusts stdout alone.
    """
    cmd = [
        pilot_python,
        phase_path(framework_root, "scripts", "lock.py"),
        chunk.locked_test_files[0],  # primary locked test (PRD §5.4)
        accepted_assertion,
        "--pilot-root",
        pilot_root,
        "--locks-dir",
        phase_path(framework_root, "locks"),
    ]
    if dry_run:
        # Synthesize a manifest that mirrors lock.py's output shape so
        # downstream steps have something deterministic to test against.
        synth_sha = hash_text(chunk.locked_test_files[0] + "::" + accepted_assertion)[:32]
        manifest = {
            "file": chunk.locked_test_files[0],
            "sha256": synth_sha,
            "accepted_at": "1970-01-01T00:00:00+00:00",
            "accepted_assertion": accepted_assertion,
        }
        lock_path = phase_path(framework_root, "locks", f"{chunk.locked_test_files[0]}.lock.json")
        chunk.lock_manifest_path = lock_path
        chunk.locked_test_sha = synth_sha
        return manifest
    r = _run_step(cmd, "lock.py", timeout=60)
    if r.returncode != 0:
        raise RuntimeError(
            f"lock.py exited {r.returncode} for chunk '{chunk.chunk_id}': {r.stderr[:500]!r}"
        )
    # Find the lock file (lock.py writes to <LOCKS_ROOT>/<test_file>.lock.json)
    lock_path = phase_path(framework_root, "locks", f"{chunk.locked_test_files[0]}.lock.json")
    if not os.path.isfile(lock_path):
        raise RuntimeError(f"lock.py reported success but manifest missing at {lock_path}")
    with open(lock_path) as f:
        manifest = json.load(f)
    chunk.lock_manifest_path = lock_path
    chunk.locked_test_sha = manifest["sha256"]
    return manifest


# ── valid-RED step ───────────────────────────────────────────────────────


def validate_red(
    chunk: ChunkState,
    *,
    framework_root: str,
    pilot_root: str,
    pilot_python: str,
    dry_run: bool = False,
) -> dict:
    """Run ``phase-1/scripts/valid-red.py`` for the chunk's test.

    Returns the classification dict.

    PRD §5.4: a valid RED means the test collected, executed the
    intended path, reached its assertion, and failed because the
    required behavior is absent. Syntax / import / fixture failures
    are invalid.
    """
    cmd = [
        pilot_python,
        phase_path(framework_root, "scripts", "valid-red.py"),
        "--pilot-root",
        pilot_root,
        "--test-file",
        chunk.locked_test_files[0],
        "--accepted-assertion",
        chunk.accepted_assertion,
        "--python",
        pilot_python,
        "-o",
        "json",
    ]
    if dry_run:
        return {
            "valid": True,
            "reason": "dry-run: simulated valid RED",
            "exit_code": 1,
            "stdout": "[dry-run] simulated pytest output",
            "stderr": "",
        }
    r = _run_step(cmd, "valid-red.py", timeout=180)
    try:
        # valid-red.py prints JSON if the test exits non-zero, otherwise text.
        # Try JSON first.
        out = r.stdout
        try:
            cls = json.loads(out)
        except json.JSONDecodeError:
            # Fall back: text shape — "INVALID RED: <reason>" or "VALID RED: ..."
            cls = {
                "valid": r.returncode == 0,
                "reason": out.strip() or r.stderr.strip(),
                "exit_code": r.returncode,
            }
    except Exception as e:
        raise RuntimeError(
            f"valid-red.py output unparseable for '{chunk.chunk_id}': "
            f"{e}; r.returncode={r.returncode}, stdout={r.stdout[:200]!r}"
        ) from e
    if not cls.get("valid"):
        raise RuntimeError(
            f"RED rejected for '{chunk.chunk_id}': {cls.get('reason')!r} "
            f"(exit_code={cls.get('exit_code')}). Loop will route back "
            f"to the test designer."
        )
    return cls


# ── verify-green step ────────────────────────────────────────────────────


def verify_green(
    chunk: ChunkState,
    *,
    framework_root: str,
    pilot_root: str,
    pilot_python: str,
    dry_run: bool = False,
) -> dict:
    """Run ``phase-1/scripts/verify-green.py`` for the chunk's test.

    Returns the dict from verify-green if GREEN ACCEPTED; raises
    RuntimeError with the script's reasoning if GREEN REFUSED.
    """
    cmd = [
        pilot_python,
        phase_path(framework_root, "scripts", "verify-green.py"),
        "--pilot-root",
        pilot_root,
        "--lock-file",
        chunk.lock_manifest_path,
        "--test-file",
        chunk.locked_test_files[0],
        "--python",
        pilot_python,
    ]
    if dry_run:
        return {"green": True, "sha": chunk.locked_test_sha or "dry-run-sha"}
    r = _run_step(cmd, "verify-green.py", timeout=180)
    if r.returncode != 0:
        raise RuntimeError(
            f"GREFUSED chunk '{chunk.chunk_id}': verify-green.py exit "
            f"{r.returncode}; stdout={r.stdout[:300]!r} stderr={r.stderr[:300]!r}"
        )
    sha_match = re.search(r"sha256:\s+(\w+)", r.stdout)
    return {"green": True, "sha": sha_match.group(1) if sha_match else None}


# ── evidence production ─────────────────────────────────────────────────


def produce_evidence(
    chunk: ChunkState,
    *,
    framework_root: str,
    pilot_root: str,
    pilot_python: str,
    evidence_output_path: str,
    dry_run: bool = False,
    signing_key_env: str = "EVIDENCE_SIGNING_KEY",
    security_scan: bool = False,
    security_allowlist: str = "",
    security_baseline: str = "",
    full_suite: bool = False,
    full_suite_command: str = "",
) -> dict:
    """Run ``phase-3.2/evidence/local_backend.py`` to produce a signed
    EvidenceBundle. Returns the bundle dict (parsed).

    ``full_suite_command`` is the chunk's declared regression command and is
    what the producer runs for ``tests.full_suite``. Passing ``full_suite``
    alone leaves the producer running bare ``pytest`` from the pilot root,
    which collects nothing in a pilot whose tests live in a subdirectory.

    Asserts the bundle signature against EVIDENCE_SIGNING_KEY — the
    producer signs, the consumer verifies; this side verifies too
    so the orchestrator catches a stale-signature signing-key change
    before passing the bundle to validators.
    """
    full_suite = full_suite or bool(full_suite_command)
    if dry_run:
        tests: dict = {
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "suite_exit_code": 0,
            "failures": [],
            "scope": "locked-test",
        }
        if full_suite:
            tests["full_suite"] = {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "suite_exit_code": 0,
                "failures": [],
                "scope": "full-suite",
                "command": full_suite_command,
            }
        bundle = {
            "bundle_schema_version": "v1",
            "producer": "local-dry-run",
            "change": {
                "commit_sha": "0000000000000000000000000000000000000000",
                "locked_test_sha_observed": chunk.locked_test_sha or "",
            },
            "tests": tests,
            "provenance": {
                "producer_run_id": "dry-run",
                "started_at": "1970-01-01T00:00:00Z",
                "finished_at": "1970-01-01T00:00:01Z",
                "tool_versions": {"python": "dry-run"},
            },
            "signature": {
                "algorithm": "HMAC-SHA256",
                "value": "dry-run-no-sig",
                "key_id": "dry-run",
            },
        }
        with open(evidence_output_path, "w") as f:
            json.dump(bundle, f, indent=2)
        chunk.evidence_bundle_path = evidence_output_path
        return bundle
    cmd = [
        pilot_python,
        phase_path(framework_root, "evidence-code", "local_backend.py"),
        "--pilot-root",
        pilot_root,
        "--framework-root",
        framework_root,
        "--test-file",
        chunk.locked_test_files[0],
        "--lock-file",
        chunk.lock_manifest_path,
        "--output",
        evidence_output_path,
        "--python",
        pilot_python,
        "--signing-key-env",
        signing_key_env,
        "--key-id",
        f"phase-4.5-{chunk.chunk_id}",
    ]
    if full_suite:
        cmd.append("--full-suite")
    if full_suite_command:
        cmd.extend(["--full-suite-command", full_suite_command])
    if security_scan:
        cmd.append("--security-scan")
        if security_allowlist:
            cmd.extend(["--security-allowlist", security_allowlist])
        if security_baseline:
            cmd.extend(["--security-baseline", security_baseline])
    r = _run_step(cmd, "local_backend.py", timeout=300)
    if r.returncode != 0:
        print(f"[evidence] local_backend.py stderr: {r.stderr[:300]!r}", file=sys.stderr)
        # local_backend.py exits non-zero on RED; surface a structured failure.
        if not os.path.isfile(evidence_output_path):
            raise RuntimeError(
                f"local_backend.py exit {r.returncode} AND no bundle at "
                f"{evidence_output_path} — chunk '{chunk.chunk_id}' "
                f"cannot evidence a RED state"
            )
    if not os.path.isfile(evidence_output_path):
        raise RuntimeError(f"local_backend.py produced no bundle at {evidence_output_path}")
    with open(evidence_output_path) as f:
        bundle = json.load(f)

    # Cross-check the bundle's locked_test_sha_observed against the lock
    # manifest (PRD §5.7 / §4.1). Mismatch is fail-closed.
    observed = bundle.get("change", {}).get("locked_test_sha_observed")
    if not observed:
        raise RuntimeError("bundle has no locked_test_sha_observed — fail-closed per §7")

    if observed != chunk.locked_test_sha:
        raise RuntimeError(
            f"locked_test_sha_observed mismatch: bundle={observed} "
            f"manifest={chunk.locked_test_sha} (PRD §4.1 fail-closed)"
        )

    # A chunk whose regression run is not in the bundle leaves the
    # validator with no evidence for "existing behaviour unchanged", and
    # the executor's prose claim is not evidence (§7).
    if full_suite and not (bundle.get("tests") or {}).get("full_suite"):
        raise RuntimeError(
            f"chunk '{chunk.chunk_id}' defines a full-suite command but the "
            f"bundle at {evidence_output_path} carries no tests.full_suite "
            f"section — the validator would have no regression evidence"
        )

    # Verify the signature against the signing key the backend used.
    sig = bundle.get("signature") or {}
    if sig.get("algorithm") != "HMAC-SHA256":
        raise RuntimeError(
            f"bundle signature algorithm {sig.get('algorithm')!r} not "
            f"HMAC-SHA256 — refusing to trust unsigned bundle"
        )
    signing_key = os.environ.get(signing_key_env)
    if not signing_key:
        raise RuntimeError(
            f"{signing_key_env} not set — cannot verify bundle signature. "
            f"Set it to the same value the backend used."
        )
    import hashlib
    import hmac

    payload = {k: v for k, v in bundle.items() if k != "signature"}
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(signing_key.encode(), payload_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig.get("value", "")):
        raise RuntimeError(
            "bundle signature FAILED verification — refusing to "
            "forward the bundle to validators (PRD §7 fail-closed)"
        )

    chunk.evidence_bundle_path = evidence_output_path
    return bundle


# ── per-role invocations ─────────────────────────────────────────────────


def _emit_seat_row(rr: RunRecord, chunk: ChunkState, rs: RunState, phase_step: str) -> None:
    """Stamp v3 funnel/provenance fields on a per-chunk seat record and
    append it to ``runs.jsonl``."""
    rr.chunk_id = chunk.chunk_id
    rr.run_label = rs.run_label
    rr.phase_step = phase_step
    rr.provenance = run_provenance(rs)
    append_run_record(
        rr,
        phase="phase-4.5",
        branch=_git_branch(rs.framework_root),
        telemetry_path=os.path.join(rs.framework_root, "telemetry", "runs.jsonl"),
    )


def invoke_test_designer(
    chunk: ChunkState,
    rs: RunState,
    *,
    evidence_output_dir: str,
    rendered_prompt_path: str,
    envelope_path: str,
    dry_run: bool = False,
    phase_step: str = "test-design",
) -> dict:
    """Invoke the test_designer droid role for this chunk.

    Writes the rendered prompt to ``rendered_prompt_path``, fires the
    droid call, parses the envelope. The test_designer role MUST
    produce a test file at ``chunk.locked_test_files[0]``; the orchestrator
    then calls ``lock_test`` to lock it.
    """
    options = InvokeOptions(
        model_id=rs.test_designer.pinned_model_id or "claude-opus-5",
        auto_level=rs.test_designer.auto_level,
        enabled_tools=rs.test_designer.enabled_tools,
        prompt_file=rendered_prompt_path,
        cwd=rs.pilot_root,
        timeout_seconds=rs.per_call_timeout_seconds or 1800,
    )
    rr = invoke_droid(
        Role.TEST_DESIGNER,
        options=options,
        envelope_path=envelope_path,
        stderr_path=os.path.join(evidence_output_dir, "stderr-test-designer.log"),
        max_retries=rs.max_auto_retries,
        retry_delay_seconds=rs.retry_delay_seconds,
        dry_run=dry_run,
    )
    rs.test_designer.resolved_model_id = rr.model_id
    rs.test_designer.resolved_family = rr.family
    rs.test_designer.num_turns = rr.num_turns
    rs.test_designer.input_tokens = rr.input_tokens
    rs.test_designer.output_tokens = rr.output_tokens
    rs.test_designer.duration_ms = rr.duration_ms
    rs.test_designer.is_error = rr.is_error
    rs.test_designer.envelope_path = rr.envelope_path
    rs.test_designer.run_id = rr.run_id
    chunk.test_designer_run_id = rr.run_id
    _emit_seat_row(rr, chunk, rs, phase_step)
    # The accepted assertion was emitted by the test-designer; the
    # runner parses it out of the result text. For dry-run / chunk that
    # was loaded via chunks_file, the assertion is already in
    # chunk.accepted_assertion and the renderer substituted it in the
    # prompt.
    return {"record": rr, "result_text": _read_envelope_result_text(rr.envelope_path)}


def invoke_executor(
    chunk: ChunkState,
    rs: RunState,
    *,
    evidence_output_dir: str,
    rendered_prompt_path: str,
    envelope_path: str,
    dry_run: bool = False,
) -> dict:
    """Invoke the executor droid role for this chunk.

    The executor writes the implementation to the pilot repo; the
    orchestrator calls ``verify_green`` next.
    """
    options = InvokeOptions(
        model_id=rs.executor.pinned_model_id or "gpt-5.4-mini",
        auto_level=rs.executor.auto_level,
        enabled_tools=rs.executor.enabled_tools,
        prompt_file=rendered_prompt_path,
        cwd=rs.pilot_root,
        timeout_seconds=rs.per_call_timeout_seconds or 1800,
    )
    rr = invoke_droid(
        Role.EXECUTOR,
        options=options,
        envelope_path=envelope_path,
        stderr_path=os.path.join(evidence_output_dir, "stderr-executor.log"),
        max_retries=rs.max_auto_retries,
        retry_delay_seconds=rs.retry_delay_seconds,
        dry_run=dry_run,
    )
    rs.executor.resolved_model_id = rr.model_id
    rs.executor.resolved_family = rr.family
    rs.executor.num_turns = rr.num_turns
    rs.executor.input_tokens = rr.input_tokens
    rs.executor.output_tokens = rr.output_tokens
    rs.executor.duration_ms = rr.duration_ms
    rs.executor.is_error = rr.is_error
    rs.executor.envelope_path = rr.envelope_path
    rs.executor.run_id = rr.run_id
    chunk.executor_run_id = rr.run_id
    # Stamp the feedback source on the seat row so a finding-carrying
    # retry is distinguishable from a gate-reason-only one in runs.jsonl.
    # Only set on a retry (retry_count > 0); a first attempt has no prior
    # rejection to carry.
    if chunk.retry_count > 0 and chunk.rejection_feedback_source:
        tag = f"retry_feedback_source={chunk.rejection_feedback_source}"
        rr.note = f"{rr.note}; {tag}" if rr.note else tag
    _emit_seat_row(rr, chunk, rs, "execute")
    return {"record": rr, "result_text": _read_envelope_result_text(rr.envelope_path)}


def run_validators(
    chunk: ChunkState,
    rs: RunState,
    *,
    evidence_output_dir: str,
    dry_run: bool = False,
    full_suite_command: str | None = None,
) -> BackendResult:
    """Run the cross-family validator panel via LocalBackend.

    Returns a ``BackendResult`` with ``gate`` and ``reason`` already set.
    The orchestrator propagates gate decisions into chunk.gate_decision
    and decides retry-via-executor or move-on.

    ``full_suite_command`` is the same regression command the evidence step
    ran; it has to reach ``orchestrate-review.py`` because that script
    re-produces the bundle in place, and a re-production without it strips
    the regression section out from under the validators. ``None`` derives it
    from the chunk so a caller cannot silently skip it.
    """
    if full_suite_command is None:
        full_suite_command = chunk_full_suite_command(chunk)
    backend = LocalBackend(dry_run=dry_run)
    validators_csv = [
        f"{v.pinned_model_id}:{v.pinned_provider}:{v.pinned_family}:{v.pinned_model_id}"
        for v in rs.validators
    ]
    review_output_dir = os.path.join(evidence_output_dir, "reviews")
    # The validator prompt is rendered (not handed over as a raw template)
    # and archived next to the validator envelopes, like every other seat's
    # prompt. Passing the template path here is what let both validator
    # seats run on literal ``{{...}}`` placeholders.
    rendered_prompt = render_validator_prompt(
        chunk,
        rs,
        output_path=os.path.join(review_output_dir, f"{chunk.chunk_id}-va-prompt.md"),
    )
    # Per §17.5 — validators get ``Read,Glob,Grep,LS`` in bundle mode.
    # ``Execute`` is NOT in the allowlist (KI-2 preventive fix).
    res = backend.validate(
        chunk={
            "test_file": chunk.locked_test_files[0],
            "lock_file": chunk.lock_manifest_path,
            "review_output_dir": review_output_dir,
            "scope": chunk.scope,
        },
        evidence_bundle=chunk.evidence_bundle_path,
        framework_root=rs.framework_root,
        pilot_root=rs.pilot_root,
        pilot_python=rs.pilot_python,
        signing_key_env=rs.signing_key_env,
        validators=validators_csv,
        run_label=f"{rs.run_id}-{chunk.chunk_id}",
        prompt_template_path=rendered_prompt,
        enabled_tools="Read,Glob,Grep,LS",
        evidence_source="bundle",
        full_suite_command=full_suite_command,
        run_id=rs.run_id,
        phase=rs.run_id.split("-")[0] if "-" in rs.run_id else "phase-4.5",
        branch=_git_branch(rs.framework_root),
    )
    chunk.validator_run_ids = [
        v.get("label") or v.get("model") or "<unknown>" for v in res.validators
    ]
    return res


# ── rejection routing ────────────────────────────────────────────────────

# Verdicts that name the LOCKED TEST, not the implementation, as the thing
# at fault. ``orchestrate-review.py:step4_parse_verdicts`` recognises the
# full vocabulary (ACCEPT, ACCEPT-WITH-NITS, REJECT_IMPLEMENTATION,
# REJECT_TEST, REJECT, HUMAN_DECISION) but collapses every REJECT* to one
# ``REJECT`` gate, so the distinction survives only in the per-validator
# verdicts the summary carries.
TEST_DIRECTED_VERDICTS: frozenset = frozenset({"REJECT_TEST"})

REJECTION_TEST = "test"
REJECTION_IMPLEMENTATION = "implementation"

_NO_TEST_REJECTION_FEEDBACK = "(no prior test rejection — author the test from the chunk spec)"
_NO_IMPL_REJECTION_FEEDBACK = (
    "This is the first attempt at this chunk — no previous implementation was "
    "rejected. Implement from the chunk spec."
)

# Mirrors ``orchestrate-review.py``'s REVIEW_FINDING_TEXT_LIMIT: that is
# what the review summary already clips a seat's prose to, so a per-seat
# block in a prompt cannot usefully carry more, and a runaway review must
# not be able to crowd the chunk spec out of the prompt.
REVIEW_FINDING_TEXT_LIMIT = 4000

# Which telemetry answer a retry's prompt earned. ``validator-finding``
# means the rejecting seats' own prose reached the executor;
# ``gate-reason`` means only the one-line gate string was available
# (dry-run, or a rejection that never reached the validator panel).
FEEDBACK_SOURCE_VALIDATOR_FINDING = "validator-finding"
FEEDBACK_SOURCE_GATE_REASON = "gate-reason"


def _clip_finding(text: str, limit: int = REVIEW_FINDING_TEXT_LIMIT) -> str:
    """Length-cap a seat's prose without flattening it to one line.

    ``sprint-loop.py:_clip`` flattens whitespace because it renders
    findings into single-line console output; a prompt block keeps the
    reviewer's paragraphs, so only the cap carries over.
    """
    body = (text or "").strip()
    if len(body) <= limit:
        return body
    return body[: limit - 1].rstrip() + "…"


def _defuse_placeholders(text: str) -> str:
    """Break ``{{...}}`` sequences inside seat-supplied prose.

    A validator that quotes a prompt template — which KI-10's reviews did
    verbatim — would otherwise plant a live-looking placeholder in the
    next seat's prompt and trip ``assert_prompt_fully_rendered`` on text
    that was never a placeholder at all.
    """
    return (text or "").replace("{{", "{ {").replace("}}", "} }")


def _is_test_directed(verdict: str) -> bool:
    return verdict in TEST_DIRECTED_VERDICTS


def _is_implementation_directed(verdict: str) -> bool:
    """A rejecting verdict the EXECUTOR can act on.

    A ``REJECT_TEST`` seat on a mixed panel is deliberately excluded: its
    finding asks for a different locked test, which the executor is
    forbidden to touch (invariant #3). Handing it over invites the seat
    to argue with the contract instead of meeting it; that finding goes
    to the test-designer's own block.
    """
    return verdict.startswith("REJECT") and not _is_test_directed(verdict)


def _format_rejecting_seats(result: BackendResult, predicate, *, why_label: str) -> list[str]:
    """One markdown block per rejecting seat, attributed to its model id.

    Order is the panel order the backend reports (which is the configured
    validator order), so two runs over the same panel render the seats
    the same way. Seats that accepted are skipped entirely: an approval
    beside a refusal reads as permission to change nothing.
    """
    parts: list[str] = []
    for v in result.validators or []:
        verdict = str((v or {}).get("verdict") or "").strip().upper()
        if not predicate(verdict):
            continue
        text = _clip_finding(v.get("finding_text") or "")
        if not text:
            # A verdict with no reasoning tells the next seat nothing;
            # the gate reason the caller falls back to is more useful
            # than a bare label.
            continue
        label = v.get("label") or v.get("model") or "(unlabelled validator)"
        body = [f"### {label} — {verdict}"]
        if v.get("model"):
            body.append(f"- **Model**: {v['model']} ({v.get('family') or 'unknown family'})")
        body.append(f"- **{why_label}**:")
        body.append("")
        body.append(_defuse_placeholders(text))
        if v.get("envelope_path"):
            body.append(f"- **Full review envelope**: {v['envelope_path']}")
        parts.append("\n".join(body))
    return parts


def classify_rejection(validators: list[dict]) -> str:
    """Which seat a validator panel's rejection is directed at.

    Returns ``"test"`` when every rejecting verdict is test-directed,
    ``"implementation"`` when at least one rejects the code, and ``""``
    when nothing was rejected.

    A mixed panel routes to the implementation: one seat holding the
    locked test to be a fair contract means the code has to change, and
    regenerating the test would discard that finding.
    """
    verdicts = [str((v or {}).get("verdict") or "").strip().upper() for v in (validators or [])]
    rejects = [v for v in verdicts if v.startswith("REJECT")]
    if not rejects:
        return ""
    if all(v in TEST_DIRECTED_VERDICTS for v in rejects):
        return REJECTION_TEST
    return REJECTION_IMPLEMENTATION


def format_test_rejection_feedback(result: BackendResult) -> str:
    """Render the test-directed findings for the test-designer prompt.

    Same spirit as the planner's prior-findings block: without the
    rejecting seat's actual reasoning the designer regenerates a
    near-identical test and the next validator round re-finds the same
    gap. Never raises — this is prompt context, not flow control.
    """
    try:
        parts = _format_rejecting_seats(
            result, _is_test_directed, why_label="Why the locked test was rejected"
        )
        if not parts:
            # The gate reason is the only thing left when a backend
            # reports no per-validator text (e.g. dry-run).
            reason = (result.reason or "").strip()
            return reason or _NO_TEST_REJECTION_FEEDBACK
        header = (
            f"The validator panel rejected the PREVIOUS locked test as "
            f"inadequate ({len(parts)} test-directed verdict(s)). The "
            f"implementation was NOT found at fault. Regenerate the test so "
            f"it actually locks what the chunk claims."
        )
        return header + "\n\n" + "\n\n".join(parts)
    except Exception:
        return _NO_TEST_REJECTION_FEEDBACK


def format_implementation_rejection_feedback(result: BackendResult) -> str:
    """Render the implementation-directed findings for the executor prompt.

    Sibling to ``format_test_rejection_feedback``: same structure (one
    attributed block per rejecting seat, clipped, skipping acceptors), a
    different header. Without the rejecting seat's own reasoning the
    executor re-runs the most expensive seat in the pipeline with no
    knowledge of why the previous attempt was refused (KI-16). Never
    raises — this is prompt context, not flow control.

    A ``REJECT_TEST`` verdict on a mixed panel is deliberately skipped:
    its finding asks for a different locked test, which the executor is
    forbidden to touch (invariant #3); the test-designer carries it.
    """
    try:
        parts = _format_rejecting_seats(
            result,
            _is_implementation_directed,
            why_label="Why the implementation was rejected",
        )
        if not parts:
            reason = (result.reason or "").strip()
            return reason or _NO_IMPL_REJECTION_FEEDBACK
        header = (
            f"The validator panel rejected the PREVIOUS implementation "
            f"({len(parts)} implementation-directed verdict(s)). The locked "
            f"test is a fair contract — the CODE is at fault. Read each "
            f"finding and fix the gap it names; do not duplicate the rejected "
            f"work."
        )
        return header + "\n\n" + "\n\n".join(parts)
    except Exception:
        return _NO_IMPL_REJECTION_FEEDBACK


def implementation_rejection_has_finding(result: BackendResult) -> bool:
    """True if at least one implementation-directed seat carried finding text.

    Used to stamp the telemetry source so a finding-carrying retry is
    distinguishable from one that only had the gate-reason fallback.
    """
    for v in result.validators or []:
        verdict = str((v or {}).get("verdict") or "").strip().upper()
        if _is_implementation_directed(verdict) and (v.get("finding_text") or "").strip():
            return True
    return False


def archive_superseded_test(
    chunk: ChunkState,
    rs: RunState,
    *,
    evidence_output_dir: str,
    round_index: int,
) -> dict:
    """Move the rejected locked test and the review that rejected it aside.

    Failed-run evidence is renamed, never deleted: both artifacts are the
    proof that the panel rejected THIS test text, and the next round
    overwrites the review directory and the test file in place. The test
    is moved out of the pilot tree (not copied) because its absence is
    what makes the test-designer auto-fire path re-author it.
    """
    dest = os.path.join(evidence_output_dir, f"superseded-test-round{round_index}")
    os.makedirs(dest, exist_ok=True)
    moved: dict = {}
    if chunk.locked_test_files:
        test_abs = os.path.join(rs.pilot_root, chunk.locked_test_files[0])
        if os.path.isfile(test_abs):
            target = os.path.join(dest, os.path.basename(test_abs))
            shutil.move(test_abs, target)
            moved["locked_test"] = target
    reviews_dir = os.path.join(evidence_output_dir, "reviews")
    if os.path.isdir(reviews_dir):
        target = os.path.join(dest, "reviews")
        if os.path.exists(target):
            target = os.path.join(dest, f"reviews-{len(os.listdir(dest))}")
        shutil.move(reviews_dir, target)
        moved["reviews"] = target
    return moved


# ── helpers ──────────────────────────────────────────────────────────────


def _read_envelope_result_text(envelope_path: str) -> str:
    """Pluck ``result`` text from a droid envelope for parsing."""
    try:
        with open(envelope_path) as f:
            env = json.load(f)
        return env.get("result") or ""
    except (OSError, json.JSONDecodeError):
        return ""


# ── render role prompts per chunk ────────────────────────────────────────


def render_test_designer_prompt(
    chunk: ChunkState, rs: RunState, pilot_spec_text: str, output_path: str
) -> str:
    """Render the test_designer role prompt for this chunk.

    Carries ``chunk.test_design_feedback`` — the validator findings that
    rejected a previous locked test — so a re-fired designer knows which
    part of the chunk the superseded test failed to lock.
    """
    test_rel = chunk.locked_test_files[0]
    sibling_dir = os.path.dirname(test_rel) or "."
    return render_to_file(
        "test-designer",
        {
            "prior_test_rejection": (
                "\n\n".join(t for t in chunk.test_design_feedback if t)
                or _NO_TEST_REJECTION_FEEDBACK
            ),
            "chunk_spec": _format_chunk_spec(chunk),
            "pilot_root": rs.pilot_root,
            "pilot_spec": pilot_spec_text,
            "test_file_path": os.path.join(rs.pilot_root, test_rel),
            "pytest_baseline_path": (
                chunk.commands[0] if chunk.commands else "(no baseline command in chunk spec)"
            ),
            "sibling_tests_pattern": os.path.join(rs.pilot_root, sibling_dir),
        },
        output_path,
    )


def render_executor_prompt(chunk: ChunkState, rs: RunState,
                           output_path: str,
                           verify_and_harden: bool = False) -> str:
    """Render the executor role prompt for this chunk.

    When ``verify_and_harden=True`` (§5.3 verify mode), the prompt
    context instructs the executor to verify and harden the existing
    implementation rather than build from scratch.

    Carries ``chunk.rejection_feedback`` — the implementation-directed
    validator findings that rejected a previous attempt — so a re-fired
    executor knows which criterion the previous diff failed. Without it
    a retry is the same dice roll at full cost (KI-16).
    """
    verify_directive = ""
    if verify_and_harden:
        verify_directive = (
            "> **VERIFY-AND-HARDEN MODE (§5.3 relaxation):** The changes\n"
            "> already exist at HEAD — the locked test is already GREEN.\n"
            "> Your job is NOT to build from scratch. Review the existing\n"
            "> implementation against the chunk spec and observable\n"
            "> criteria. Harden it: fix edge cases, improve error paths,\n"
            "> add defensive checks, and ensure the full suite still\n"
            "> passes. Do NOT break the existing GREEN test. If the\n"
            "> existing implementation is already correct and complete,\n"
            "> make minimal or no changes — the validator will confirm.\n"
        )
    # The rejection_feedback list carries the formatted findings from the
    # previous round's implementation-directed rejection. On a first
    # attempt (or an ACCEPT that cleared it) the list is empty — pass an
    # empty string so the {{...}} placeholder resolves to nothing and no
    # prior-rejection section appears. When findings exist, wrap them in
    # a heading so the section is self-contained in the rendered prompt.
    prior_body = "\n\n".join(t for t in chunk.rejection_feedback if t)
    prior_rejection = (
        "## Prior rejection feedback\n\n" + prior_body if prior_body else ""
    )
    rendered_path = render_to_file(
        "executor",
        {
            "chunk_spec": _format_chunk_spec(chunk),
            "pilot_root": rs.pilot_root,
            "test_file_path": os.path.join(rs.pilot_root, chunk.locked_test_files[0]),
            "commands": "\n".join(chunk.commands),
            "verify_and_harden_directive": verify_directive,
            "prior_implementation_rejection": prior_rejection,
        },
        output_path,
    )
    with open(rendered_path) as f:
        assert_prompt_fully_rendered(
            f.read(), prompt_path=rendered_path, role="executor"
        )
    return rendered_path


def render_validator_prompt(chunk: ChunkState, rs: RunState, output_path: str) -> str:
    """Render the validator role prompt for this chunk.

    Returns the absolute path of the rendered file, which is what the
    backend must hand to ``droid exec`` — never the template.
    """
    rendered_path = render_to_file(
        "validator",
        {
            "chunk_spec": _format_chunk_spec(chunk),
            "branch": _git_branch(rs.pilot_root),
            "commit": _commit_under_review(chunk, rs),
            "pilot_root": rs.pilot_root,
            "test_file_path": os.path.join(rs.pilot_root, chunk.locked_test_files[0]),
            "evidence_bundle_path": chunk.evidence_bundle_path,
        },
        output_path,
    )
    with open(rendered_path) as f:
        assert_prompt_fully_rendered(f.read(), prompt_path=rendered_path, role="validator")
    return rendered_path


_PLACEHOLDER_RE = re.compile(r"\{\{[^{}]*\}\}")


def assert_prompt_fully_rendered(rendered: str, *, prompt_path: str, role: str) -> None:
    """Raise if a rendered prompt still carries ``{{...}}`` placeholders.

    A seat handed an unrendered template has no spec, no diff and no
    bundle: whatever verdict it emits is unsound. §7 — that must be a
    loud failure, never a silent one.
    """
    if "{{" not in rendered:
        return
    unresolved = sorted(set(_PLACEHOLDER_RE.findall(rendered)))
    named = ", ".join(unresolved) if unresolved else "{{ (unparseable placeholder)"
    raise RuntimeError(
        f"{role} prompt at {prompt_path} still contains unresolved "
        f"placeholders: {named}. Refusing to invoke the {role} seat on an "
        f"unrendered template — it would review nothing and its verdict "
        f"would be unsound (§7)."
    )


def _commit_under_review(chunk: ChunkState, rs: RunState) -> str:
    """The commit the evidence bundle attests, falling back to pilot HEAD.

    The bundle's ``change.commit_sha`` is authoritative: it is the commit
    the producer actually hashed and ran against, which is what the
    validator must review.
    """
    try:
        with open(chunk.evidence_bundle_path) as f:
            bundle = json.load(f)
        commit = (bundle.get("change") or {}).get("commit_sha") or ""
    except (OSError, TypeError, json.JSONDecodeError):
        commit = ""
    return commit or _git_sha(rs.pilot_root)


def chunk_full_suite_command(chunk: ChunkState) -> str:
    """The chunk's regression command, if it names one distinct from the
    locked test.

    A pytest command that does not name any locked test file runs more
    than the locked test — that is the chunk's "existing behaviour
    unchanged" evidence, and the bundle has to carry its outcome or the
    validator cannot evidence that criterion.
    """
    locked = [f for f in chunk.locked_test_files if f]
    for cmd in chunk.commands:
        if "pytest" not in cmd:
            continue
        if not any(f in cmd for f in locked):
            return cmd
    return ""


def _format_chunk_spec(chunk: ChunkState) -> str:
    lines = [
        f"CHUNK_ID: {chunk.chunk_id}",
        f"SCOPE: {chunk.scope}",
        "OBSERVABLE_CRITERIA:",
    ]
    for c in chunk.observable_criteria:
        lines.append(f"  - {c}")
    if chunk.allowed_files:
        lines.append("ALLOWED_FILES:")
        for f in chunk.allowed_files:
            lines.append(f"  - {f}")
    if chunk.locked_test_files:
        lines.append("LOCKED_TEST_FILES:")
        for f in chunk.locked_test_files:
            lines.append(f"  - {f}")
    if chunk.commands:
        lines.append("COMMANDS:")
        for c in chunk.commands:
            lines.append(f"  - {c}")
    if chunk.rollback:
        lines.append(f"ROLLBACK: {chunk.rollback}")
    if chunk.accepted_assertion:
        # verify-green greps the locked test source for this phrase;
        # a designer who never sees it cannot satisfy the gate.
        lines.append(f"ACCEPTED_ASSERTION: {chunk.accepted_assertion}")
    return "\n".join(lines)
