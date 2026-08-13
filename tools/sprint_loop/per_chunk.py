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
  REJECT?  → feedback to executor, retry up to retry_threshold
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
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

# Make tools/ importable
_TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.state import (  # noqa: E402
    ChunkState,
    ChunkStatus,
    GateDecision,
    Role,
    RoleAssignment,
    RunState,
    hash_text,
)
from sprint_loop.config import phase_path  # noqa: E402
from sprint_loop.droid import InvokeOptions, invoke_droid  # noqa: E402
from sprint_loop.backends import LocalBackend, BackendResult  # noqa: E402
from sprint_loop.prompts.render import render_to_file  # noqa: E402


# ── subprocess helpers ──────────────────────────────────────────────────

def _run_step(cmd: list[str], label: str, cwd: str | None = None,
              timeout: int = 120) -> subprocess.CompletedProcess:
    """Generic subprocess runner; surfaces exit, stderr, stdout. Label
    goes into error messages so a stop at step N is debuggable.
    """
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"per_chunk step '{label}' timed out after {timeout}s: {cmd[:3]}..."
        ) from e


# ── lock step ────────────────────────────────────────────────────────────

def lock_test(chunk: ChunkState, *, framework_root: str, pilot_root: str,
              pilot_python: str, accepted_assertion: str, dry_run: bool = False) -> dict:
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
        "--pilot-root", pilot_root,
        "--locks-dir", phase_path(framework_root, "locks"),
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
        lock_path = phase_path(framework_root, "locks",
                               f"{chunk.locked_test_files[0]}.lock.json")
        chunk.lock_manifest_path = lock_path
        chunk.locked_test_sha = synth_sha
        return manifest
    r = _run_step(cmd, "lock.py", timeout=60)
    if r.returncode != 0:
        raise RuntimeError(
            f"lock.py exited {r.returncode} for chunk '{chunk.chunk_id}': "
            f"{r.stderr[:500]!r}"
        )
    # Find the lock file (lock.py writes to phase-1/locks/<test_file>.lock.json)
    lock_path = phase_path(framework_root, "locks",
                           f"{chunk.locked_test_files[0]}.lock.json")
    if not os.path.isfile(lock_path):
        raise RuntimeError(
            f"lock.py reported success but manifest missing at {lock_path}"
        )
    with open(lock_path) as f:
        manifest = json.load(f)
    chunk.lock_manifest_path = lock_path
    chunk.locked_test_sha = manifest["sha256"]
    return manifest


# ── valid-RED step ───────────────────────────────────────────────────────

def validate_red(chunk: ChunkState, *, framework_root: str, pilot_root: str,
                 pilot_python: str, dry_run: bool = False) -> dict:
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
        "--pilot-root", pilot_root,
        "--test-file", chunk.locked_test_files[0],
        "--accepted-assertion", chunk.accepted_assertion,
        "--python", pilot_python,
        "-o", "json",
    ]
    if dry_run:
        return {"valid": True, "reason": "dry-run: simulated valid RED",
                "exit_code": 1,
                "stdout": "[dry-run] simulated pytest output",
                "stderr": ""}
    r = _run_step(cmd, "valid-red.py", timeout=180)
    try:
        # valid-red.py prints JSON if the test exits non-zero, otherwise text.
        # Try JSON first.
        out = r.stdout
        try:
            cls = json.loads(out)
        except json.JSONDecodeError:
            # Fall back: text shape — "INVALID RED: <reason>" or "VALID RED: ..."
            cls = {"valid": r.returncode == 0,
                   "reason": out.strip() or r.stderr.strip(),
                   "exit_code": r.returncode}
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

