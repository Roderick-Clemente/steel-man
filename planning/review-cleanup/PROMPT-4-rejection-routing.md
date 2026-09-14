# Operator prompt — review-cleanup stack, PR 4 (flagship): rejection routing, retry feedback, blocked signal

Repo: /Users/factory/work/adversarial-sprint-dev (all work stays local; do NOT push, do NOT open a PR, do NOT touch untracked *.orig files or untracked evidence/ dirs).

Goal: PR 4 of a stacked split — the flagship: adversarial seat routing + retry feedback + blocked-signal handling, plus fixes for the most important review findings. Base: factory/red-structural-classification (must exist; stop and report if not).

## Steps

1. `git checkout -b factory/rejection-routing-and-feedback factory/red-structural-classification`
2. Cherry-pick in order: `a404ddf d80c924 cecd984 116b710 7009844` (REJECT_TEST routing; regression-command threading; impl-retry feedback; RUN-LEDGER data; SPEC_OR_TEST_BLOCKED handling)

   Cherry-pick conflict guidance: tools/KNOWN-ISSUES.md WILL conflict — the stack's PR 3 filed `## Issue KI-17: Warnings summary misclassified as a collection failure` in the same append region where a404ddf/d80c924/cecd984 file KI-14/KI-15/KI-16. Resolution: keep ALL entries; the cherry-picked entries keep their original ids (KI-14: invalid RED retries executor, KI-15, KI-16); the KI-17 warnings entry stays as PR 3 wrote it. Prefer numeric order in the file. Note: cherry-picked KI-14 ("an invalid RED still retries the executor") is closely related to your finding (a) below — after your fix, update the KI-14 entry status/text accordingly.
3. Fix these verified review findings, each as its own commit with tests:

   a. **[P1 — most important] The implementation-retry path is unreachable live.** A REJECT_IMPLEMENTATION only occurs after verify_green succeeded, so the locked test is GREEN at HEAD; the retry re-enters run_chunk_inner, validate_red fails with "Invalid RED: test passed", and the relaxation at tools/sprint-loop.py (~line 1732 at old head) is `if chunk.verify_mode or redesign_round:` — the impl-retry round is neither. Retries burn at the RED gate until HUMAN_DECISION and render_executor_prompt is never re-invoked with prior_implementation_rejection. Fix: extend the already-GREEN relaxation to the implementation-retry round (the rejected implementation being present and GREEN is the EXPECTED starting state for that round). Add an end-to-end test that drives a real REJECT_IMPL -> executor retry through validate_red with the real control flow (stub only the droid subprocess, matching the style of tests/test_reject_impl_feedback.py) and asserts the executor prompt on round 2 contains the validator's finding. Update the KI-16 entry in tools/KNOWN-ISSUES.md documenting the dead path and its fix.

   b. **[P1] VERDICT: REPLAN is unparseable.** prompts/validator.md offers `VERDICT: REPLAN` (~line 96) but orchestrate-review.py's verdict regex (~line 351) has no REPLAN token, so it parses as a stray prose word or UNKNOWN. Root-cause fix: create tools/sprint_loop/vocab.py as the single source of truth for verdict strings, executor RESULT signals, and phase_step values; import it in orchestrate-review.py (it loads modules dynamically — follow the existing pattern) and per_chunk.py (TEST_DIRECTED_VERDICTS); decide REPLAN's routing semantics (recommended: route to the planner loop, or remove it from the prompt if out of scope — pick one, justify in the commit message); add a test asserting the prompt's verdict block exactly matches the vocab constant, so drift is structurally impossible. File a KI entry (find->fix).

   c. **[P2] SPEC_OR_TEST_BLOCKED contract inconsistent on both sides.** _SPEC_OR_TEST_BLOCKED_RE (sprint-loop.py ~646-671) is .search() over the ENTIRE result text (narrating the string hard-blocks a GREEN chunk, no retry), while executor.md lines 33/58 instruct emitting the BARE string without the `RESULT:` prefix (parser never sees a genuine block). Fix: parse only the last RESULT: line of the result text (mirror the verdict parser's last-occurrence discipline), and make executor.md lines 33/58 name the full `RESULT: SPEC_OR_TEST_BLOCKED` literal from vocab.py. Extend tests/test_spec_blocked_signal.py with: (1) narration mentions the string but final line is RESULT: GREEN -> not blocked; (2) bare-string-only emission behavior is explicit and tested.

   d. **[P2] All-skipped regression suite passes the gate.** A regression run with 0 passed, N skipped, exit 0 is accepted as green evidence — the exact vacuous-green the gate fails closed on for the locked test ten lines above (tools/phase-3.2-evidence/consumer.py ~line 51). The gap exists in BOTH duplicated copies of regression_refusal_reason (consumer.py ~41 and local_backend.py ~210), which have already diverged. Fix: extract regression_refusal_reason into one shared module, refuse when passed == 0 (mirroring the locked-test rule), update both call sites, add producer-, consumer-, and gate-level tests for the all-skipped case.

   e. **Checkpoint round-trip inheritance check.** Verify chunk.retry_count and chunk.rejection_feedback survive a checkpoint round-trip (PR 2 made restore field-driven for both RunState and ChunkState — confirm with a test here since these fields matter to this PR's features).

   f. **SCHEMA.md enum update deferred from PR 2.** PR 2 verified that no emitter for phase_step `test-design-rerun` existed at its stage; your cherry-picks introduce it (grep the emitters to confirm, e.g. `phase_step="test-design-rerun"`). Add it to SCHEMA.md's phase_step enum AND the tripwire test list in tests/test_telemetry_v3.py together. The tripwire test will fail after your cherry-picks until you do — that is by design; do not delete or weaken it.

4. Validation: `/usr/bin/python3 -m pytest -q` must pass, ignoring ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds (duplicated local git history; pre-existing).
5. Commit style: conventional, lowercase, imperative; reference KI-16 and new KI ids.

Constraints: follow AGENTS.md (treat repo as public; technical, sourced, fair). Keep scope strictly to this package.

## Final report protocol

Write the full report (branch name, commit list, REPLAN routing decision + rationale, new KI numbers, test results, any deferrals) to planning/review-cleanup/REPORT-4-rejection-routing.md. Then your ENTIRE final chat message must be at most 3 lines, in exactly this shape:

    PR 4 done. Branch factory/rejection-routing-and-feedback, <N> commits. REPLAN: <routed to planner | removed>.
    Tests: <N> passed, <M> skipped, 1 known env failure. Blockers/deferrals: <none | one short phrase>.
    Full report: planning/review-cleanup/REPORT-4-rejection-routing.md

The supervising session reviews the branch before anything is pushed.
