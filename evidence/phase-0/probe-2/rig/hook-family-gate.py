#!/usr/bin/env python3
"""Pre-flight family gate.

The resolved model ID is absent from the droid exec result envelope, so the only
runtime source is the session transcript. This hook reads transcript_path on the
FIRST tool call, extracts message.modelId, and denies if the resolved model is not
in the expected family. Fails CLOSED: if the model cannot be determined, deny.
"""
import json, os, sys, datetime
from pathlib import Path
EXPECTED = os.environ.get("EXPECT_FAMILY", "claude")
LOG = Path("/tmp/probe-2/hooklog/family.jsonl")
try: p = json.loads(sys.stdin.read() or "{}")
except Exception:
    print("MODEL_FAMILY_UNVERIFIED: unparseable hook input", file=sys.stderr); sys.exit(2)
tpath = p.get("transcript_path") or ""
resolved, effort = None, None
try:
    with open(tpath) as f:
        for line in f:
            m = (json.loads(line) or {}).get("message") or {}
            if isinstance(m, dict) and m.get("modelId"):
                resolved, effort = m["modelId"], m.get("reasoningEffort")
except Exception as e:
    resolved = None
family = (resolved or "").split("-")[0] or None
ok = family == EXPECTED
rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
       "tool_name": p.get("tool_name"), "transcript_readable": bool(resolved),
       "resolved_model": resolved, "resolved_effort": effort,
       "expected_family": EXPECTED, "verdict": "allow" if ok else "deny"}
LOG.parent.mkdir(parents=True, exist_ok=True)
with LOG.open("a") as f: f.write(json.dumps(rec, sort_keys=True) + "\n")
if not ok:
    print(f"MODEL_FAMILY_VIOLATION: run resolved to {resolved!r} (effort {effort!r}), "
          f"expected family {EXPECTED!r}. Aborting before any tool acts.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
