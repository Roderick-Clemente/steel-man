#!/usr/bin/env python3
"""Rung 3 inner-session tool-call extractor.

Reads the inner droid session jsonl (where individual tool_use events
landed) and emits a digest of:
- num_turns (per envelope, taken from --output json)
- tokens (input/output)
- tool_use event count
- per-event: name, args (first 240 chars), is_error

The digests tools/rung3-tool-call-digest.json is the rung-3 evidence
that the run was real (not silent-green).

Usage:
    python3 tools/fixtures/rung3-extract-tool-calls.py
        --envelope build-evidence/rung3-droid-exec-output.json
        --out tools/fixtures/rung3-tool-call-digest.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def locate_inner_session_jsonl(session_id: str) -> Path | None:
    """Inner droid exec sessions live at
    ~/.factory/sessions/-<cwd-name-encoded>/<session_id>.jsonl.
    We discover the primary path by walking ~/.factory/sessions."""
    base = Path.home() / ".factory" / "sessions"
    if not base.exists():
        return None
    matches = []
    for p in base.rglob(f"{session_id}.jsonl"):
        matches.append(p)
    # Prefer a path that contains '-private-tmp' (a fresh-clone pattern);
    # otherwise any match works.
    if not matches:
        return None
    matches.sort(key=lambda p: (not str(p).startswith(str(base / "-private-tmp")), str(p)))
    return matches[0]


def extract(env_path: Path, out_path: Path) -> int:
    if not env_path.exists():
        print(f"FAIL: envelope missing: {env_path}", file=sys.stderr)
        return 2
    envelope = json.loads(env_path.read_text())

    session_id = envelope.get("session_id")
    if not session_id:
        print("FAIL: envelope has no session_id", file=sys.stderr)
        return 2

    inner = locate_inner_session_jsonl(session_id)
    if inner is None:
        print(f"FAIL: inner session jsonl not located for {session_id}", file=sys.stderr)
        return 2

    print(f"inner session log: {inner}")
    events_tool_use: list[dict] = []
    tool_calls_total = 0
    with inner.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            msg = o.get("message")
            if isinstance(msg, dict):
                content = msg.get("content", [])
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_use":
                            events_tool_use.append(
                                {
                                    "name": c.get("name"),
                                    "args": _truncate(c.get("input", {}), 240),
                                }
                            )
                            tool_calls_total += 1

    usage = envelope.get("usage", {})
    digest = {
        "_meta": "Rung 3 evidence digest: numeric claims about a real droid exec run.",
        "envelope": {
            "session_id": session_id,
            "is_error": envelope.get("is_error"),
            "duration_ms": envelope.get("duration_ms"),
            "num_turns": envelope.get("num_turns"),
            "subtype": envelope.get("subtype"),
        },
        "usage_tokens": {
            "input": usage.get("input_tokens"),
            "output": usage.get("output_tokens"),
            "cache_read_input": usage.get("cache_read_input_tokens"),
            "cache_creation_input": usage.get("cache_creation_input_tokens"),
            "thinking": usage.get("thinking_tokens"),
        },
        "inner_session_log": str(inner),
        "tool_calls_total": tool_calls_total,
        "tool_use_events": events_tool_use,
        "verdict_text_first_240chars": envelope.get("result", "")[:240],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(digest, indent=2))
    print(f"wrote {out_path}")
    print(f"  num_turns         : {digest['envelope']['num_turns']}")
    print(f"  tool_calls_total  : {tool_calls_total}")
    print(f"  tokens input/out  : {usage.get('input_tokens')} / {usage.get('output_tokens')}")
    for i, ev in enumerate(events_tool_use, 1):
        print(f"  tool[{i}] name={ev['name']!r}  args={ev['args']!r}")
    return 0


def _truncate(o: object, n: int) -> object:
    """Recursively truncate long string values for readability."""
    if isinstance(o, str):
        return o if len(o) <= n else o[: n - 3] + "..."
    if isinstance(o, dict):
        return {k: _truncate(v, n) for k, v in o.items()}
    if isinstance(o, list):
        return [_truncate(v, n) for v in o]
    return o


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envelope", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    sys.exit(extract(args.envelope, args.out))
