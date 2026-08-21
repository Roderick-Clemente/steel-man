"""Validation backend abstraction (Track B per Phase 4.5).

The runner composes one ``ValidationBackend`` per chunk. Today: the
local backend (shells out to ``tools/orchestrate-review.py``). Tomorrow:
a CI backend that opens a PR, waits for the CI status check, and reads
the gate result. **Same interface, different backend.**

The CIBackend is intentionally **just the interface** — Phase 4.5
PRD §11 Track B exit is ``CIBackend stub (not implemented, just the
interface)``. Building a real CI backend is Backlog E (`ROADMAP-REVIEW.md`).
Until the CI back-end is wired up, the only way to fail CLOSED on CI mode
is the NotImplementedError the stub raises — which is exactly what the
operator needs (a clear, refusing message rather than a silent fallback).

LocalBackend is the *thin composition* of the project's existing review
harness — it does not reimplement the validation step.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Protocol

from sprint_loop.config import phase_path
from sprint_loop.state import GateDecision

# Make tools/ importable so the package can co-locate with adapters
# even though backends.py doesn't itself call the adapter.
_TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)


# ── common return shape ──────────────────────────────────────────────────


@dataclass
class BackendResult:
    """Normalised return from any ``ValidationBackend.validate(...)`` call.

    The local backend reads ``review-summary.json`` written by
    ``tools/orchestrate-review.py``; the CI backend (future) reads a
    status check. Both produce this shape so the chunk-loop logic does
    not need to branch on backend flavour.
    """

    gate: GateDecision
    reason: str
    summary_path: str = ""  # on-disk JSON for audit
    validators: list[dict[str, Any]] = field(default_factory=list)
    evidence_source: str = "bundle"
    raw: dict[str, Any] = field(default_factory=dict)


# ── interface ────────────────────────────────────────────────────────────


class ValidationBackend(Protocol):
    """Track B interface. Both backends satisfy this — the loop runner
    calls ``backend.validate(chunk, evidence_bundle)`` and gets back a
    ``BackendResult``. The chunk loop logic does not branch on backend
    type beyond passing backend-specific kwargs.
    """

    name: str

    def validate(
        self,
        *,
        chunk: dict[str, Any],
        evidence_bundle: str,
        framework_root: str,
        pilot_root: str,
        pilot_python: str,
        signing_key_env: str,
        validators: list[str],
        run_label: str,
        prompt_template_path: str,
        **extra: Any,
    ) -> BackendResult: ...


# ── LocalBackend ──────────────────────────────────────────────────────────


class LocalBackend:
    """Delegates to ``tools/orchestrate-review.py``.

    Composition: the local backend **does not reimplement** the review
    pipeline. It builds the per-call argv, shells out, parses the
    ``review-summary.json`` the orchestrator already writes, and returns
    a ``BackendResult``. Any bug fix or feature added to
    ``orchestrate-review.py`` benefits the runner with no further
    change here.
    """

    name = "local"

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def validate(
        self,
        *,
        chunk: dict[str, Any],
        evidence_bundle: str,
        framework_root: str,
        pilot_root: str,
        pilot_python: str,
        signing_key_env: str,
        validators: list[str],
        run_label: str,
        prompt_template_path: str,
        enabled_tools: str | None = None,
        auto_level: str = "high",
        evidence_source: str = "bundle",
        **extra: Any,
    ) -> BackendResult:
        # Check chunk keys first — the more specific programmer error.
        # If a chunk is missing test_file / lock_file, that's a
        # contract-level mistake; surfacing it is more useful than the
        # generic "orchestrator missing" message.
        test_file = chunk.get("test_file", "")
        lock_file = chunk.get("lock_file", "")
        # "evidence" is the phase_path KIND (expanded to EVIDENCE_ROOT), not a
        # literal directory name, so the remaining segments must be spelled
        # out. Substituting config.BUILD_EVIDENCE_REL — itself already rooted —
        # would double the evidence root. CHUNK-2-SPEC §2.2 mandates this
        # segment-preserving form; it reads as duplication and is not.
        review_output_dir = chunk.get("review_output_dir", "") or phase_path(
            framework_root,
            "evidence",
            "phase-4.5",
            "build-evidence",
            extra.get("run_id", run_label),
            "reviews",
        )
        if not test_file or not lock_file:
            return BackendResult(
                gate=GateDecision.STOP,
                reason=f"chunk missing test_file or lock_file (chunk keys: {sorted(chunk.keys())})",
                evidence_source=evidence_source,
            )

        # Dry-run short-circuits the real orchestrator call — we still
        # need a review_output_dir to dump the synthetic summary so the
        # orchestrator can read it, and we still need to return a
        # well-formed BackendResult. The orchestrator-existence check
        # is skipped on dry-run by design (the test fixture may use a
        # path that has no orchestrator).
        if self.dry_run:
            summary_path = os.path.join(review_output_dir, "review-summary.json")
            os.makedirs(review_output_dir, exist_ok=True)
            summary = {
                "ts": _utcnow_iso(),
                "branch": extra.get("branch", ""),
                "evidence_source": evidence_source,
                "run_label": run_label,
                "validators": [
                    {
                        "label": v.split(":")[0],
                        "model": v.split(":")[0],
                        "family": "dry-run",
                        "verdict": "ACCEPT",
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "retry_count": 0,
                    }
                    for v in validators
                ],
                "gate": "ACCEPT",
            }
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)
            return BackendResult(
                gate=GateDecision.ACCEPT,
                reason="dry-run: simulated ACCEPT for chunk validation",
                summary_path=summary_path,
                validators=summary["validators"],
                evidence_source=evidence_source,
                raw=summary,
            )

        orchestrator = os.path.join(framework_root, "tools", "orchestrate-review.py")
        if not os.path.isfile(orchestrator):
            return BackendResult(
                gate=GateDecision.STOP,
                reason=f"orchestrate-review.py missing at {orchestrator}",
                evidence_source=evidence_source,
            )

        os.makedirs(review_output_dir, exist_ok=True)

        # Validators come in as a list of model_id[:provider:family:label]
        # entries; ``orchestrate-review.py`` parses commas. We pass them
        # as comma-joined.
        validators_arg = ",".join(validators)

        argv: list[str] = [
            pilot_python,
            orchestrator,
            "--framework-root",
            framework_root,
            "--pilot-root",
            pilot_root,
            "--pilot-python",
            pilot_python,
            "--test-file",
            test_file,
            "--lock-file",
            lock_file,
            "--prompt-file",
            prompt_template_path,
            "--review-output-dir",
            review_output_dir,
            "--validators",
            validators_arg,
            "--evidence-output",
            evidence_bundle,
            "--auto-level",
            auto_level,
            "--max-retries",
            str(extra.get("max_auto_retries", 2)),
            "--retry-delay",
            str(extra.get("retry_delay_seconds", 5)),
            "--phase",
            extra.get("phase", "phase-4.5"),
            "--branch",
            extra.get("branch", "factory/phase-4.5-loop-runner"),
            "--evidence-source",
            evidence_source,
            "--run-label",
            run_label,
        ]
        # KI-2 fix: bundle-mode validators get no Execute tool (Track B + Track C
        # both rely on this). The runner passes --enabled-tools explicitly
        # when needed; otherwise the orchestrator's bundle-mode default
        # (Read,Glob,Grep,LS) applies.
        if enabled_tools:
            argv += ["--enabled-tools", enabled_tools]
        elif evidence_source == "bundle":
            argv += ["--treatment"]

        # Dry-run short-circuit lives BEFORE the signing-key guard:
        # in dry-run there is no real evidence flow, so the key is
        # not relevant — short-circuit returns a simulated ACCEPT so
        # the rest of the runner wires through. (Live runs hit the
        # signing-key guard below.) The dry-run path was relocated
        # here from the original three duplicate blocks at :141 / :216
        # / :244 — panel-finding F-9.
        if self.dry_run:
            summary_path = os.path.join(review_output_dir, "review-summary.json")
            os.makedirs(review_output_dir, exist_ok=True)
            summary = {
                "ts": _utcnow_iso(),
                "branch": extra.get("branch", ""),
                "evidence_source": evidence_source,
                "run_label": run_label,
                "validators": [
                    {
                        "label": v.split(":")[0],
                        "model": v.split(":")[0],
                        "family": "dry-run",
                        "verdict": "ACCEPT",
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "retry_count": 0,
                    }
                    for v in validators
                ],
                "gate": "ACCEPT",
            }
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)
            return BackendResult(
                gate=GateDecision.ACCEPT,
                reason="dry-run: simulated ACCEPT for chunk validation",
                summary_path=summary_path,
                validators=summary["validators"],
                evidence_source=evidence_source,
                raw=summary,
            )

        # Environment: evidence signing key. OPERATING-RULES §7:
        # do NOT fabricate a per-process key when the env var is unset
        # (panel-finding F-10) — that gives producer and verifier the
        # same secret, so the HMAC verifies whatever the process
        # produced and proves nothing cross-process. Refuse closed
        # instead, surfacing the operator's missing-config.
        env = dict(os.environ)
        signing_key = os.environ.get(signing_key_env, "")
        if not signing_key:
            return BackendResult(
                gate=GateDecision.STOP,
                reason=(
                    f"{signing_key_env} is unset. The evidence producer's "
                    f"HMAC would have no key to sign with, so the verifier "
                    f"would either (a) refuse closed (correct, but useless) "
                    f"or (b) share a fabricated per-process key with the "
                    f"producer, which §7 forbids. Set {signing_key_env} in "
                    f"the operator environment before launching the runner."
                ),
                evidence_source=evidence_source,
            )
        env["EVIDENCE_SIGNING_KEY"] = signing_key

        result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=900)
        # The orchestrator writes review-summary.json; read it.
        summary_path = os.path.join(review_output_dir, "review-summary.json")
        if not os.path.isfile(summary_path):
            return BackendResult(
                gate=GateDecision.STOP,
                reason=f"orchestrate-review.py exited {result.returncode} without writing "
                f"{summary_path}; stderr: {result.stderr[:300]!r}",
                evidence_source=evidence_source,
            )
        try:
            with open(summary_path) as f:
                summary = json.load(f)
        except json.JSONDecodeError as e:
            return BackendResult(
                gate=GateDecision.STOP,
                reason=f"review-summary.json at {summary_path} unreadable: {e}",
                evidence_source=evidence_source,
            )

        gate_text = (summary.get("gate") or "STOP").upper()
        try:
            gate = GateDecision(gate_text.replace("-", "_"))
        except ValueError:
            gate = GateDecision.STOP

        return BackendResult(
            gate=gate,
            reason=_reason_from_summary(summary, gate_text),
            summary_path=summary_path,
            validators=summary.get("validators", []),
            evidence_source=summary.get("evidence_source", evidence_source),
            raw=summary,
        )


def _reason_from_summary(summary: dict[str, Any], gate: str) -> str:
    """Pull a human-readable reason from the orchestrator's summary JSON."""
    n_v = len(summary.get("validators", []))
    if gate == "ACCEPT":
        nits = sum(
            1 for v in summary.get("validators", []) if v.get("verdict") == "ACCEPT-WITH-NITS"
        )
        return f"all {n_v} validator(s) ACCEPT" + (f" ({nits} with nits)" if nits else "")
    if gate == "REJECT":
        return f"{summary.get('note') or 'reject gate returned'}"
    return f"gate={gate} ({n_v} validator(s))"


