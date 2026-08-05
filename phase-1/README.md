# Phase 1 — Test-evidence vertical slice

This directory holds the first vertical slice of the Adversarial Sprint
workflow: a locked behavioral test, an executor that cannot touch it, and a
GREEN verifier that checks both the test hash and the asserted reason.

## Pilot target

- Repo: `~/work/quantum-bank--llms-txt-pilot`
- Pre-fix commit: `2b70eae11969a5eabece97a81a80cf42853d7514`
- Behavior: the `/llms.txt` doubled-charset defect
  (`Content-Type: text/plain; charset=utf-8; charset=utf-8`).
- Same pin as `tools/fixtures/doubled-charset-pin.json`.

## Layout

| Path | Purpose |
|---|---|
| `phase-1/scripts/lock.py` | Compute SHA-256 of an accepted test and write the lock manifest |
| `phase-1/scripts/valid-red.py` | Run the locked test and classify whether the RED is valid |
| `phase-1/scripts/verify-green.py` | Recompute the hash and verify the test passes |
| `phase-1/hooks/locked-test-guard.py` | PreToolUse hook enforcing the executor cannot write locked tests |
| `phase-1/valid-red.md` | Classifier criteria and rejection families |
| `phase-1/locks/` | Lock manifests `{file, sha256, accepted_at, accepted_assertion}` |
| `phase-1/RUN-LEDGER.md` | Run records for the test designer and executor invocations |
| `phase-1/KNOWN-ISSUES.md` | Bugs found during the slice, using the same schema as `tools/KNOWN-ISSUES.md` |
| `phase-1/open-questions.md` | Open questions escalated before retrying |

## Two-line framing

Executor can't touch the test; we verify it didn't.

## How the slice runs

1. **Test designer** (separate droid invocation) reads the doubled-charset
   pin and writes a failing test in the pilot repo's `test/` directory.
2. **Lock** the accepted test: `python3 phase-1/scripts/lock.py <test-file>
   "<accepted-assertion>"`. This records the SHA-256 and the assertion that
   must fail.
3. **Classify RED**: `python3 phase-1/scripts/valid-red.py --pilot-root ...`.
   The test must fail for the intended reason.
4. **Executor** (separate droid invocation, different model family) is run with
   the PreToolUse hook registered. It may only write non-test files. It fixes
   `api/llms_txt.py` to use the bare `text/plain` mimetype so Werkzeug appends
   exactly one charset.
5. **Verify GREEN**: `python3 phase-1/scripts/verify-green.py ...` checks the
   test hash and that the test passes.
6. **Record** the run in `phase-1/RUN-LEDGER.md`.

## Exit criteria (verbatim from PRD §11)

- Invalid RED cases are rejected.
- The same hashed test is observed failing for the intended assertion before
  any implementation writes.
- The same hashed test is later observed passing for the same intended
  assertion after implementation writes.
- Hash unchanged across the transition; lock manifest preserved.
