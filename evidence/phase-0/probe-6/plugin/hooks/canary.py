#!/usr/bin/env python3
"""Plugin-scope canary. Logs to a fixed absolute path so the probe can read it
from outside. Never blocks."""
import json, sys, os, datetime
from pathlib import Path
LOG = Path("/tmp/probe-6/hooklog/plugin-canary.jsonl")
try: p = json.loads(sys.stdin.read() or "{}")
except Exception: p = {"parse":"failed"}
LOG.parent.mkdir(parents=True, exist_ok=True)
with LOG.open("a") as f:
    f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "tool_name": p.get("tool_name"), "hook_event": p.get("hook_event_name"),
        "plugin_root_env": os.environ.get("DROID_PLUGIN_ROOT"),
        "cwd": p.get("cwd")}, sort_keys=True) + "\n")
sys.exit(0)
