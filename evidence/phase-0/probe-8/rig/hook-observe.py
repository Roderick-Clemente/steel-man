#!/usr/bin/env python3
"""Observe-only PreToolUse hook: records the model's self-declared risk label
alongside the command it labelled. Never blocks - exit 0 always."""
import json, sys, datetime
from pathlib import Path
LOG = Path("/tmp/probe-8/hooklog/observe.jsonl")
try: p = json.loads(sys.stdin.read() or "{}")
except Exception: sys.exit(0)
ti = p.get("tool_input") or {}
with LOG.open("a") as f:
    f.write(json.dumps({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "tool_name": p.get("tool_name"),
        "permission_mode": p.get("permission_mode"),
        "declared_riskLevel": ti.get("riskLevel"),
        "declared_reason": (ti.get("riskLevelReason") or "")[:200],
        "command": (ti.get("command") or "")[:200],
        "file_path": ti.get("file_path"),
        "session_id": p.get("session_id"),
    }, sort_keys=True) + "\n")
sys.exit(0)
