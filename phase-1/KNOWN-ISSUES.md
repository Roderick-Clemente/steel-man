# Phase 1 — KNOWN ISSUES

Tracked defects exposed by the Phase 1 slice, using the same schema as
`tools/KNOWN-ISSUES.md`.

All seven below were found the same way: by feeding crafted `PreToolUse` payloads
to the deployed `phase-1/hooks/locked-test-guard.py` and recording its exit code,
rather than by reading the source. Two rounds of cross-family review had already
audited this file and caught real defects (`MultiEdit` bypass, `python3 -c`
inline eval) — but both rounds reviewed the code *as written*. Nobody had probed
the guard *as deployed*. That gap is itself the finding, and it is the reason
`phase-1/probes/guard-bypass-probe.sh` is now committed and re-runnable.

Reproduce all of them:

```sh
bash phase-1/probes/guard-bypass-probe.sh
```

**Status summary:** F1, F2, F4 fixed. F3, F5 fixed. F6, F7 open by design decision
— see `phase-1/open-questions.md`.

---

## Issue F1: Missing locks directory fails OPEN

- **Status:** FIXED (this branch). Was: critical.
- **Surface:** `locked-test-guard.py` `load_locked_state()` / `main()`.
- **Filed:** 2026-08-11.

### Symptom

`load_locked_state()` returned an empty state when `LOCKS_DIR` was not a
directory. `main()` then read empty state as "no locks loaded means no policy to
enforce; allow." The docstring claimed fail-closed behaviour; the guard failed
closed on a *malformed* manifest and **open** on a *missing* one — the easier of
the two conditions to cause.

### Repro

```
{"tool_name":"Execute","cwd":"<pilot>","tool_input":{"command":"rm -rf <locks-dir>"}}
```
→ exit 0 (allow). Every subsequent call is then also allowed, regardless of target.

### Fix

A locks directory that is missing or unreadable now **denies**. The genuine
"no locks configured" case must opt out explicitly with
`ADVERSARIAL_SPRINT_LOCKS_REQUIRED=0`.

---

## Issue F2: Only the immediate parent of a protected path was guarded

- **Status:** FIXED (this branch). Was: critical.
- **Surface:** `locked-test-guard.py` `glob_resolves_to_locked()`.
- **Filed:** 2026-08-11.

### Symptom

The structural check compared a cleaned token against each protected path and
against `os.path.dirname(p)` — the *immediate* parent only. Lock manifests live
at `locks/test/<name>.lock.json`, so `locks/test` was protected but `locks`, one
level above, was not.

### Repro

`rm -rf phase-1/locks` and `mv phase-1/locks /tmp/stash` both returned exit 0.

### Fix

Every ancestor directory of each protected path, up to the pilot root, is now
treated as protected.

### Chain with F1 — full fake-GREEN

F1 and F2 compose into a defeat of the invariant without ever editing the test
through a guarded path:

1. `rm -rf phase-1/locks` — allowed (F2)
2. guard now allows every subsequent call (F1)
3. rewrite the locked test to a tautology — allowed
4. `python3 phase-1/scripts/lock.py <test> "<same assertion>"` — new manifest, new hash
5. `verify-green.py` compares against the *regenerated* manifest → **GREEN ACCEPTED**

`verify-green.py` cannot detect this: it trusts the `--lock-file` it is given and
re-checks `accepted_assertion` against source the same actor controls. The only
thing that catches the swap is a human diffing `RUN-LEDGER.md`'s recorded sha
against the manifest. **The audit trail caught it; the guard did not.**

---

## Issue F3: `find … -delete` classified as read-only

- **Status:** FIXED (this branch). Was: high.
- **Surface:** `locked-test-guard.py` `READ_ONLY_HEADS` / `WRITE_RE`.
- **Filed:** 2026-08-11.

### Symptom

`find` was a read-only command head, and `WRITE_RE` matched `>`, `sed -i`, `tee`,
`cp`, `mv`, `rm` — but not `-delete`. The segment short-circuited as read-only.

### Repro

