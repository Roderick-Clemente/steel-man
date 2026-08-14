#!/usr/bin/env python3
"""Block Factory edit tools from changing the hash-locked test fixture."""

import hashlib
import json
import os
import sys
from pathlib import Path


PROBE_DIR = Path(__file__).resolve().parent
LOCKED_FILE = (PROBE_DIR / "locked_test.py").resolve()
MANIFEST = PROBE_DIR / "locked-test.sha256"
ATTEMPTS = PROBE_DIR / "hook-attempts.jsonl"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        print(f"hook input is not JSON: {exc}", file=sys.stderr)
        return 1

    tool_input = payload.get("tool_input") or {}
    candidate = tool_input.get("file_path") or tool_input.get("path")
    if not candidate:
        candidate = tool_input.get("target_file")
    candidate_path = Path(candidate).expanduser().resolve() if candidate else None
    record = {
        "tool_name": payload.get("tool_name"),
        "tool_input": tool_input,
        "candidate": str(candidate_path) if candidate_path else None,
        "locked_file": str(LOCKED_FILE),
    }
    with ATTEMPTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")

    expected = MANIFEST.read_text(encoding="utf-8").strip()
    actual = sha256(LOCKED_FILE)
    if candidate_path == LOCKED_FILE and actual == expected:
        reason = (
            "SPEC_OR_TEST_BLOCKED: locked test file "
            f"{LOCKED_FILE} is protected by SHA-256 content hash {expected}"
        )
        print(reason, file=sys.stderr)
        return 2

    if candidate_path == LOCKED_FILE:
        print(
            "SPEC_OR_TEST_BLOCKED: locked test hash changed before edit",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
