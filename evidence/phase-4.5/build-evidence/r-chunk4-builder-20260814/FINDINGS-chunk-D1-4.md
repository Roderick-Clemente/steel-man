# FINDINGS — chunk-D1-4 (builder seat)

Findings raised by building chunk-D1-4 against
`planning/layout-refactor/CHUNK-4-SPEC.md`. Per §13/§6 these are problem
statements for the planner/referee, not spec edits — the builder seat does not
amend the spec.

## Summary of the build

Everything in §3.1–§3.4 that does not require editing the locked judge is
built, verified, and scripted:

| | |
|---|---|
| §3.1 CLI argument shapes | verified against live `--help` output, recorded below |
| §2.1/§3.2 valid-RED fixture | `tests/fixtures/phase-1/valid-red/{test_valid_red.py,subject.py}`, confirmed VALID by `valid-red.py` |
| §3.3 four direct invocations | all exit 0, scripted in `tools/d1-exit-check.sh`, captured in `d1-exit-check.out` |
| §3.4.1 `wiki-link-audit.py` | rc=0, 61 pages, all zero |
| §3.4.2 full suite | 237 collected, 234 passed, 0 failed, 3 skipped (see F-B on the "198" figure) |
| §2.2/§3.4.4/§4.4 Test 4 (path-existence) | **BLOCKED — see F-A**, not built |

## F-A — BLOCKED: §2.2's Test 4 requires editing a content-hash-locked file

`tests/test_layout_paths.py` is locked at
`tools/phase-1-locks/tests/test_layout_paths.py.lock.json`
(`sha256: cb00dfac5d925f8f643bce1b3fd7fe51fd2b01f3d0578487c5ca201aeedb1121`).
§2.2 asks the executor to "grow the Chunk-1 file" by adding a fourth test to
that exact file. Framework invariant #3 (re-affirmed at chunk-D1-1's finding 1
and chunk-D1-3's F8) is that the builder seat does not touch a locked judge —
not even to fix a stale comment. Adding a test is a larger edit than that, and
it would also invalidate the lock hash the planner already signed off on.

**This is not a new failure mode — it is the same one chunk-D1-1's finding 1
raised against CHUNK-1-SPEC §3.4, and chunks 2/2a/3 already carry the fix
in their own structure:** each of those three chunks added its *own* new
locked file — `tests/test_layout_paths_chunk2.py`,
`test_layout_paths_chunk2a.py`, `test_layout_paths_chunk3.py` — rather than
editing `tests/test_layout_paths.py` in place. Chunk-D1-4 is the first chunk
whose spec asks to grow the base file instead of following that established
pattern.

I did not author Test 4 anywhere, under any filename — that is the planner's
judgment call once §2.2 is amended, not mine to make unilaterally. **For the
planner:** either (a) add Test 4 to a new `tests/test_layout_paths_chunk4.py`,
lock it, and let me build against that lock, matching chunks 2/2a/3; or (b)
edit and re-lock `tests/test_layout_paths.py` directly in the planner/referee
seat. Either way, §4.4's "path-existence test passes" cannot close until one
of those lands.

## F-B — the "198 tests green" figure in §3.4.2/§4.2 is stale by three chunks

§3.4.2 and §4.2 both read "198 tests green (197 from chunks 1-3 + 1 new
path-existence test)". The live suite, measured just now on
`/private/tmp/asprint-venv/bin/python` via junit XML (not `-q` stdout — see
chunk-D1-3's F11 on why a second `-q` silently deletes the summary line):

```
collected=237 passed=234 failed=0 errors=0 skipped=3
```

197 was the count when v2/v3 of this spec was drafted, before chunk-D1-2a (23
tests) and the chunk-D1-3 nit-fix commits landed. `test_layout_paths.py` (3) +
`_chunk2.py` (3) + `_chunk2a.py` (23) + `_chunk3.py` (14) = 43 judge tests
alone, against a base suite that has also grown independently. The correct
exit check is "current baseline (237 collected, 234 passed, 3 skipped) + 1 new
Test 4", not a fixed absolute number — the same drift chunk-D1-3's nits
already found in a hand-typed statistic elsewhere (`PATH-REDIRECTS.md`'s
evidence-prefix count). I verified the number rather than hand-typing a
corrected one, per the same §7 discipline.

## F-C — §3.5 repeats the stale "origin" push target

§3.5 reads "Push to `origin/factory/layout-refactor`". This is the same
correction chunk-D1-1 already made as an operator decision: `origin`
(`Roderick-Clemente/adversarial-sprint`) does not carry this branch; the working
remote is `dev` (`Roderick-Clemente/adversarial-sprint-dev`). Re-flagging
because CHUNK-4-SPEC.md repeats the pre-correction text rather than the
corrected one — a future chunk spec drafted from an older template would
carry the same error forward.

## Verified CLI argument shapes (§3.1)

Read from live `--help` output on this build, not from memory or an earlier
chunk's notes:

```
lock.py         [-h] [--pilot-root PILOT_ROOT] [--locks-dir LOCKS_DIR] test_file accepted_assertion
valid-red.py    [-h] --pilot-root PILOT_ROOT --test-file TEST_FILE [--python PYTHON] --accepted-assertion ACCEPTED_ASSERTION [-o {text,json}]
verify-green.py [-h] --pilot-root PILOT_ROOT --lock-file LOCK_FILE --test-file TEST_FILE [--python PYTHON]
local_backend.py [-h] --pilot-root P --framework-root FR --test-file F --lock-file L --output O [--python PY] [--signing-key-env E] [--key-id K] [--security-scan] [--security-allowlist A] [--security-baseline B] [--full-suite]
```

## §3.3 real invocations — what each one actually demonstrated

Scripted end to end in `tools/d1-exit-check.sh`, captured in
`d1-exit-check.out`. Two things worth calling out beyond "all four exit 0":

- **`verify-green.py` was run twice on purpose.** Once against the fixture
  exactly as committed (pre-fix, `subject.py` still has the off-by-one), where
  it correctly returns rc=1 `GREEN REFUSED` — that refusal is the passing
  behaviour, not a failure. Once against a scratch copy with the documented
  one-line fix applied to `subject.py` only, using the **same lock file**,
  where it returns rc=0 `GREEN ACCEPTED` with the identical
  `locked_test_sha`. That pair is the real RED→GREEN transition §2.1 asks for,
  observed by the actual tool rather than asserted.
- **`local_backend.py` used `EVIDENCE_SIGNING_KEY=test-key`** with
  `--key-id d1-exit-check-test-key`, never a real signing key — the builder
  seat holds no key for chunk-close (§22).

## Fence self-check

`git status --porcelain` before this commit shows only the two new fixture
files, `tools/d1-exit-check.sh`, and this evidence directory. No edits to
`tests/test_layout_paths*.py`, `evidence/phase-4.5/tokens/`, `planning/**`, or
`evidence/LEDGER.md` beyond an append.
