#!/usr/bin/env python3
"""Rung 5 gate — gate ONLY on machine-verifiable tool-call events.

Brief: "parse the JSON verdict, but gate ONLY on machine-verifiable
tool-call events (is_error=false + exit codes + required-command
coverage), NEVER transcript prose. A model can narrate `pwd` and emit
a verdict with num_turns>0 and prove nothing."

This script reads the inner droid session jsonl directly and verifies:
1. EVERY tool_use event has a matching tool_result event with
   is_error=False (per-tool failure must show as is_error, but the
   inner-session may have tool-execution errors we can't see in the
   envelope).
2. Required-command coverage: at least one tool_use event read or
   inspected api/llms_txt.py (validators MUST look at the source
   file, not just narrate from KB).
3. Optional: at least one tool_use exercised a *runtime tool* (i.e.,
   Execute / run-test / pytest etc.) — rung 5 logs this as
   'coverage' but does NOT mandate it (the model may legitimately
   Read the source and skip the runtime probe; that's rung 6's
   correctness concern).

Exits 0 on green; SystemExit(1) with --exit-loud on FAIL.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def locate_inner_session_jsonl(session_id: str) -> Path | None:
    base = Path.home() / ".factory" / "sessions"
    if not base.exists():
        return None
    matches = list(base.rglob(f"{session_id}.jsonl"))
    if not matches:
        return None
    matches.sort(key=lambda p: (not str(p).startswith(str(base / "-private-tmp")), str(p)))
    return matches[0]


def parse_events(jsonl_path: Path) -> dict:
    """Return counters and event lists for tool_use / tool_result pairs."""
    tool_uses: list[dict] = []
    tool_results: list[dict] = []
    file_paths: list[str] = []
    commands: list[str] = []
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
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
                    name = c.get("name")
                    inp = c.get("input", {}) or {}
                    fp = inp.get("file_path") or inp.get("path") or None
                    cmd = inp.get("command") or None
                    tool_uses.append(
                        {
                            "name": name,
                            "input": inp,
                            "file_path": fp,
                            "command": cmd,
                            "tool_use_id": c.get("id"),
                        }
                    )
                    if fp:
                        file_paths.append(fp)
                    if cmd:
                        commands.append(cmd)
                elif ctype == "tool_result":
                    tool_results.append(
                        {
                            "is_error": bool(c.get("is_error")),
                            "tool_use_id": c.get("tool_use_id"),
                            "content_first_240": str(c.get("content", ""))[:240],
                        }
                    )
    return {
        "tool_uses": tool_uses,
        "tool_results": tool_results,
        "file_paths": file_paths,
        "commands": commands,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On FAIL, raise SystemExit(1).",
    )
    parser.add_argument(
        "--envelope",
        required=True,
        type=Path,
        help="The rung-3 envelope (used to recover the session_id).",
    )
    args = parser.parse_args(argv)

    if not args.envelope.exists():
        print(f"FAIL: envelope missing: {args.envelope}", file=sys.stderr)
        return 2
    envelope = json.loads(args.envelope.read_text())
    session_id = envelope.get("session_id")
    if not session_id:
        print("FAIL: envelope has no session_id", file=sys.stderr)
        return 2
    inner = locate_inner_session_jsonl(session_id)
    if inner is None:
        print(f"FAIL: inner session jsonl not located for {session_id}", file=sys.stderr)
        return 2

    print(f"inner session log: {inner}")
    events = parse_events(inner)
    print(f"tool_uses   : {len(events['tool_uses'])}")
    print(f"tool_results: {len(events['tool_results'])}")
    for i, u in enumerate(events["tool_uses"], 1):
        print(f"  tool_use[{i}] name={u['name']!r}  file={u.get('file_path')!r}  cmd={u.get('command')!r}")
    for i, r in enumerate(events["tool_results"], 1):
        print(f"  tool_res[{i}] is_error={r['is_error']}  prefix={r['content_first_240']!r}")

    fails: list[str] = []
    # 1. Every tool_use must have a matching (by tool_use_id) tool_result.
    use_ids = {u["tool_use_id"] for u in events["tool_uses"]}
    matched = [r for r in events["tool_results"] if r["tool_use_id"] in use_ids]
    if len(matched) < len(events["tool_uses"]):
        extra = len(events["tool_uses"]) - len(matched)
        fails.append(
            f"{extra} tool_use events have no matching tool_result (assert: each call answered)",
        )
    # 2. Every matched tool_result must be is_error=False.
    for r in matched:
        if r["is_error"]:
            fails.append(
                f"tool_result is_error=True for use_id={r['tool_use_id']}: "
                f"{r['content_first_240']!r}"
            )
    # 3. Required-command coverage: at least one tool_use inspected
    #    api/llms_txt.py.
    saw_llms_txt_source_inspection = any(
        fp and fp.endswith("api/llms_txt.py")
        for fp in events["file_paths"]
    )
    if not saw_llms_txt_source_inspection:
        fails.append(
            "no Required-command coverage: validator did NOT read / inspect api/llms_txt.py. "
            f"file_paths seen: {events['file_paths']}"
        )

    if fails:
        print()
        print("RED — rung 5 gate failed:")
        for f in fails:
            print(f"  - {f}")
        if args.exit_loud:
            raise SystemExit(1)
        return 1

    print()
    print("GREEN — rung 5 gate. Tool calls present and clean; required source file inspected.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
