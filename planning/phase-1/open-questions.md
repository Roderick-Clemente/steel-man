# Phase 1 — Open questions

Questions escalated per the brief: two attempts on the same problem → write
the question down before retrying.

---

## Q1 — Is a syntactic command classifier the right primitive at all?

Raised 2026-08-11, from the F1–F7 probe results.

Five of the seven findings are the same shape: the guard enumerates dangerous
things, and something not enumerated slips past. `MultiEdit` was missing until a
reviewer caught it. Then `Write` and `NotebookEdit` were missing. Then `-delete`.
Then `truncate`. Each fix is correct and each one leaves the next unenumerated
verb open. `-exec`, `dd`, `patch`, `install` are patched now; `perl -i`, a shell
function, a Makefile target and a future CLI's new tool name are not.

The fixes in this branch make the guard meaningfully harder to defeat. They do
not change the fact that it is pattern-matching over an open-ended space.

**The structural alternative:** stop trusting the working tree at verification
time. If `verify-green.py` re-materialized the locked test from content-addressed
storage — the blob the lock manifest names — instead of reading the file on disk,
then hash equality becomes tautological, and *no* amount of tampering with the
on-disk file changes the verdict. The hook would drop from load-bearing to
advisory: useful for fast feedback to the executor, but not the thing the
invariant rests on.

The stronger version runs the executor as a separate OS user with the test
directory mounted read-only, which removes the question rather than answering it.

**Decision needed before Phase 2 commits to more guard surface.**

---

## Q2 — F6: the invariant is defined too narrowly

Raised 2026-08-11. See `KNOWN-ISSUES.md` F6.

The stated invariant is "the executor cannot write or modify the tests that judge
it." The probe shows GREEN can be manufactured *without touching the test*, by
writing `test/conftest.py` — an autouse fixture patches the subject under test,
the locked test passes, the hash is intact, and `verify-green.py` accepts.

So the invariant as written is satisfied while the property it exists to protect
is violated. Extending the guard to conftest, `pytest.ini`, `sitecustomize.py`
and `PYTHONPATH` is more enumeration (see Q1).

**The real question:** should the invariant be restated in terms of *outcome*
rather than *file*? Something closer to "GREEN must be attributable to changes in
the implementation under test, and to nothing else" — which is checkable by
diffing what the executor actually wrote against an allowed set, rather than by
defending a list of files.

That is a bigger change than a hook patch, and it is Phase 2's problem.

---

## Q3 — F7: what should a lock manifest resolve against?

Raised 2026-08-11. See `KNOWN-ISSUES.md` F7.

Manifests store a repo-relative path (`test/test_llms_txt_charset.py`) which the
guard resolves against the `cwd` reported in the live `PreToolUse` payload. A
call reporting a different cwd protects a path that does not exist.

Recording an absolute pilot root at lock time fixes the immediate issue but
hard-codes a machine path into an artifact meant to be portable and reviewable.
A content hash plus a repo-root marker is probably the right shape.

**Low severity; found by inspection, never observed in a live run.**
