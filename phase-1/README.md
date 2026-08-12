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

Executor is kept away from the test; we verify it didn't reach it.

Both halves are enforced, and both have known gaps — `KNOWN-ISSUES.md` lists
them with a re-runnable harness.

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

## Exit criteria (verbatim from PRD §11) — with status

Status is recorded per criterion rather than asserted collectively. Two are met,
one is unmet, one is met by weaker evidence than the criterion asks for.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Invalid RED cases are rejected. | ✅ **MET** (2026-08-12) | `valid-red.py` run explicitly against all four committed fixtures; every one rejected, `verifier_exit=1`, reasons recorded in `RUN-LEDGER.md`. |
| 2 | The same hashed test is observed failing for the intended assertion before any implementation writes. | ⛔ **UNVERIFIABLE — artifact lost** | The locked test `test/test_llms_txt_charset.py` **exists in no repository**: not in this repo's history, not in the pilot's, and the test-designer envelope records the filename but not the source. The lock manifest holds a SHA-256 of a file nobody has. "The *same* hashed test" cannot be observed failing again, now or ever. |
| 3 | The same hashed test is later observed passing for the same intended assertion after implementation writes. | ✅ MET | `verify-green.py` exit 0, recorded in `RUN-LEDGER.md`. |
| 4 | Hash unchanged across the transition; lock manifest preserved. | ✅ MET | `e78e46ff…d8b3` identical in the lock manifest and both ledger rows. |

Separately, the *enforcement* the slice depends on has seven recorded gaps —
`KNOWN-ISSUES.md`, five fixed and two open by design decision.

**Phase 1 is therefore not closed, and criterion 2 can no longer be closed as
written.** The artifact at the centre of this phase's evidence — the locked test
whose hash is the proof — was never committed. What survives is the hash, the
accepted assertion, and envelopes describing runs against a file that is gone.

This is the phase's own rule turned on itself: *if it isn't scripted it didn't
happen*, and an artifact that exists only as a hash is not reproducible evidence.
It is the same shape as the silent-green findings the project exists to catch —
the record looks complete, and the substance is absent.

Closing it honestly requires a **Phase 1.1**: author a fresh behavioural test for
the same doubled-charset defect, **commit the test file this time**, lock it, and
run the full RED → GREEN cycle with `valid-red.py` and `verify-green.py` exit
codes recorded. That is a new cycle producing new evidence — it does not
retroactively satisfy criterion 2, and this table should not be edited to claim
otherwise.
