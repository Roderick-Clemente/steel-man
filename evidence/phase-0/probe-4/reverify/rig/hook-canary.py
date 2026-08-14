#!/usr/bin/env python3
"""Log every PreToolUse invocation. Never blocks. Proves whether hooks fire at all."""
import json, sys, os, datetime
raw = sys.stdin.read()
try: p = json.loads(raw or "{}")
except Exception: p = {"_unparseable": raw[:500]}
rec = {
    "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    "hook_event_name": p.get("hook_event_name"),
    "tool_name": p.get("tool_name"),
    "session_id": p.get("session_id"),
    "cwd": p.get("cwd"),
    "permission_mode": p.get("permission_mode"),
    "transcript_path": p.get("transcript_path"),
    "tool_input_keys": sorted((p.get("tool_input") or {}).keys()),
    "file_path": (p.get("tool_input") or {}).get("file_path"),
}
with open("/tmp/probe-4/hooklog/canary.jsonl", "a") as f:
    f.write(json.dumps(rec, sort_keys=True) + "\n")
sys.exit(0)
