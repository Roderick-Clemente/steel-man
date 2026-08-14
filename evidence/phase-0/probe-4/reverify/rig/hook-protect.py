#!/usr/bin/env python3
"""Block edits to a SHA-256 content-locked test file."""
import hashlib, json, os, sys, datetime
from pathlib import Path

LOCKED = Path("/tmp/probe-4/repo/tests/locked_test.py").resolve()
MANIFEST = Path("/tmp/probe-4/locked-test.sha256")
LOG = Path("/tmp/probe-4/hooklog/protect.jsonl")
MODE = os.environ.get("HOOK_MODE", "exit2")

raw = sys.stdin.read()
try: p = json.loads(raw or "{}")
except Exception as e:
    print(f"hook input is not JSON: {e}", file=sys.stderr); sys.exit(1)

ti = p.get("tool_input") or {}
cand = ti.get("file_path") or ti.get("path") or ti.get("target_file")
cand_r = None
if cand:
    try: cand_r = Path(cand).expanduser().resolve()
    except Exception: cand_r = None

expected = MANIFEST.read_text().strip()
actual = hashlib.sha256(LOCKED.read_bytes()).hexdigest() if LOCKED.exists() else None
hit = cand_r == LOCKED

with LOG.open("a") as f:
    f.write(json.dumps({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "mode": MODE, "tool_name": p.get("tool_name"), "candidate": str(cand_r),
        "locked": str(LOCKED), "matched_locked_file": hit,
        "hash_matches_manifest": actual == expected, "session_id": p.get("session_id"),
    }, sort_keys=True) + "\n")

if not hit:
    sys.exit(0)

reason = (f"SPEC_OR_TEST_BLOCKED: {LOCKED} is a locked test file "
          f"(SHA-256 pinned in locked-test.sha256). Tests are authored independently; "
          f"the executor may not modify them. Change src.py instead.")
if MODE == "json-deny":
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)
print(reason, file=sys.stderr)
sys.exit(2)
