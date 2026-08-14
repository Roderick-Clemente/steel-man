#!/usr/bin/env python3
"""Locked-test guard that also covers shell writes, and fails closed."""
import hashlib, json, os, re, sys, datetime
from pathlib import Path
LOCKED = Path("/tmp/probe-4/repo/tests/locked_test.py").resolve()
LOG = Path("/tmp/probe-4/hooklog/protect2.jsonl")
raw = sys.stdin.read()
try: p = json.loads(raw or "{}")
except Exception as e:
    print(f"SPEC_OR_TEST_BLOCKED: unparseable hook input, failing closed: {e}", file=sys.stderr)
    sys.exit(2)
tool = p.get("tool_name"); ti = p.get("tool_input") or {}
verdict, why = "allow", None
cand = ti.get("file_path") or ti.get("path") or ti.get("target_file")
if cand:
    try:
        if Path(cand).expanduser().resolve() == LOCKED: verdict, why = "deny", "path matches locked test"
    except Exception: verdict, why = "deny", "unresolvable path, failing closed"
cmd = ti.get("command")
if verdict == "allow" and cmd:
    # Any mention of the locked file in a shell command is denied. Coarse on purpose:
    # a guard that must out-parse a shell to stay correct is not a guard.
    if LOCKED.name in cmd or str(LOCKED) in cmd or "locked_test" in cmd:
        verdict, why = "deny", "shell command references the locked test path"
with LOG.open("a") as f:
    f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "tool_name": tool, "verdict": verdict, "why": why,
        "saw_file_path": bool(cand), "saw_command": bool(cmd),
        "session_id": p.get("session_id")}, sort_keys=True) + "\n")
if verdict == "deny":
    print(f"SPEC_OR_TEST_BLOCKED: {LOCKED} is a locked test file ({why}). "
          f"Tests are authored independently; the executor may not modify them.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
