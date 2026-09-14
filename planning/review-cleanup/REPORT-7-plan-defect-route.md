# PR 7 report: plan-defect route (REPLAN) and the KI-18 re-lock pin

Date: 2026-09-16

## Branch

- Branch: `factory/plan-defect-route`
- Base: `factory/runner-hygiene` (the final branch of the review-cleanup
  stack, as expected)
- Scope: local only. Nothing was pushed and no pull request was opened.
- Protected pre-existing untracked `*.orig` files and `evidence/`
  directories were not modified.

## Outcome

The plan-defect escape is complete: a chunk validator can now return
`REPLAN` and the runner routes it back through planning within a bounded
budget, while KI-18 is verified fixed and pinned.

## Task 1 — KI-18: verified already fixed, pinned

Trace result: the re-lock already happens. Commit `b4b687a`
(`feat(gate): route a test-directed rejection to the test-designer`)
re-enters `run_chunk_inner` for the redesign round, and
`run_chunk_inner`'s step 2 runs `lock_test` unconditionally on every
entry — so the manifest is regenerated from the redesigned test before
the next validation round reads `locked_test_sha`. Every path is
covered:

- the in-run bounce: REJECT_TEST → test-designer rewrite → lock →
  validation;
- a resume from a checkpoint written mid-bounce: chunk
  `rejection_kind="test"` round-trips the field-driven checkpoint
  restore, the resumed round re-fires the designer, and the lock step
  runs again before the validation round.

No new fix was needed, so none was layered on. Instead the behavior is
pinned by `tests/test_lock_relock_on_redesign.py`, which drives the
real `tools/phase-1-scripts/lock.py` through the Arm B sequence
(pre-locked 7-test suite → `REJECT_TEST` → designer writes a 20-test
suite → assert the manifest SHA equals the redesigned suite's SHA at
the next validation, with the lock invocations counted) plus the
resume-mid-bounce variant. A regression back to the stale manifest
fails both tests loudly instead of surfacing as a split validator
verdict. KI-18 is marked FIXED citing `b4b687a` as the closing commit
and this test as the pin.

## Task 2 — REPLAN route, done the existing way rather than a third way

`REPLAN` is reintroduced as a first-class validator verdict through the
same shared vocabulary the stack introduced, so the prompt block
(`validator.md`), the `orchestrate-review.py` parser, and the routing
set cannot drift again (`VALIDATOR_VERDICTS` drives all three). The
route follows the established patterns:

- **Fail-closed stop** — a `REPLAN` verdict never re-invokes the
  executor or the test-designer against a plan the panel judged
  defective; the chunk stops with `ChunkStatus.REPLAN`.
- **Evidence preserved** — the rejecting evidence is archived to
  `superseded-replan-round<N>`, mirroring the REJECT_TEST archive.
- **Feedback threaded** — the rejecting seats' own reasoning is carried
  on `rs.replan_feedback` and rendered into a dedicated
  `## Validator replan finding` section of the next round's planner
  prompt (the REJECT_TEST feedback-threading pattern).
- **Downstream invalidation** — on re-entry, plan → plan-review →
  reconcile runs again and the chunk list is re-derived from the chunks
  file; nothing derived from the rejected plan runs against the
  revised one. The main loop is restructured into an outer plan/chunks
  loop with `_plan_review_reconcile_loop` and
  `_chunking_and_chunk_loop` helpers so a chunk verdict can re-enter
  planning at all.
- **Bounded** — `--replan-budget` (default 1) caps replans per run,
  mirroring the test-design bounce bound. Budget and finding
  round-trip the checkpoint.
- **Distinct unattended exit code** — budget exhaustion escalates to
  `HUMAN_DECISION` with exit code 7, documented in `--help` alongside
  the existing codes 2 (plan-review exhaustion) and 6
  (SPEC_OR_TEST_BLOCKED).
- **Telemetry** — replan-round planner seat rows carry
  `phase_step="plan-replan"` (vocab + `telemetry/SCHEMA.md` +
  enum tripwire updated together); the `role="run"` row gains
  `replans_spent` / `replan_budget` so a run that died replanning is
  countable.

Pins: `tests/test_replan_routing.py` (classification, fail-closed
routing, budget and exhaustion, planner-prompt threading, evidence
archive, end-to-end re-chunking with `plan-replan` phase steps, exit
code 7, help text), plus the updated contract tests in
`tests/test_vocab_contract.py`, a named checkpoint-roundtrip sentinel,
and the telemetry tripwire.

## Known-issue updates

- **KI-18 → FIXED** — traced (closed by `b4b687a`, verified on every
  path including resume-mid-bounce) and pinned by
  `tests/test_lock_relock_on_redesign.py`.
- **KI-19 → FIXED (fast follow closed)** — the REPLAN route the entry
  called for is implemented; the entry now documents the final
  semantics and pins.
- **KI-14 — noted unaffected** — first-attempt invalid-RED never
  reaches the validation gate where `classify_rejection` runs, so the
  REPLAN changes neither fix nor worsen it. Status and fix direction
  remain as written.

## Validation

Required command:

```text
/usr/bin/python3 -m pytest -q
1 failed, 496 passed, 3 skipped
```

The sole failure was the permitted environmental failure
`tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds` (the
local git history contains two commits with the fixture subject, where
the test requires exactly one). The 3 skips are the pre-existing
`tests/test_layout_paths.py` overrides.

Confirmation with only that test deselected:

```text
/usr/bin/python3 -m pytest -q \
  --deselect tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds
496 passed, 3 skipped, 1 deselected
```

## Blockers and deferrals

- Blockers: none.
- Deferrals: none requested or encountered.
