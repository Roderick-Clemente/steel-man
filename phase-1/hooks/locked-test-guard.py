#!/usr/bin/env python3
"""PreToolUse hook: block the executor from writing hash-locked test files.

This is the Phase 1 implementation of the reference guard's policy #3
(independent test authorship). It reads the lock manifests written by
phase-1/scripts/lock.py and denies any tool call that would modify a locked
test file.

The hook is registered in the pilot repo's .factory/settings.json (or via a
plugin) and receives a JSON payload on stdin with fields including:
  - tool_name
  - tool_input
  - cwd
  - transcript_path

Registration example (pilot repo .factory/settings.json):
    {
      "hooks": {
        "preToolUse": [
          {
            "command": "/Users/factory/work/adversarial-sprint-dev/phase-1/hooks/locked-test-guard.py",
            "matcher": "Edit|Create|ApplyPatch|Execute"
          }
        ]
      }
    }

The hook exits 0 on allow, 2 on deny, with a contract string on stderr that
is delivered to the agent so the run can continue and report SPEC_OR_TEST_BLOCKED.
"""
import json
import os
import re
import sys


# Default: look for lock manifests in the sibling locks/ directory.
DEFAULT_LOCKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locks"
)
LOCKS_DIR = os.environ.get("ADVERSARIAL_SPRINT_LOCKS_DIR", DEFAULT_LOCKS_DIR)


# Shell operators that can mutate a file. This is a conservative list for the
# Phase 1 slice; a fully general guard would need a shell parser, which the
# reference guard warns against. Here we fail closed: if a command mentions a
# locked test path and carries any of these operators, we deny.
SHELL_WRITE_OPERATORS = [
    r"\bsed\s+[^;|&]*\s+-i\b",
    r"\btee\b",
    r"\bcp\b",
    r"\bmv\b",
    r"\brm\b",
    r"\bcat\s+[^>|&]*>[>]?",
    r"\becho\s+[^>|&]*>[>]?",
    r"\bprintf\s+[^>|&]*>[>]?",
    r"[^>\s]>[>]?\s*\S+",
]


def load_locked_files() -> list:
    """Return the list of locked test file paths from manifest JSONs."""
    locked = []
    if not os.path.isdir(LOCKS_DIR):
        return locked
    for root, _, files in os.walk(LOCKS_DIR):
        for name in files:
            if not name.endswith(".lock.json"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path) as f:
                    manifest = json.load(f)
                file_entry = manifest.get("file", "")
                if file_entry:
                    locked.append(file_entry)
            except (json.JSONDecodeError, OSError):
                # A malformed lock manifest is a hook failure mode. We could
                # fail closed here, but for the Phase 1 slice we skip unreadable
                # manifests and rely on the lock tooling to validate them.
                continue
    return locked


def normalize_path(path: str, cwd: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(cwd, path))


def main() -> int:
    payload = sys.stdin.read()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print("SPEC_OR_TEST_BLOCKED: hook could not parse PreToolUse payload", file=sys.stderr)
        return 2

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}
    cwd = data.get("cwd", os.getcwd())

    locked_files = load_locked_files()
    if not locked_files:
        # No locks means no policy to enforce; allow. This keeps a guard with
        # no locks from blocking ordinary work.
        return 0

    locked_abs = {normalize_path(lp, cwd) for lp in locked_files}

    # Direct file-editing tools carry the target path in tool_input.file_path.
    if tool_name in ("Edit", "Create", "ApplyPatch"):
        file_path = tool_input.get("file_path", "")
        if file_path and normalize_path(file_path, cwd) in locked_abs:
            print(
                f"SPEC_OR_TEST_BLOCKED: {tool_name} is not allowed on locked test {file_path}",
                file=sys.stderr,
            )
            return 2

    # Execute commands are the bypass path. We deny if a command mentions a
    # locked test path and also contains a shell write operator. Without a real
    # shell parser we also deny any command that mentions a locked path if we
    # cannot clearly determine it is read-only, because the executor role must
    # not touch locked tests at all.
    if tool_name == "Execute":
        command = tool_input.get("command", "")
        if command:
            for locked in locked_files:
                if locked not in command and os.path.basename(locked) not in command:
                    continue

                # If the command is clearly a read-only inspection (ls, grep,
                # read, cat without redirection, pytest -v, etc.), allow it. The
                # executor should not need to read the test, but harmless reads
                # do not violate independent test authorship.
                read_only = re.search(
                    r"^(\s*(ls|grep|head|tail|wc|find|pytest|python3?\s+-m\s+pytest|read)\b|cat\b\s+[^>]*$)",
                    command,
                )
                if read_only and not re.search(r"[>]|\bsed\s+.*-i\b|\btee\b|\bcp\b|\bmv\b|\brm\b", command):
                    continue

                # Any mention of a locked test path in a non-read-only command
                # is blocked. This is the conservative, fail-closed interpretation
                # of policy #3 for this slice.
                print(
                    f"SPEC_OR_TEST_BLOCKED: Execute command touches locked test {locked}: {command}",
                    file=sys.stderr,
                )
                return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
