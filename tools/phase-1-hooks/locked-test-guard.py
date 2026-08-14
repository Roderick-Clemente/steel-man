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
            "matcher": ".*"
          }
        ]
      }
    }

The matcher MUST be broad. It was previously an enumeration
(`Edit|Create|ApplyPatch|MultiEdit|Execute`), which meant a tool the list did
not name — `Write`, `NotebookEdit`, anything added by a future CLI release —
never reached this hook at all, so no amount of logic inside it could help.
Enumerating writers is the losing half of the problem; the hook now decides,
and it only needs to be given the chance. (KNOWN-ISSUES F5.)

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

# F1 fix. A missing or empty locks directory used to mean "no policy to enforce,
# allow" — which made `rm -rf <locks-dir>` a one-command disable switch for the
# whole guard. Absence of state is now treated as inability to enforce, i.e.
# deny. A genuine unlocked phase must say so explicitly.
LOCKS_REQUIRED = os.environ.get("ADVERSARIAL_SPRINT_LOCKS_REQUIRED", "1") != "0"


# F5 fix. This was an ENUMERATION of writer tools (Edit, Create, ApplyPatch,
# MultiEdit) — `Write` and `NotebookEdit` sailed straight through, and MultiEdit
# itself was only added after a reviewer noticed it missing. A deny-list keyed on
# tool name loses to every tool nobody thought of yet, so it is inverted: these
# are the tools known to be incapable of writing, and ANYTHING else is treated as
# a writer and checked.
READ_ONLY_TOOLS = (
    "Read", "Glob", "Grep", "LS", "List", "Search", "NotebookRead",
    "WebFetch", "WebSearch", "TodoWrite",
)

# Keys an unrecognised tool might carry its target path under.
PATH_KEYS = ("file_path", "path", "notebook_path", "target_file", "filename", "file")

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
#
# F3 fix. `find` stays a read-only head — `find test -name '*.py'` is legitimate
# review behaviour — but its destructive predicates now disqualify the read-only
# short-circuit, along with the other write verbs that are not spelled rm/mv/cp.
# `find test -name '*.py' -delete` previously classified as read-only and was
# allowed to remove the locked test.
WRITE_RE = re.compile(
    r">>?"                              # redirection (write)
    r"|\bsed\s+[^;|&]*\s+-i\b"          # sed -i (in-place)
    r"|\btee\b|\bcp\b|\bmv\b|\brm\b"   # filesystem mutation
    r"|-delete\b|-execdir\b|-exec\b"    # find's destructive predicates
    r"|\btruncate\b|\bdd\b|\binstall\b" # other write verbs
    r"|\bpatch\b|\bxargs\b|\bchmod\b"
    r"|\bln\b|\bmkdir\b|\btouch\b"
)


def load_locked_state() -> dict:
    """Return `{"tests": [...], "manifests": [...]}` from LOCKS_DIR.

    Fails closed: a malformed/unreadable lock manifest raises so the caller
    can deny all author-tool calls. The reference guard teaches fail-closed:
    we cannot tell which tests are protected without a readable manifest.
    """
    state = {"tests": [], "manifests": []}
    if not os.path.isdir(LOCKS_DIR):
        # F1: absence is not permission. The caller denies unless the operator
        # has explicitly declared this phase unlocked.
        raise FileNotFoundError(f"locks directory missing: {LOCKS_DIR}")
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


def ancestors_of(path: str):
    """Yield every ancestor directory of `path`, nearest first, up to the root."""
    current = os.path.dirname(path.rstrip("/")).rstrip("/")
    while current and current != os.path.dirname(current):
        yield current
        current = os.path.dirname(current).rstrip("/")


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
    if not cleaned:
        return False
    globby = "*" in token or "?" in token
    cdir = os.path.dirname(cleaned).rstrip("/")
    for p in protected_abs:
        # Cleaned token equals the protected path itself.
        if cleaned == p:
            return True
        # F2/F4: EVERY ancestor directory of a protected path is protected, not
        # just the immediate parent. Guarding only dirname(p) left two holes:
        # lock manifests live at locks/test/<f>.lock.json, so `rm -rf locks` —
        # one level up — was allowed and disabled the guard entirely (with F1);
        # and `rm -rf *` from the repo root cleaned to the root itself, which
        # matched no immediate parent either.
        for anc in ancestors_of(p):
            if cleaned == anc:
                return True
            # Glob-born structural check, generalised to any ancestor:
            # `rm test/*` cleans to `test/.py`, whose dirname is `test`.
            if globby and cdir == anc:
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
        if not LOCKS_REQUIRED:
            return 0
        print(f"SPEC_OR_TEST_BLOCKED: lock state unreadable ({e}). Refusing to "
              f"act as if nothing were protected. Set "
              f"ADVERSARIAL_SPRINT_LOCKS_REQUIRED=0 only if this phase is "
              f"genuinely unlocked.", file=sys.stderr)
        return 2

    if not state["tests"] and not state["manifests"]:
        # F1: an empty locks dir is the state left behind by deleting the
        # manifests, and is indistinguishable from "nothing is protected yet".
        # Treated as inability to enforce, not as permission.
        if not LOCKS_REQUIRED:
            return 0
        print("SPEC_OR_TEST_BLOCKED: locks directory contains no manifests. "
              "Set ADVERSARIAL_SPRINT_LOCKS_REQUIRED=0 if this phase is "
              "genuinely unlocked.", file=sys.stderr)
        return 2

    locked_abs = {normalize_path(lp, cwd) for lp in state["tests"]}
    locked_manifest_abs = {normalize_path(mp, cwd) for mp in state["manifests"]}
    protected_abs = locked_abs | locked_manifest_abs

    # F5: anything that is not Execute and not a known read-only tool is treated
    # as a writer, whatever it calls itself, and every plausible path key on it
    # is checked. Unknown tool names fail closed rather than sailing through.
    if tool_name != "Execute" and tool_name not in READ_ONLY_TOOLS:
        for key in PATH_KEYS:
            candidate = tool_input.get(key) or ""
            if not isinstance(candidate, str) or not candidate:
                continue
            if normalize_path(candidate, cwd) in protected_abs:
                print(
                    f"SPEC_OR_TEST_BLOCKED: {tool_name} is not allowed on locked "
                    f"test or manifest {candidate}",
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
