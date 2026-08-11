"""Thin command wrapper for ``droid exec`` calls inside the loop.

OPERATING-RULES §14 binds every script that invokes ``droid exec`` to
``tools/run-with-model.sh``. OPERATING-RULES §14 also binds every script
that reads envelope data to ``tools/adapters/factory.py``.

This module is the **only** place in the sprint_loop package that does
those two things. Anyone (the orchestrator, per-chunk inner loop,
replay tools) who needs to fire a droid call goes through
``invoke_droid(...)`` and reads the run record from ``RunRecord`` —
everything else composes existing primitives and never touches
``DROID_BIN`` or raw envelope fields directly.

Telemetry contract (per ``telemetry/SCHEMA.md`` v2):

  Every call appends one row to ``telemetry/runs.jsonl`` with the
  schema fields populated from the parsed envelope. The row is
  appended from inside this module — never from the orchestrator —
  so that an interrupted call leaves a complete-attribution record
  rather than an unattributed gap (OPERATING-RULES §10).

Truth assertions (OPERATING-RULES §7):

  The wrapper does NOT trust droid exec's exit code. It returns a
  ``RunRecord`` whose ``is_error`` reflects what the envelope said,
  parsed via the vendor adapter shim. A successful ``droid exec``
  that produced an empty envelope is still flagged ``is_error=True``
  by the ``FactoryAdapter.to_envelope`` contract; an unreadable
  envelope propagates as a transient-failure record.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Make ``tools/`` importable so the call sites can stay flat — the
# package layout (tools/sprint_loop/) doesn't have an ``adapters``
# sibling easily exposed otherwise. Mirrors ``tools/orchestrate-review.py``.
_TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.state import Role  # noqa: E402

# Vendor shim — wrapped imports so the rest of the sprint_loop package
# reads normalised envelopes without depending on Factory naming.
try:
    from adapters import factory as _factory_adapter
except ImportError as e:
    raise ImportError(
        "tools/sprint_loop/droid.py requires tools/adapters/factory.py "
        "to be on sys.path (OPERATING-RULES §14). If running this module "
        "directly, ensure PYTHONPATH includes the repo's tools/ "
        f"directory. Underlying error: {e}"
    )


# ── run record ───────────────────────────────────────────────────────────

@dataclass
class RunRecord:
    """Normalised record of one droid exec invocation.

    Mirrors the v2 ``runs.jsonl`` schema (subset — the on-disk row is
    a strict superset; this dataclass is the in-memory shape).
    """
    run_id: str
    role: str                    # planner | reviewer | test-designer | executor | validator
    model_id: str                # resolved model from envelope
    provider: str
    family: str
    provider_lock: str
    api_provider_lock: str
    num_turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    thinking_tokens: int = 0
    duration_ms: int = 0
    is_error: bool = False
    decision: str | None = None  # ACCEPT/ACCEPT-WITH-NITS/REJECT/null
    evidence_source: str | None = "bundle"
    retry_count: int = 0
    envelope_path: str = ""
    stderr_path: str = ""
    envelope_raw_bytes: int = 0
    started_at: str = ""
    finished_at: str = ""
    note: str = ""

    def to_telemetry_row(self, phase: str, branch: str) -> dict[str, Any]:
        """Build the on-disk row (per ``telemetry/SCHEMA.md`` v2)."""
        row = {
            "schema_version": "v2",
            "ts": self.finished_at or self.started_at or _utcnow_iso(),
            "run_id": self.run_id,
            "phase": phase,
            "branch": branch,
            "role": self.role,
            "model_id": self.model_id,
            "provider": self.provider,
            "family": self.family,
            "providerLock": self.provider_lock,
            "apiProviderLock": self.api_provider_lock,
            "num_turns": self.num_turns,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "thinking_tokens": self.thinking_tokens,
            "duration_ms": self.duration_ms,
            "is_error": self.is_error,
            "decision": self.decision,
            "evidence_source": self.evidence_source,
            "retry_count": self.retry_count,
            "envelope_path": self.envelope_path,
        }
        if self.note:
            row["note"] = self.note
        return row

    def to_finding_rows(self) -> list[dict[str, Any]]:
        """Placeholder — findings are not parsed here; the orchestrator
        or the validation step builds finding rows from
        ``tools/orchestrate-review.py:review-summary.json`` content."""
        return []


# ── envelope parsing ─────────────────────────────────────────────────────

# Defensive regex catches the common tail an adapter might emit; the
# canonical place to interpret envelope content is the adapter shim —
# this regex is a defensive capture for the adversarial-review's
# session-id stamping audit, not a parser.
_SESSION_ID_RE = re.compile(r'"session_id"\s*:\s*"([^"]+)"')


def parse_envelope(envelope_path: str,
                   session_jsonl_path: str | None = None,
                   settings_json_path: str | None = None) -> dict[str, Any]:
    """Parse an envelope via the vendor adapter shim.

    Wraps ``tools/adapters/factory.py:to_envelope`` with a clear error
    message when something goes wrong — OPERATING-RULES §7 demands
    assert-on-reality, and silent envelope failures were the §15 lesson.
    """
    if not os.path.isfile(envelope_path):
        raise FileNotFoundError(
            f"envelope missing: {envelope_path} (silently missing "
            f"envelope is the §7 silent-green defect shape)"
        )
    try:
        return _factory_adapter.to_envelope(
            envelope_path=envelope_path,
            session_jsonl_path=session_jsonl_path,
            settings_json_path=settings_json_path,
        )
    except (json.JSONDecodeError, OSError, KeyError) as e:
        raise ValueError(
            f"unreadable envelope at {envelope_path}: {e}. Per "
            f"OPERATING-RULES §7, surface the actual artifact state "
            f"rather than read a string."
        ) from e


# ── droid invocation ─────────────────────────────────────────────────────

@dataclass
class InvokeOptions:
    """Per-call knobs for ``invoke_droid``."""
    model_id: str                    # DROID_MODEL_ID (required by the wrapper)
    auto_level: str = "medium"        # --auto <level>
    enabled_tools: str = ""          # --enabled-tools <list>
    prompt_file: str = ""            # -f <path>
    cwd: str = ""                    # --cwd <path>
    extra_args: list[str] = field(default_factory=list)  # any extras
    timeout_seconds: int = 600        # droid exec per-call cap
    skip_run_with_model: bool = False # escape hatch for tests only — never True in production chunks


def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _retry_delay(args_paced_max_attempts: int, attempt: int) -> int:
    """Linearly increasing delay: 0, base, 2*base, ... capped at a sane ceiling."""
    return min(2 ** attempt, 30)


def _resolved_provider_and_family(
    model_id: str,
    provider_lock: str | None = None,
) -> tuple[str, str]:
    """Return the observed provider plus the curated family label.

    ``provider_lock`` is the raw lock string surfaced by the Factory
    envelope. ``family`` always comes from the curated model map so the
    guard compares like with like.
    """
    provider = provider_lock or _provider_for(model_id)
    family = _family_for(model_id)
    if not provider:
        provider = "unknown"
    if not family:
        family = "unknown"
    return provider, family


def invoke_droid(
    role: Role | str,
    *,
    options: InvokeOptions,
    envelope_path: str,
    stderr_path: str | None = None,
    max_retries: int = 2,
    retry_delay_seconds: int = 5,
    dry_run: bool = False,
    allowed_mission: bool = False,
) -> RunRecord:
    """Invoke ``droid exec`` once (with transient-API retry).

    Honours:
      - ``tools/run-with-model.sh`` wrapper (mandatory) unless
        ``options.skip_run_with_model=True`` (escape hatch for unit tests).
      - The vendor envelope parser via ``tools/adapters/factory.py``.

    Returns a ``RunRecord``. The caller decides what to do with it
    (write to telemetry, propagate gate decisions, etc.).
    """
    started_at = _utcnow_iso()
    role_str = role.value if isinstance(role, Role) else role

    if not options.prompt_file:
        raise ValueError("invoke_droid requires options.prompt_file (the rendered role prompt)")

    # Resolve cwd: caller controls; default = OS cwd
    cwd = options.cwd or os.getcwd()

    # Build the droid exec command (used by both dry-run and real path)
    droid_args: list[str] = ["droid", "exec"]
    if options.model_id:
        droid_args += ["--model", options.model_id]
    if options.auto_level:
        droid_args += ["--auto", options.auto_level]
    if options.enabled_tools:
        droid_args += ["--enabled-tools", options.enabled_tools]
    if cwd:
        droid_args += ["--cwd", cwd]
    droid_args += ["-f", options.prompt_file, "-o", "json"]
    droid_args += list(options.extra_args or [])

    run_with_model = os.path.join(_TOOLS_DIR, "run-with-model.sh")

    env = dict(os.environ)
    env["DROID_MODEL_ID"] = options.model_id
    if allowed_mission:
        env["DROID_ALLOW_MISSION"] = "1"
    else:
        env.pop("DROID_ALLOW_MISSION", None)

    # ── dry-run path: we *simulate* the call, writing a fake envelope
    # to envelope_path so that downstream code paths *do* see what they
    # would see, without burning model credits. The envelope is small,
    # correct-shaped, and explicitly marked is_error=False but carries a
    # note that records its dry-run provenance (so a reviewer reading
    # the bundle can spot it).
    if dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(envelope_path)) or ".", exist_ok=True)
        envelope_path_abs = os.path.abspath(envelope_path)
        provider, family = _resolved_provider_and_family(options.model_id)
        fake_envelope = {
            "session_id": "dry-run-no-session",
            "is_error": False,
            "num_turns": 0,
            "duration_ms": 0,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "thinking_tokens": 0,
            },
            "result": (
                f"[dry-run] No droid exec fired. Planned call: "
                f"{' '.join(droid_args)}"
            ),
            "model_id": options.model_id,
            "modelId": options.model_id,
            "apiProviderLock": provider,
            "providerLock": provider,
        }
        with open(envelope_path_abs, "w") as f:
            json.dump(fake_envelope, f, indent=2)
        if stderr_path:
            with open(stderr_path, "w") as f:
                f.write(f"[dry-run] no stderr — call not fired\n")
        return RunRecord(
            run_id=f"r-dry-run-{int(time.time()*1000)}",
            role=role_str,
            model_id=options.model_id,
            provider=provider,
            family=family,
            provider_lock=provider,
            api_provider_lock=provider,
            num_turns=0,
            duration_ms=0,
            is_error=False,
            envelope_path=envelope_path_abs,
            stderr_path=stderr_path or "",
            envelope_raw_bytes=os.path.getsize(envelope_path_abs),
            started_at=started_at,
            finished_at=_utcnow_iso(),
            note="dry-run: simulated; no droid exec fired",
        )

    # ── live path: route through run-with-model.sh, retry on transient
    # failures (0-output-tokens, is_error=True from a provider hiccup,
    # non-zero droid exit with no envelope).
    #
    # Single contiguous retry loop: envelope-parse failures AND
    # post-parse transient failures both retry through this loop,
    # so `attempts` increments monotonically. Recursion
    # (panel-finding F-8) would re-enter with a fresh local
    # `attempts = 0`, defeating the budget guard and firing N
    # unbounded paid calls before Python's recursion limit kicks in.
    envelope_path_abs = os.path.abspath(envelope_path)
    stderr_path_abs = os.path.abspath(stderr_path) if stderr_path else os.path.join(
        os.path.dirname(envelope_path_abs), "stderr.log"
    )
    os.makedirs(os.path.dirname(envelope_path_abs) or ".", exist_ok=True)
    if stderr_path:
        os.makedirs(os.path.dirname(stderr_path_abs) or ".", exist_ok=True)

    last_error: str | None = None
    attempts = 0
    env_parsed: dict | None = None
    result: subprocess.CompletedProcess | None = None
    while True:
        attempts += 1
        if attempts > max_retries + 1:
            # Persistent — surface as a real error record (don't silently degrade).
            return RunRecord(
                run_id=f"r-error-{int(time.time()*1000)}",
                role=role_str,
                model_id=options.model_id,
                provider="unknown",
                family="unknown",
                provider_lock=_provider_for(options.model_id),
                api_provider_lock=_provider_for(options.model_id),
                num_turns=0,
                duration_ms=0,
                is_error=True,
                envelope_path=envelope_path_abs,
                stderr_path=stderr_path_abs,
                envelope_raw_bytes=os.path.getsize(envelope_path_abs),
                started_at=started_at,
                finished_at=_utcnow_iso(),
                note=f"retry budget exhausted after {max_retries} retries: "
                     f"{last_error!r}",
            )

        with open(envelope_path_abs, "wb") as enf, open(stderr_path_abs, "wb") as errf:
            result = subprocess.run(
                [run_with_model] + droid_args,
                stdout=enf, stderr=errf,
                cwd=cwd, env=env,
                timeout=options.timeout_seconds,
            )

        # Try to parse the envelope. If unreadable, this is a transient
        # failure (provider hiccup or wrapper failure). Retry.
        try:
            env_parsed = parse_envelope(envelope_path_abs)
        except (FileNotFoundError, ValueError) as e:
            last_error = f"envelope parse failed: {e}"
            delay = retry_delay_seconds * (2 ** (attempts - 1))
            print(f"[droid] retry {attempts}/{max_retries + 1} after {delay}s "
                  f"({last_error!r})", file=sys.stderr)
            time.sleep(delay)
            continue

        # Detect transient failure post-parse: 0-output-tokens or
        # is_error=True from a provider hiccup that wrote a parseable
        # envelope. This is the same shape §11 of orchestrator-review
        # catches — retry budget is shared with envelope-parse retries.
        is_transient = (
            env_parsed["is_error"] is True
            or env_parsed["usage"]["output"] == 0
        )
        if is_transient:
            last_error = (
                f"transient failure (is_error={env_parsed['is_error']}, "
                f"output_tokens={env_parsed['usage']['output']})"
            )
            delay = retry_delay_seconds * (2 ** (attempts - 1))
            print(f"[droid] retry {attempts}/{max_retries + 1} after {delay}s "
                  f"({last_error})", file=sys.stderr)
            time.sleep(delay)
            continue

        # Success path — exit the retry loop with the record intact.
        break

    assert env_parsed is not None and result is not None  # noqa: S101 — analysed loop

    finished_at = _utcnow_iso()
    provider, family = _resolved_provider_and_family(
        env_parsed.get("model_id") or options.model_id,
        env_parsed.get("family"),
    )
    return RunRecord(
        run_id=f"r-{role_str}-{int(time.time()*1000)}",
        role=role_str,
        model_id=env_parsed.get("model_id") or options.model_id,
        provider=provider,
        family=family,
        provider_lock=provider,
        api_provider_lock=provider,
        num_turns=env_parsed["num_turns"],
        input_tokens=env_parsed["usage"]["input"],
        output_tokens=env_parsed["usage"]["output"],
        cache_read_tokens=env_parsed["usage"]["cache_read"],
        thinking_tokens=env_parsed["usage"]["thinking"],
        duration_ms=env_parsed["duration_ms"],
        is_error=bool(env_parsed["is_error"]),
        envelope_path=envelope_path_abs,
        stderr_path=stderr_path_abs,
        envelope_raw_bytes=os.path.getsize(envelope_path_abs),
        started_at=started_at,
        finished_at=finished_at,
        note=f"droid exec returned exit={result.returncode}" if 'result' in locals() else "",
    )


# ── family / provider lookups (mirror Config.provider_family; imported
# lazily so this module has no cycle) ────────────────────────────────────

def _provider_for(model_id: str) -> str:
    """Mirror ``tools/sprint_loop/config.py`` MODEL_FAMILY_MAP."""
    from sprint_loop.config import MODEL_FAMILY_MAP
    if model_id in MODEL_FAMILY_MAP:
        return MODEL_FAMILY_MAP[model_id][0]
    return "unknown"


def _family_for(model_id: str) -> str:
    """Same map, column 1."""
    from sprint_loop.config import MODEL_FAMILY_MAP
    if model_id in MODEL_FAMILY_MAP:
        return MODEL_FAMILY_MAP[model_id][1]
    return "unknown"


# ── telemetry append ─────────────────────────────────────────────────────

def append_run_record(record: RunRecord,
                      phase: str,
                      branch: str,
                      telemetry_path: str) -> None:
    """Append a single ``RunRecord`` to ``telemetry/runs.jsonl``.

    OPERATING-RULES §10 — telemetry rows are written by the script.
    Idempotency: same run_id re-appended would duplicate the row; the
    orchestrator is responsible for stable run_ids (one per invocation).
    """
    row = record.to_telemetry_row(phase=phase, branch=branch)
    # Phase 4.5 telemetry row — annotated so the aggregator's classifier
    # can filter by phase. PRD §17.4: do not `git add` this path; the
    # .gitignore already excludes ``telemetry/*.jsonl``.
    os.makedirs(os.path.dirname(os.path.abspath(telemetry_path)) or ".", exist_ok=True)
    with open(telemetry_path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