def verify_green(chunk: ChunkState, *, framework_root: str, pilot_root: str,
                 pilot_python: str, dry_run: bool = False) -> dict:
    """Run ``phase-1/scripts/verify-green.py`` for the chunk's test.

    Returns the dict from verify-green if GREEN ACCEPTED; raises
    RuntimeError with the script's reasoning if GREEN REFUSED.
    """
    cmd = [
        pilot_python,
        phase_path(framework_root, "scripts", "verify-green.py"),
        "--pilot-root", pilot_root,
        "--lock-file", chunk.lock_manifest_path,
        "--test-file", chunk.locked_test_files[0],
        "--python", pilot_python,
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

def produce_evidence(chunk: ChunkState, *, framework_root: str,
                     pilot_root: str, pilot_python: str,
                     evidence_output_path: str,
                     dry_run: bool = False,
                     signing_key_env: str = "EVIDENCE_SIGNING_KEY",
                     security_scan: bool = False,
                     security_allowlist: str = "",
                     security_baseline: str = "",
                     full_suite: bool = False,
                     ) -> dict:
    """Run ``phase-3.2/evidence/local_backend.py`` to produce a signed
    EvidenceBundle. Returns the bundle dict (parsed).

    Asserts the bundle signature against EVIDENCE_SIGNING_KEY — the
    producer signs, the consumer verifies; this side verifies too
    so the orchestrator catches a stale-signature signing-key change
    before passing the bundle to validators.
    """
    if dry_run:
        bundle = {
            "bundle_schema_version": "v1",
            "producer": "local-dry-run",
            "change": {
                "commit_sha": "0000000000000000000000000000000000000000",
                "locked_test_sha_observed": chunk.locked_test_sha or "",
            },
            "tests": {
                "passed": 1, "failed": 0, "skipped": 0,
                "suite_exit_code": 0, "failures": [],
            },
            "provenance": {
                "producer_run_id": "dry-run",
                "started_at": "1970-01-01T00:00:00Z",
                "finished_at": "1970-01-01T00:00:01Z",
                "tool_versions": {"python": "dry-run"},
            },
            "signature": {"algorithm": "HMAC-SHA256",
                          "value": "dry-run-no-sig",
                          "key_id": "dry-run"},
        }
        with open(evidence_output_path, "w") as f:
            json.dump(bundle, f, indent=2)
        chunk.evidence_bundle_path = evidence_output_path
        return bundle
    cmd = [
        pilot_python,
        phase_path(framework_root, "evidence-code", "local_backend.py"),
        "--pilot-root", pilot_root,
        "--framework-root", framework_root,
        "--test-file", chunk.locked_test_files[0],
        "--lock-file", chunk.lock_manifest_path,
        "--output", evidence_output_path,
        "--python", pilot_python,
        "--signing-key-env", signing_key_env,
        "--key-id", f"phase-4.5-{chunk.chunk_id}",
    ]
    if full_suite:
        cmd.append("--full-suite")
    if security_scan:
        cmd.append("--security-scan")
        if security_allowlist:
            cmd.extend(["--security-allowlist", security_allowlist])
        if security_baseline:
            cmd.extend(["--security-baseline", security_baseline])
    r = _run_step(cmd, "local_backend.py", timeout=300)
    if r.returncode != 0:
        print(f"[evidence] local_backend.py stderr: {r.stderr[:300]!r}",
              file=sys.stderr)
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
        raise RuntimeError(
            f"bundle has no locked_test_sha_observed — fail-closed per §7"
        )
    if observed != chunk.locked_test_sha:
        raise RuntimeError(
            f"locked_test_sha_observed mismatch: bundle={observed} "
            f"manifest={chunk.locked_test_sha} (PRD §4.1 fail-closed)"
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
    expected = hmac.new(signing_key.encode(), payload_bytes,
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig.get("value", "")):
        raise RuntimeError(
            f"bundle signature FAILED verification — refusing to "
            f"forward the bundle to validators (PRD §7 fail-closed)"
        )

    chunk.evidence_bundle_path = evidence_output_path
    return bundle


# ── per-role invocations ─────────────────────────────────────────────────

def invoke_test_designer(chunk: ChunkState, rs: RunState, *,
                         evidence_output_dir: str,
                         rendered_prompt_path: str,
                         envelope_path: str,
                         dry_run: bool = False) -> dict:
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
    )
    rr = invoke_droid(Role.TEST_DESIGNER, options=options,
                     envelope_path=envelope_path,
                     stderr_path=os.path.join(evidence_output_dir, "stderr-test-designer.log"),
                     max_retries=rs.max_auto_retries,
                     retry_delay_seconds=rs.retry_delay_seconds,
                     dry_run=dry_run)
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
    # The accepted assertion was emitted by the test-designer; the
    # runner parses it out of the result text. For dry-run / chunk that
    # was loaded via chunks_file, the assertion is already in
    # chunk.accepted_assertion and the renderer substituted it in the
    # prompt.
    return {"record": rr, "result_text": _read_envelope_result_text(rr.envelope_path)}


def invoke_executor(chunk: ChunkState, rs: RunState, *,
                    evidence_output_dir: str,
                    rendered_prompt_path: str,
                    envelope_path: str,
                    dry_run: bool = False) -> dict:
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
    )
    rr = invoke_droid(Role.EXECUTOR, options=options,
                     envelope_path=envelope_path,
                     stderr_path=os.path.join(evidence_output_dir, "stderr-executor.log"),
                     max_retries=rs.max_auto_retries,
                     retry_delay_seconds=rs.retry_delay_seconds,
                     dry_run=dry_run)
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
    return {"record": rr, "result_text": _read_envelope_result_text(rr.envelope_path)}


