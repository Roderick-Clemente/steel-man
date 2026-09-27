#!/usr/bin/env python3
"""Claude Code adapter.

The single vendor-shim describing how a Claude Code `claude -p
--output-format json` envelope plus its inner-session jsonl log
get translated into the vendor-neutral envelope shape consumed by
the gates.

ONE public function: `to_envelope(*, envelope_path, session_jsonl_path=None,
settings_json_path=None) -> dict`. Gate code calls it via this adapter;
it does NOT read the raw Claude Code paths or fields directly.

Verified against a real captured run (not synthesized): see
`tools/fixtures/claude-code-probe/{envelope,session}.jsonl`. Captured
via `claude -p "<prompt>" --output-format json --model
claude-haiku-4-5-20251001` on 2026-09-25.

Two structural differences from the Factory adapter, both because
Claude Code's on-disk shapes are simpler than Factory's:

1. No `settings.json` sibling. Claude Code has nothing analogous to
   Factory's per-session settings.json — the model id is already
   resolved and present directly in the session jsonl's assistant
   turns (`message.model`) and in the envelope's `modelUsage` keys.
   The `settings_json_path` parameter is accepted for interface
   parity with the shared adapter contract and is unused.
2. The session jsonl's tool_use/tool_result content blocks are
   already native Anthropic Messages API shape (Claude Code IS the
   Anthropic API), not a vendor-specific transform of it. The walk
   logic below is structurally identical to Factory's for that
   reason, not by coincidence.

What this module MOVES into the seam:
  - the `~/.claude/projects/<cwd-slug>/<session_id>.jsonl` path
    search (Claude Code slugs the working directory into the
    project folder name by replacing `/` with `-`)
  - the envelope's field name mapping (`usage.input_tokens` /
    `output_tokens` / `cache_read_input_tokens` -> normalised
    `usage.{input, output, cache_read}`)
  - the inner-session jsonl's `tool_use` / `tool_result` walk
    (paired `tool_use_id` lookup)

Known limitation (documented, not fixed here): `family` is
hardcoded to `"anthropic"` whenever a model_id resolves, since
Claude Code only ever runs Anthropic models. This inherits the
same documented shortcoming as the Factory adapter (README.md
"Family key" section) — two distinct Claude models collapse to the
same family. A future change should key family on resolved
model_id, same as noted there.

Not currently surfaced: `usage.thinking`. Claude Code's
`--output-format json` result does not expose a separate
thinking-token count in the top-level usage block (unlike
`input_tokens`/`output_tokens`/`cache_read_input_tokens`, which
are always present). Defaults to 0 per the contract's "if vendor
surfaces" carve-out.
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
    """Translate one Claude Code run into the normalised envelope shape.

    Parameters
    ----------
    envelope_path
        Path to the raw `claude -p --output-format json` output
        file for one run.
    session_jsonl_path
        Path to the inner-session jsonl log under
        `~/.claude/projects/<cwd-slug>/<session_id>.jsonl`.
        Optional; if absent, auto-located via `session_id` (a
        globally-unique UUID, so an rglob under `~/.claude/projects/`
        is unambiguous). If still not found, the returned
        `tool_calls` is empty.
    settings_json_path
        Unused for this vendor (see module docstring). Accepted
        only for interface parity with the shared adapter contract.

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

    if session_jsonl_path is None:
        session_jsonl_path = locate_session_jsonl(envelope.get("session_id"))

    usage_block = envelope.get("usage") or {}
    usage = {
        "input": int(usage_block.get("input_tokens") or 0),
        "output": int(usage_block.get("output_tokens") or 0),
        "cache_read": int(usage_block.get("cache_read_input_tokens") or 0),
        "thinking": 0,
    }

    result_text = envelope.get("result") or ""
    tool_calls = (
        _extract_tool_calls_from_session_jsonl(session_jsonl_path)
        if session_jsonl_path is not None
        else []
    )

    model_id = _resolve_model_id(envelope, session_jsonl_path)
    family = "anthropic" if model_id else None

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


# ---------- Claude-Code-specific helpers MOVED INTO this seam ----------


def locate_session_jsonl(session_id: str | None) -> Path | None:
    """Locate the session jsonl under ~/.claude/projects/.

    Claude Code stores one jsonl per session at
    `~/.claude/projects/<cwd-slug>/<session_id>.jsonl`, where
    `<cwd-slug>` is the working directory with `/` replaced by `-`.
    Since `session_id` is a UUID, an rglob for `<session_id>.jsonl`
    is unambiguous — unlike Factory's sessions dir, there's no
    private-tmp-vs-historical directory ordering to resolve.
    """
    base = Path.home() / ".claude" / "projects"
    if not session_id or not base.exists():
        return None
    matches = list(base.rglob(f"{session_id}.jsonl"))
    return matches[0] if matches else None


def _extract_tool_calls_from_session_jsonl(jsonl_path: str | Path) -> list[dict]:
    """Walk the inner-session jsonl and pair tool_use <-> tool_result.

    Returns a list of `{"name", "args", "is_error"}` dicts, one per
    matched pair. Unmatched tool_use events are emitted with
    `is_error=None`. Unmatched tool_result events are ignored.

    The content blocks here are native Anthropic Messages API shape
    (`type: "tool_use"` / `type: "tool_result"`), so this walk is
    structurally the same as Factory's — Claude Code doesn't
    transform the shape, it just persists it.
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
                    # Anthropic convention: `is_error` is omitted on
                    # success, present and true on failure. Absent
                    # -> False, matching Factory's bool(None)==False
                    # handling of the same convention.
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


def _resolve_model_id(envelope: dict, session_jsonl_path: str | Path | None) -> str | None:
    """Resolve the model id used for the run.

    Preferred source: the session jsonl's assistant turns
    (`message.model`), since that's the actually-invoked model per
    turn. Falls back to the envelope's `modelUsage` dict keys when
    the jsonl isn't available — reliable only when exactly one
    model was used in the run (a `--fallback-model` mid-session
    switch would show two keys; ambiguous, so treated as
    unresolvable in that case).
    """
    if session_jsonl_path is not None:
        path = Path(session_jsonl_path)
        if path.exists():
            with path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    msg = o.get("message")
                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                        model = msg.get("model")
                        if isinstance(model, str) and model:
                            return model
    model_usage = envelope.get("modelUsage") or {}
    if len(model_usage) == 1:
        return next(iter(model_usage))
    return None