# ── CIBackend (stub) ──────────────────────────────────────────────────────


class CIBackend:
    """Stub — Track B says the interface exists; do NOT implement until
    Backlog E (per ROADMAP-REVIEW.md §3 — Flavor b Harness-native is
    optional, only worth building if H-CI saving at scale justifies it).

    Any operator setting ``--validation-backend=ci`` today reaches the
    stub, which raises NotImplementedError with a clear, refusing
    message — pointing at the local backend as the working path. This
    prevents the silent-fallback defect shape (where the runner might
    paper over a missing CI backend with a local one).
    """

    name = "ci"

    def validate(
        self,
        *,
        chunk: dict[str, Any],
        evidence_bundle: str,
        framework_root: str,
        pilot_root: str,
        pilot_python: str,
        signing_key_env: str,
        validators: list[str],
        run_label: str,
        prompt_template_path: str,
        **extra: Any,
    ) -> BackendResult:
        raise NotImplementedError(
            "ValidationBackend=ci is currently a stub per Phase 4.5 PRD §11 "
            "Track B (do not build the CI side until Backlog E). Use "
            "--validation-backend=local to drive the existing "
            "tools/orchestrate-review.py pipeline. The CI backend will be "
            "wired up after the H-CI experiment confirms whether the "
            "evidence provider actually saves tokens on the review side."
        )


def build_backend(name: str, *, dry_run: bool = False) -> ValidationBackend:
    """Factory for the configured backend.

    Centralises the validation; the entry-point CLI just calls this.
    """
    n = (name or "local").lower()
    if n == "local":
        return LocalBackend(dry_run=dry_run)
    if n == "ci":
        return CIBackend()
    raise ValueError(f"unknown validation backend: {name!r} (expected 'local' or 'ci')")


# ── helpers ──────────────────────────────────────────────────────────────


def _utcnow_iso() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _random_key() -> str:
    """Random signing key for the dry-run / dev path; real production
    orchestrator runs set EVIDENCE_SIGNING_KEY explicitly."""
    return os.urandom(32).hex()