`find test -name '*.py' -delete` → exit 0 (allow); the locked test is removed.

Deletion makes `verify-green.py` fail closed, so this is denial-of-service rather
than a fake-pass — but it directly falsifies "the executor cannot touch the test."

### Fix

`-delete`, `-exec`, `-execdir`, `truncate`, `dd`, `install`, `patch`, `ed` and
`xargs` added to `WRITE_RE`; `find` is no longer unconditionally read-only.

---

## Issue F4: `rm -rf *` from the pilot root

- **Status:** FIXED (this branch, same fix as F2). Was: high.
- **Surface:** `locked-test-guard.py` `glob_resolves_to_locked()`.
- **Filed:** 2026-08-11.

### Symptom

`*` globs to top-level entries (`<root>/test`), never to `<root>/test/<file>`, so
no candidate landed in `protected_abs`, and the structural branch compared against
the wrong directory level.

### Repro

`rm -rf *` executed from the pilot root → exit 0 (allow).

---

## Issue F5: Tool deny-list is enumeration-based

- **Status:** FIXED (this branch). Was: high.
- **Surface:** `locked-test-guard.py` `EDITOR_TOOLS` and the registration matcher.
- **Filed:** 2026-08-11.

### Symptom

`EDITOR_TOOLS` enumerated `Edit`, `Create`, `ApplyPatch`, `MultiEdit`. `Write` and
`NotebookEdit` both returned exit 0 against a locked test. `MultiEdit` itself was
only added after a round-2 reviewer caught its absence — the same miss class was
still open for every tool nobody had thought of yet.

### Repro

```
{"tool_name":"Write","cwd":"<pilot>","tool_input":{"file_path":"test/test_llms_txt_charset.py"}}
{"tool_name":"NotebookEdit","cwd":"<pilot>","tool_input":{"file_path":"test/test_llms_txt_charset.py"}}
```
Both → exit 0 (allow).

### Fix

Inverted to an **allow-list of known read-only tools**. Any tool name the guard
does not recognise is treated as a writer and denied. A deny-list keyed on tool
name loses to any runtime that adds or renames a write tool; an allow-list fails
closed on the unknown.

---

## Issue F6: GREEN can be manufactured from the collection surface

- **Status:** OPEN — design question, not a patch. See `open-questions.md`.
- **Surface:** the invariant itself, not the guard implementation.
- **Filed:** 2026-08-11.

### Symptom

The guard protects the locked test file and its manifest, and nothing else in the
pytest collection surface. An executor may freely write `test/conftest.py`. An
autouse fixture there can patch the subject under test so the locked test passes
with no real implementation change:

- test file hash unchanged ✅
- `accepted_assertion` still present in source ✅
- pytest exits 0 ✅
- → `verify-green.py` prints **GREEN ACCEPTED**

The same vector exists via `pytest.ini`, `sitecustomize.py`, `PYTHONPATH`, and
local plugins. `valid-red.py` greps for `conftest.py` in *failure output*, which
is not a defence.

This is the most interesting of the seven because it defeats the invariant
without ever violating it.

### Why it is not being patched here

Extending the guard to cover conftest, pytest.ini, sitecustomize and PYTHONPATH
is more enumeration — the same losing game as F3 and F5. The structural answer is
to stop trusting the working tree: have `verify-green.py` re-materialize the test
from content-addressed storage rather than reading the file on disk, which makes
hash equality tautological and demotes the hook from load-bearing to advisory.
That is a Phase 2 design change.

---

## Issue F7: Path resolution keys off the payload's `cwd`

- **Status:** OPEN — low severity, found by inspection, not probed.
- **Surface:** `locked-test-guard.py` `main()`.
- **Filed:** 2026-08-11.

### Symptom

`cwd` is taken from the `PreToolUse` payload and used to resolve the manifest's
repo-relative `file` entry. A call reporting a different cwd protects a path that
does not exist, while the real file sits unguarded.

### Fix direction

Lock manifests should record an absolute pilot root at lock time and resolve
against that, rather than against whatever cwd the live payload reports.