def run_validators(chunk: ChunkState, rs: RunState, *,
                   evidence_output_dir: str,
                   dry_run: bool = False) -> BackendResult:
    """Run the cross-family validator panel via LocalBackend.

    Returns a ``BackendResult`` with ``gate`` and ``reason`` already set.
    The orchestrator propagates gate decisions into chunk.gate_decision
    and decides retry-via-executor or move-on.
    """
    backend = LocalBackend(dry_run=dry_run)
    validators_csv = [f"{v.pinned_model_id}:{v.pinned_provider}:{v.pinned_family}:{v.pinned_model_id}"
                      for v in rs.validators]
    prompt_template = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "prompts", "validator.md"
    )
    # Per §17.5 — validators get ``Read,Glob,Grep,LS`` in bundle mode.
    # ``Execute`` is NOT in the allowlist (KI-2 preventive fix).
    res = backend.validate(
        chunk={
            "test_file": chunk.locked_test_files[0],
            "lock_file": chunk.lock_manifest_path,
            "review_output_dir": os.path.join(evidence_output_dir, "reviews"),
            "scope": chunk.scope,
        },
        evidence_bundle=chunk.evidence_bundle_path,
        framework_root=rs.framework_root,
        pilot_root=rs.pilot_root,
        pilot_python=rs.pilot_python,
        signing_key_env=rs.signing_key_env,
        validators=validators_csv,
        run_label=f"{rs.run_id}-{chunk.chunk_id}",
        prompt_template_path=prompt_template,
        enabled_tools="Read,Glob,Grep,LS",
        evidence_source="bundle",
        run_id=rs.run_id,
        phase=rs.run_id.split("-")[0] if "-" in rs.run_id else "phase-4.5",
        branch="factory/phase-4.5-loop-runner",
    )
    chunk.validator_run_ids = [
        v.get("label") or v.get("model") or "<unknown>"
        for v in res.validators
    ]
    return res


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

def render_test_designer_prompt(chunk: ChunkState, rs: RunState,
                               pilot_spec_text: str,
                               output_path: str) -> str:
    """Render the test_designer role prompt for this chunk."""
    return render_to_file(
        "test-designer",
        {
            "chunk_spec": _format_chunk_spec(chunk),
            "pilot_root": rs.pilot_root,
            "test_file_path": os.path.join(rs.pilot_root, chunk.locked_test_files[0]),
            "pytest_baseline_path": "",
            "sibling_tests_pattern": "",
        },
        output_path,
    )


def render_executor_prompt(chunk: ChunkState, rs: RunState,
                           output_path: str) -> str:
    """Render the executor role prompt for this chunk."""
    return render_to_file(
        "executor",
        {
            "chunk_spec": _format_chunk_spec(chunk),
            "pilot_root": rs.pilot_root,
            "test_file_path": os.path.join(rs.pilot_root, chunk.locked_test_files[0]),
            "commands": "\n".join(chunk.commands),
        },
        output_path,
    )


def _format_chunk_spec(chunk: ChunkState) -> str:
    lines = [
        f"CHUNK_ID: {chunk.chunk_id}",
        f"SCOPE: {chunk.scope}",
        "OBSERVABLE_CRITERIA:",
    ]
    for c in chunk.observable_criteria:
        lines.append(f"  - {c}")
    if chunk.allowed_files:
        lines.append(f"ALLOWED_FILES:")
        for f in chunk.allowed_files:
            lines.append(f"  - {f}")
    if chunk.locked_test_files:
        lines.append(f"LOCKED_TEST_FILES:")
        for f in chunk.locked_test_files:
            lines.append(f"  - {f}")
    if chunk.commands:
        lines.append(f"COMMANDS:")
        for c in chunk.commands:
            lines.append(f"  - {c}")
    if chunk.rollback:
        lines.append(f"ROLLBACK: {chunk.rollback}")
    return "\n".join(lines)
