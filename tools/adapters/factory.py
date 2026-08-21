#!/usr/bin/env python3
"""Factory (Droid CLI) adapter.

The single vendor-shim describing how a Factory `droid exec
--output-format json` envelope plus its inner-session jsonl log
plus its inner-session settings.json get translated into the
vendor-neutral envelope shape consumed by the gates.

ONE public function: `to_envelope(*, envelope_path, session_jsonl_path=None,
settings_json_path=None) -> dict`. The gate code (`tools/fixtures/
rung{3,5,6}-gate.py`) calls it via this adapter; it does NOT read
the raw Factory paths or fields directly.

Why a seam here? Two reasons:

1. Locks the verifier envelope parsing into one place so a
   future vendor (Codex, Anthropic / Claude Code, Ollama, ...) can
   be plugged in by adding `tools/adapters/<vendor>.py` that produces
   the same normalised shape.
2. Keeps the gate LOGIC deterministic; gates assert on the
   normalised shape, not on Factory's field naming.

What this module MOVES into the seam:
  - the `~/.factory/sessions/-private-tmp-*` path search
  - the droid exec envelope's field name mapping
    (`usage.input_tokens` / `output_tokens` /
    `cache_read_input_tokens` / `thinking_tokens` → normalised
    `usage.{input, output, cache_read, thinking}`)
  - the inner-session jsonl's `tool_use` / `tool_result` walk
    (paired `tool_use_id` lookup)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# ---------- public function: to_envelope ----------


def to_envelope(
    *,
    envelope_path: str | Path,
    session_jsonl_path: str | Path | None = None,
    settings_json_path: str | Path | None = None,
) -> dict[str, Any]:
    """Translate one Factory run into the normalised envelope shape.

    Parameters
    ----------
    envelope_path
        Path to the raw `droid exec --output-format json` output
        file. The kind of file produced by every rung's audit-run
        envelope (e.g., `build-evidence/rung3-droid-exec-output.json`).
    session_jsonl_path
        Path to the inner-session jsonl log under
        `~/.factory/sessions/-private-tmp-rungN-fresh-clone-.../
        <session_id>.jsonl`. Optional; if absent, the returned
        `tool_calls` is empty.
    settings_json_path
        Path to the inner-session settings.json under
        `~/.factory/sessions/-private-tmp-rungN-fresh-clone-.../
        <session_id>.settings.json`. Optional; if absent, the
        returned `model_id`/`family` are `None`.

    Returns
    -------
    A dict matching the contract documented in
    `tools/adapters/README.md`:
      {
        "session_id": str,
        "is_error": bool,
        "num_turns": int,
        "duration_ms": int,
        "tool_calls": [{"name", "args", "is_error"}],
        "usage": {"input", "output", "cache_read", "thinking"},
        "model_id": str|None,
        "family": str|None,
        "result_text": str,
        "result_text_first_240chars": str,
      }
    """
    envelope = json.loads(Path(envelope_path).read_text())
    # Auto-locate sibling files if not explicitly given. This keeps
    # the vendor-specific path-search logic out of the gate code.
    if session_jsonl_path is None or settings_json_path is None:
        siblings = locate_sibling_files(envelope_path)
        if session_jsonl_path is None:
            session_jsonl_path = siblings["session_jsonl"]
        if settings_json_path is None:
            settings_json_path = siblings["settings_json"]
    usage_block = envelope.get("usage") or {}
    usage = {
        "input": int(usage_block.get("input_tokens") or 0),
        "output": int(usage_block.get("output_tokens") or 0),
        "cache_read": int(usage_block.get("cache_read_input_tokens") or 0),
        "thinking": int(usage_block.get("thinking_tokens") or 0),
    }
    result_text = envelope.get("result") or ""
    tool_calls = (
        _extract_tool_calls_from_session_jsonl(session_jsonl_path)
        if session_jsonl_path is not None
        else []
    )
    model_id: str | None = None
    family: str | None = None
    if settings_json_path is not None and Path(settings_json_path).exists():
        settings = json.loads(Path(settings_json_path).read_text())
        model_id, family = _resolve_family_from_settings(settings)
    return {
        "session_id": str(envelope.get("session_id") or ""),
        "is_error": bool(envelope.get("is_error")),
        "num_turns": int(envelope.get("num_turns") or 0),
        "duration_ms": int(envelope.get("duration_ms") or 0),
        "tool_calls": tool_calls,
        "usage": usage,
        "model_id": model_id,
        "family": family,
        "result_text": result_text,
        "result_text_first_240chars": result_text[:240],
    }


# ---------- the Factory-specific helpers MOVED INTO this seam ----------


def locate_sibling_files(envelope_path: str | Path) -> dict[str, Path | None]:
    """Locate sibling jsonl + settings.jsonl under ~/.factory/sessions/.

    Given an envelope that contains `session_id`, return
    matching files in `~/.factory/sessions/-private-tmp-rungN-…/`
    (the droid platform's runtime working dir). Returns a dict
    keyed by `session_jsonl`, `settings_json`, both `Path` or
    `None`.
    """
    envelope_path = Path(envelope_path)
    envelope = json.loads(envelope_path.read_text())
    session_id = envelope.get("session_id")
    base = Path.home() / ".factory" / "sessions"
    out = {"session_jsonl": None, "settings_json": None}
    if not session_id or not base.exists():
        return out
    jsonl_matches = list(base.rglob(f"{session_id}.jsonl"))
    if jsonl_matches:
        jsonl_matches.sort(
            key=lambda p: (
                not str(p).startswith(str(base / "-private-tmp")),
                str(p),
            )
        )
        out["session_jsonl"] = jsonl_matches[0]
    settings_matches = list(base.rglob(f"{session_id}.settings.json"))
    if settings_matches:
        settings_matches.sort(
            key=lambda p: (
                not str(p).startswith(str(base / "-private-tmp")),
                str(p),
            )
        )
        out["settings_json"] = settings_matches[0]
    return out


def _extract_tool_calls_from_session_jsonl(jsonl_path: str | Path) -> list[dict]:
    """Walk the inner-session jsonl and pair tool_use ↔ tool_result.

    Returns a list of `{"name", "args", "is_error"}` dicts, one per
    matched pair. Unmatched tool_use events are emitted with
    `is_error=None`. Unmatched tool_result events are ignored.
    """
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists():
        return []
    tool_uses: list[dict] = []
    tool_results_by_id: dict[str, bool] = {}
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception as exc:
                print(f"skip unparseable JSONL line: {exc}", file=sys.stderr)
                continue
            msg = o.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                ctype = c.get("type")
                if ctype == "tool_use":
                    tool_uses.append(
                        {
                            "name": c.get("name"),
                            "args": c.get("input") or {},
                            "tool_use_id": c.get("id"),
                        }
                    )
                elif ctype == "tool_result":
                    is_error = bool(c.get("is_error"))
                    tuid = c.get("tool_use_id")
                    if tuid is not None:
                        tool_results_by_id[tuid] = is_error
    out: list[dict] = []
    for u in tool_uses:
        is_error = tool_results_by_id.get(u["tool_use_id"])
        out.append(
            {
                "name": u["name"],
                "args": u["args"],
                "is_error": is_error,
            }
        )
    return out


def _resolve_family_from_settings(settings: dict) -> tuple[str | None, str | None]:
    """Return (model_id, family) from a session settings.json.

    Family resolution rule mirrors the rung-4 family-gate contract:
    primary key is `apiProviderLock`, secondary `providerLock`,
    final then `effectiveFactoryRouterModel.apiProvider`. The
    model_id is `effectiveFactoryRouterModel.modelId` if present,
    otherwise `modelId` (the surface `model` field at the seat).
    """
    model_id: str | None = (
        (settings.get("effectiveFactoryRouterModel") or {}).get("modelId")
        or settings.get("modelId")
        or settings.get("model")
    )
    candidate = (
        settings.get("apiProviderLock")
        or settings.get("providerLock")
        or (settings.get("effectiveFactoryRouterModel") or {}).get("apiProvider")
    )
    family: str | None = None
    if isinstance(candidate, str) and candidate.strip():
        family = candidate
    return model_id, family


# ---------- legacy hand-rolled digest emission (for backward compat) ----------


def to_digest_shape(envelope: dict[str, Any]) -> dict[str, Any]:
    """Re-emit a digest matching the historical `rung3-tool-call-digest.json`.

    The previously-hardcoded `rung3-tool-call-digest.json` file used
    key names `envelope.num_turns`, `usage_tokens.{input,output,
    cache_read_input,thinking}`, `tool_calls_total`,
    `tool_use_events[].{name,args}`, `verdict_text_first_240chars`.
    This helper re-emits the same shape from the normalised
    envelope so any tooling that still reads the digest directly
    keeps working without modification.
    """
    return {
        "envelope": {
            "session_id": envelope.get("session_id"),
            "is_error": envelope.get("is_error"),
            "duration_ms": envelope.get("duration_ms"),
            "num_turns": envelope.get("num_turns"),
            "subtype": "success" if not envelope.get("is_error") else "error",
        },
        "usage_tokens": {
            "input": envelope["usage"]["input"],
            "output": envelope["usage"]["output"],
            "cache_read_input": envelope["usage"]["cache_read"],
            "thinking": envelope["usage"]["thinking"],
        },
        "tool_calls_total": len(envelope["tool_calls"]),
        "tool_use_events": [
            {"name": tc.get("name"), "args": tc.get("args") or {}} for tc in envelope["tool_calls"]
        ],
        "verdict_text_first_240chars": envelope["result_text_first_240chars"],
        "session_id": envelope["session_id"],
    }


# ---------- minimal CLI for manual re-extraction ----------


def _cli(argv: list[str]) -> int:
    """Tiny shell-style driver: `python3 factory.py <envelope> [<session_jsonl>] [<settings>]`."""
    if not argv:
        print(
            "usage: factory.py <envelope_path> [<session_jsonl_path>] [<settings_json_path>]",
            file=sys.stderr,
        )
        return 2
    envelope_path = argv[0]
    session_jsonl_path = argv[1] if len(argv) > 1 else None
    settings_json_path = argv[2] if len(argv) > 2 else None
    # Auto-locate sibling files if not explicitly given.
    if session_jsonl_path is None or settings_json_path is None:
        siblings = locate_sibling_files(envelope_path)
        if session_jsonl_path is None:
            session_jsonl_path = siblings["session_jsonl"]
        if settings_json_path is None:
            settings_json_path = siblings["settings_json"]
    env = to_envelope(
        envelope_path=envelope_path,
        session_jsonl_path=session_jsonl_path,
        settings_json_path=settings_json_path,
    )
    print(json.dumps(env, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
