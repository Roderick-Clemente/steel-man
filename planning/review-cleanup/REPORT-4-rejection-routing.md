# PR 4 report: rejection routing and feedback

Date: 2026-09-13

## Branch

- Branch: `factory/rejection-routing-and-feedback`
- Base: `factory/red-structural-classification` at `b530f33`
- Scope: local only. Nothing was pushed and no pull request was opened.
- Protected pre-existing untracked `*.orig` files and `evidence/` directories
  were not modified.

## Outcome

The branch now routes test-directed rejections back to the test designer,
threads regression evidence consistently, feeds validator findings into
implementation retries, and stops distinctly on a genuine
`RESULT: SPEC_OR_TEST_BLOCKED`.

The review findings in the operator prompt were addressed as follows:

1. Implementation retries now treat the rejected implementation's GREEN
   locked test as their expected starting state. They verify that GREEN state,
   run the executor in verify-and-harden mode, and include the rejecting
   validator's finding. A live-path test stubs only the droid-backed seats and
   runs real lock, RED, GREEN, evidence, prompt, and retry paths.
2. `tools/sprint_loop/vocab.py` is the shared vocabulary for plan and chunk
   verdicts, executor result signals, and per-seat `phase_step` values.
3. Executor blocked-signal parsing considers only the last tagged `RESULT:`
   line. Narration and bare `SPEC_OR_TEST_BLOCKED` text do not block a chunk,
   and the executor prompt requires the full protocol literal.
4. Producer and consumer regression checks share one refusal function. An
   exit-0 suite with zero passed and only skipped tests now fails producer,
   validator-consumer, and orchestrator gates.
5. An explicit checkpoint test confirms `ChunkState.retry_count` and
   `ChunkState.rejection_feedback` survive write and restore.
6. `test-design-rerun` is documented in `telemetry/SCHEMA.md` and pinned in
   the telemetry enum tripwire.
7. Full-suite integration regressions introduced by the cherry-picked stack
   were fixed for legacy backend test doubles and older evidence argument
   objects.

The `tools/KNOWN-ISSUES.md` conflict was resolved by preserving KI-14,
KI-15, KI-16, and KI-17 in numeric order.

## REPLAN decision

**Removed.**

`VERDICT: REPLAN` was advertised by the chunk-validator prompt but had no
parser or safe runtime transition. Chunk validation occurs after plan
approval, reconciliation, chunking, and implementation. Routing back to the
planner correctly would also require invalidating or replacing chunk state
and repeating those gates. Treating the token as an executor retry or a human
pause would misrepresent that lifecycle. The unsupported promise was removed;
a future planner route must add the complete transition explicitly.

## Known-issue updates

- **KI-14:** partially fixed. The implementation-retry instance of expected
  GREEN at the RED gate is fixed. First-attempt invalid-RED seat
  classification remains open as a separate follow-up.
- **KI-16:** fixed and expanded to document the previously unreachable live
  retry path.
- **KI-19:** new and fixed. It records the unsupported `REPLAN` contract and
  the shared-vocabulary correction. KI-18 remains assigned to the adjacent
  experiment-doc stack.

## Commits

Implementation commits, oldest first:

1. `b4b687a feat(gate): route a test-directed rejection to the test-designer`
2. `9e5e553 fix(evidence): one regression command, threaded to the producer that counts`
3. `cc61014 feat(executor): feed the validator's finding back on an implementation retry`
4. `d3cbb97 docs: add phase-4.5 sprint attempt progression and per-seat cost data to RUN-LEDGER`
5. `dcb910c fix(runner): handle SPEC_OR_TEST_BLOCKED signal from the executor`
6. `a04ed46 fix(runner): reach implementation retry feedback (KI-16)`
7. `5b8abeb fix(protocol): remove unsupported replan verdict (KI-19)`
8. `cf02abe fix(runner): parse the final executor result`
9. `5758589 fix(evidence): refuse all-skipped regression suites`
10. `b13d75d test(checkpoint): preserve rejection retry state`
11. `4f6e1ae docs(telemetry): add test design rerun phase`
12. `96d6f9e fix(runner): preserve legacy integration contracts`

The final branch also contains the report commit for this file.

## Validation

Required command:

```text
/usr/bin/python3 -m pytest -q
473 passed, 3 skipped, 1 known environmental failure
```

The sole failure was the permitted
`tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds`: the local git
history contains two commits with the fixture subject, where the test requires
exactly one.

Confirmation with only that test deselected:

```text
/usr/bin/python3 -m pytest -q \
  --deselect tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds
473 passed, 3 skipped, 1 deselected
```

Pytest collection reported 477 tests total. Focused suites for every changed
path also passed before the full run.

## Blockers and deferrals

- Blockers: none.
- Deferral: KI-14's first-attempt invalid-RED seat classification remains
  open. It is separate from the implementation-retry dead path fixed here.
