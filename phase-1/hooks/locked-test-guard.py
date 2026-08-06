#!/usr/bin/env python3
"""PreToolUse hook: block the executor from writing hash-locked test files AND
lock manifests.

This is the Phase 1 implementation of the reference guard's policy #3
(independent test authorship) extended to protect the lock manifest itself.
It reads the lock manifests written by phase-1/scripts/lock.py and denies
any tool call that would modify:

  - a locked test file, OR
  - a locked test's manifest (because the manifest is what `verify-green.py`
    reads to confirm hash-equality; rewriting it would defeat the backstop).

Registration (in the pilot repo's .factory/settings.json):

    {
      "hooks": {
        "preToolUse": [
          {
            "command": "<path-to-this-file>",
            "matcher": "Edit|Create|ApplyPatch|Execute"
          }
        ]
      }
    }

The hook exits 0 on allow, 2 on deny. The contract string `SPEC_OR_TEST_BLOCKED`
is delivered to stderr so the agent run can continue with the message
visible in the transcript.
"""
import glob
import json
import os
import re
import shlex
import sys


# Default: lock manifests live in the sibling `locks/` directory.
DEFAULT_LOCKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locks"
)
LOCKS_DIR = os.environ.get("ADVERSARIAL_SPRINT_LOCKS_DIR", DEFAULT_LOCKS_DIR)


# Tools whose `tool_input.file_path` is treated as a file-write request.
EDITOR_TOOLS = ("Edit", "Create", "ApplyPatch")

# Shell operators we split commands on before segment-level inspection.
# Splitting on `;`, `&`, `|`, and `\n` prevents the cheap bypass-chain
# `pytest test.py ; python3 -c "..."` from being treated as a single test run.
SHELL_SEPARATORS = re.compile(r"[;&|\n]")

# Command heads that count as read-only at the segment level. Each segment is
# checked independently; the segment must start with one of these AND contain
# no write operator further in the segment.
READ_ONLY_HEADS = (
    "ls", "grep", "rg", "head", "tail", "wc", "find",
    "pytest", "read", "cat",
    "python3", "python",
)

# Write operators used for the per-segment read-only check.
WRITE_RE = re.compile(
    r">>?"                              # redirection (write)
    r"|\bsed\s+[^;|&]*\s+-i\b"          # sed -i (in-place)
    r"|\btee\b|\bcp\b|\bmv\b|\brm\b"   # filesystem mutation
)


def load_locked_state() -> dict:
    """Return `{"tests": [...], "manifests": [...]}` from LOCKS_DIR.

    Fails closed: a malformed/unreadable lock manifest raises so the caller
    can deny all author-tool calls. The reference guard teaches fail-closed:
    we cannot tell which tests are protected without a readable manifest.
    """
    state = {"tests": [], "manifests": []}
    if not os.path.isdir(LOCKS_DIR):
        return state
    for root, _, files in os.walk(LOCKS_DIR):
        for name in files:
            if not name.endswith(".lock.json"):
                continue
            path = os.path.join(root, name)
            state["manifests"].append(path)
            with open(path) as f:
                manifest = json.load(f)
            file_entry = manifest.get("file", "")
            if file_entry:
                state["tests"].append(file_entry)
    return state


def normalize_path(path: str, cwd: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(cwd, path))


def shell_segments(command: str) -> list:
    """Split on shell separators. Empty/whitespace-only segments dropped."""
    return [seg for seg in SHELL_SEPARATORS.split(command) if seg.strip()]


def segment_is_read_only(segment: str) -> bool:
    """True iff the segment begins with a read-only head AND contains no write
    operator anywhere in the segment."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    if not tokens:
        return False
    head = tokens[0]
    if head not in READ_ONLY_HEADS:
        return False
    return not bool(WRITE_RE.search(segment))


def glob_resolves_to_locked(token: str, cwd: str, protected_abs: set) -> bool:
    """If `token` carries a glob, expand it relative to cwd and check whether
    any expansion lands on a protected path."""
    if "*" not in token and "?" not in token:
        return False
    base = cwd if not os.path.isabs(token) else "/"
    candidates = glob.glob(os.path.join(base, token))
    return any(os.path.normpath(c) in protected_abs for c in candidates)


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

    try:
        state = load_locked_state()
    except (json.JSONDecodeError, OSError) as e:
        # Fail closed per reference guard: cannot enforce without a readable
        # manifest. The hook denies author-tool calls and the executor surfaces
        # the block in its transcript.
        print(f"SPEC_OR_TEST_BLOCKED: lock manifest malformed/unreadable: {e}", file=sys.stderr)
        return 2

    if not state["tests"] and not state["manifests"]:
        # No locks loaded means no policy to enforce; allow.
        return 0

    locked_abs = {normalize_path(lp, cwd) for lp in state["tests"]}
    locked_manifest_abs = {normalize_path(mp, cwd) for mp in state["manifests"]}
    protected_abs = locked_abs | locked_manifest_abs

    # Editor tools carry the target path directly.
    if tool_name in EDITOR_TOOLS:
        file_path = tool_input.get("file_path", "")
        if file_path and normalize_path(file_path, cwd) in protected_abs:
            print(
                f"SPEC_OR_TEST_BLOCKED: {tool_name} is not allowed on locked test or manifest {file_path}",
                file=sys.stderr,
            )
            return 2

    # Execute commands: segment by segment. A non-read-only segment that
    # mentions any locked test path or manifest is denied. Glob-resolved tokens
    # resolve against protected_abs so `rm test/*.py` cannot sneak past by
    # substring-evading.
    if tool_name == "Execute":
        command = tool_input.get("command", "")
        if not command:
            return 0
        for locked in state["tests"] + state["manifests"]:
            basename = os.path.basename(locked)
            for segment in shell_segments(command):
                if locked not in segment and basename not in segment:
                    continue
                if segment_is_read_only(segment):
                    continue
                try:
                    tokens = shlex.split(segment)
                except ValueError:
                    tokens = segment.split()
                for tok in tokens:
                    if glob_resolves_to_locked(tok, cwd, protected_abs):
                        print(
                            f"SPEC_OR_TEST_BLOCKED: Execute command globs locked path: {segment}",
                            file=sys.stderr,
                        )
                        return 2
                print(
                    f"SPEC_OR_TEST_BLOCKED: Execute command touches locked test or manifest {locked}: {segment}",
                    file=sys.stderr,
                )
                return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
