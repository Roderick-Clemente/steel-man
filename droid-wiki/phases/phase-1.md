# Phase 1 — Test-Evidence Vertical Slice

Phase 1 was the first vertical slice of the adversarial sprint workflow: a locked behavioral test, an executor that cannot touch it, and a verifier that checks both the test hash and the asserted reason. It proved the pipeline on one real defect in the QuantumBank pilot repo.

The pilot was `~/work/quantum-bank--llms-txt-pilot` at a pre-fix commit. The defect was the doubled-charset `Content-Type: text/plain; charset=utf-8; charset=utf-8` in the `/llms.txt` endpoint.

## Key source files

| File | Purpose |
|---|---|
| `/Users/factory/work/adversarial-sprint-dev/phase-1/README.md` | Slice brief and exit criteria |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/lock.py` | Compute SHA-256 of an accepted test and write the lock manifest |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/valid-red.py` | Run the locked test and classify whether the RED is valid |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/verify-green.py` | Recompute the hash and verify the test passes |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/hooks/locked-test-guard.py` | PreToolUse hook that blocks executor edits to locked tests |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/valid-red.md` | Classifier criteria and rejection families |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/RUN-LEDGER.md` | Run records for test designer and executor invocations |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/KNOWN-ISSUES.md` | Bugs found during the slice |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/locks/` | Lock manifests (`{file, sha256, accepted_at, accepted_assertion}`) |

## How the slice runs

1. A test designer reads the doubled-charset pin and writes a failing test in the pilot's `test/` directory.
2. Lock the accepted test: `python3 phase-1/scripts/lock.py <test-file> "<accepted-assertion>"`. This records the SHA-256 and the assertion that must fail.
3. Classify RED: `python3 phase-1/scripts/valid-red.py --pilot-root ...`. The test must fail for the intended behavioral reason, not an import or syntax error.
4. Run the executor with the PreToolUse hook registered. It may only write non-test files. It fixes `/Users/factory/work/quantum-bank--llms-txt-pilot/api/llms_txt.py` to use the bare `text/plain` mimetype so Werkzeug appends exactly one charset.
5. Verify GREEN: `python3 phase-1/scripts/verify-green.py ...` checks the test hash and that the test passes.
6. Record the run in `/Users/factory/work/adversarial-sprint-dev/phase-1/RUN-LEDGER.md`.

## The lock-and-verify contract

The lock manifest captures the exact bytes of the accepted test. The executor cannot change those bytes because the hook denies any `Edit` or `Execute` payload that targets a locked path. After the executor finishes, `/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/verify-green.py` recomputes the hash and confirms it matches the manifest, then runs the test and confirms it passes. The same test must have been observed failing for the intended assertion before implementation and passing after.

## What was learned

- The hook blocks edits effectively, but it must also watch `Execute` commands (shell redirections, `sed -i`, etc.).
- A valid-RED classifier is necessary because a test can fail for the wrong reason (import error, fixture problem) and still look like a RED.
- The same lock manifest format carries into later phases; Phase 3 reuses `/Users/factory/work/adversarial-sprint-dev/phase-1/locks/` as the canonical locks directory.

## Exit criteria

From the PRD, verbatim:

- Invalid RED cases are rejected.
- The same hashed test is observed failing for the intended assertion before any implementation writes.
- The same hashed test is later observed passing for the same intended assertion after implementation writes.
- Hash unchanged across the transition; lock manifest preserved.
