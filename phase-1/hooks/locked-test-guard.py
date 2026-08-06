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
            "matcher": "Edit|Create|ApplyPatch|MultiEdit|Execute"
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
# MultiEdit is included because it's a multi-target variant of Edit that
# otherwise bypasses the PreToolUse matcher pattern. (Gemini round-2: major.)
EDITOR_TOOLS = ("Edit", "Create", "ApplyPatch", "MultiEdit")

# Shell operators we split commands on before segment-level inspection.
# Splitting on `;`, `&`, `|`, and `\n` prevents the cheap bypass-chain
# `pytest test.py ; python3 -c "..."` from being treated as a single test run.
SHELL_SEPARATORS = re.compile(r"[;&|\n]")

# Command heads that count as read-only at the segment level. Each segment is
# checked independently; the segment must start with one of these AND contain
# no write operator further in the segment.
#
# Note: python and python3 are deliberately NOT in this list. They are
# general-purpose interpreters that can rewrite arbitrary files — for example
# `python3 -c "open('test/test_foo.py','w').write('mutated')"`. Such a segment
# has no shell-write operator (`>`, `tee`, `cp`, `mv`, `rm`, `sed -i`) and so
# would otherwise be classified read-only and allowed through the syntax-based
# gate. The only acceptable entry point for running the locked test is
# `pytest <path>` directly. This was caught as a BLOCKING finding in the
# round-2 cross-family review (Grok, xAI).
READ_ONLY_HEADS = (
    "ls", "grep", "rg", "head", "tail", "wc", "find",
    "pytest", "read", "cat",
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
    """Decide whether `token` could resolve onto a protected path.

    Three checks:
      1. Hard glob expansion at `cwd` (or `/` for absolute paths).
      2. Structural check: project the token into cwd, strip glob chars,
         compare against protected paths. This catches `rm test/*.py`
         even when no real filesystem expansion is available.
      3. Parent-directory check: if the cleaned token equals the
         directory that contains a protected file, deny. This catches
         `rm -rf test/` even without glob chars.
    """
    if not token:
        return False
    base = cwd if not os.path.isabs(token) else "/"
    try:
        candidates = glob.glob(os.path.join(base, token))
    except (OSError, ValueError):
        candidates = []
    if any(os.path.normpath(c) in protected_abs for c in candidates):
        return True
    abs_token = token if os.path.isabs(token) else os.path.join(cwd, token)
    cleaned = re.sub(r"[*?]", "", abs_token).rstrip("/")
    cleaned = os.path.normpath(cleaned) if cleaned else ""
    for p in protected_abs:
        if not cleaned:
            continue
        # Cleaned token equals the protected path itself.
        if cleaned == p:
            return True
        pdir = os.path.dirname(p).rstrip("/")
        # Cleaned token equals the directory of a protected file
        # (`rm -rf test/` where test/ contains the lock).
        if cleaned == pdir:
            return True
        # Glob-born structural check: cleaned dirname equals the
        # protected file's directory AND the original token had glob
        # chars. (`rm test/*` cleans to `test/.py` -- dirname `test`
        # matches protected file's `test/` directory, so we deny.)
        if "*" in token or "?" in token:
            cdir = os.path.dirname(cleaned).rstrip("/")
            if cdir == pdir:
                return True
    return False


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

    # Execute commands: read-only short-circuit FIRST. A clear read-only
    # segment (`cat x`, `pytest x`, `head x`) is allowed even if it
    # mentions a locked path as a token. The auth-pipeline guarantee is
    # that read-only commands cannot mutate state, so the read of a
    # locked test by the executor (or a coordinated `pytest x -v`) is
    # legitimate review behaviour.
    #
    # Otherwise deny by:
    #   a. Token-literal-match (e.g. `rm test/test_foo.py`),
    #   b. Structural glob match (e.g. `rm test/*.py`, `rm -rf test/`,
    #      `python3 -c "open('locked','w').write(...)"`),
    #   c. Substring/basename match on the segment.
    # (Gemini round-2: blocking on the basal gating; Grok round-2:
    # blocking on python3 inline-eval.)
    if tool_name == "Execute":
        command = tool_input.get("command", "")
        if not command:
            return 0
        protected_literals = protected_abs | {os.path.basename(p) for p in protected_abs}
        for segment in shell_segments(command):
            # Read-only short-circuit FIRST.
            if segment_is_read_only(segment):
                continue

            # Tokenize with shlex; on parse error fall back to whitespace.
            try:
                tokens = shlex.split(segment)
            except ValueError:
                tokens = segment.split()

            for tok in tokens:
                if tok in protected_literals:
                    print(
                        f"SPEC_OR_TEST_BLOCKED: Execute token is locked path or basename: {tok} (segment: {segment})",
                        file=sys.stderr,
                    )
                    return 2
                if glob_resolves_to_locked(tok, cwd, protected_abs):
                    print(
                        f"SPEC_OR_TEST_BLOCKED: Execute token globs locked path: {segment}",
                        file=sys.stderr,
                    )
                    return 2

            # Substring backstop: catches quoted-then-evaluated commands
            # where shlex-flattened tokens don't surface the path (the
            # Grok+Gemini canonical case: `python3 -c "open('...','w')..."`).
            for locked in state["tests"] + state["manifests"]:
                basename = os.path.basename(locked)
                if locked in segment or basename in segment:
                    print(
                        f"SPEC_OR_TEST_BLOCKED: Execute segment touches locked test or manifest {locked}: {segment}",
                        file=sys.stderr,
                    )
                    return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
