# Operator prompt — fast follow, PR 7: close the plan/test defect-signaling gaps

Repo: /Users/factory/work/adversarial-sprint-dev (all work stays local; do NOT push, do NOT open a PR, do NOT touch untracked *.orig files or untracked evidence/ dirs).

Base: the final branch of the review-cleanup stack (factory/runner-hygiene if PR 6 ran, otherwise factory/executor-experiment-docs — check which exists; stop and report if neither does). Create branch factory/plan-defect-route.

Context: the stack made test-defect signaling robust (REJECT_TEST routing; SPEC_OR_TEST_BLOCKED last-line parsing) but left two gaps the operator wants closed: (1) KI-18 — the test-designer bounce historically did not re-lock the redesigned test — may have been incidentally fixed by the stack but has no pinned proof; (2) the REPLAN verdict was removed (KI-19) because it never worked, leaving HUMAN_DECISION as the only outlet for a validator that believes the PLAN is defective. Locking tests is only sound if every defect class has a working escape; this PR completes the set.

## Task 1 — KI-18: verify and pin, or fix

1. Read the KI-18 entry in tools/KNOWN-ISSUES.md and the incident description in tools/EXPERIMENT-cheap-vs-expensive-executor.md (Arm B: after a REJECT_TEST redesign, the lock manifest still pointed at the pre-redesign SHA, so round 2 fail-closed on a stale lock).
2. Trace the current code: on a redesign round, run_chunk_inner re-enters and lock_test re-runs; determine whether the manifest is regenerated from the redesigned test BEFORE the next validation round reads locked_test_sha, in EVERY path (including resume-from-checkpoint mid-bounce).
3. If the re-lock now happens: add an end-to-end regression test that reproduces the Arm B sequence (lock 7-test suite -> REJECT_TEST -> designer rewrites to a different suite -> assert the manifest SHA equals the redesigned suite's SHA at the next validation) and update KI-18 to FIXED, citing the stack commit that closed it and this test as the pin.
4. If any path still serves a stale lock: fix it (regenerate the manifest when a redesigned test is accepted), same test as the pin, KI-18 -> FIXED.

## Task 2 — implement the plan-defect route (REPLAN done right)

Design constraints (from the KI-19 removal rationale — read the KI-19 entry first):
1. Reintroduce VERDICT: REPLAN in tools/sprint_loop/vocab.py, validator.md, and the orchestrate-review parser — via the existing vocab constants and contract tests, so prompt/parser/routing cannot drift.
2. Routing semantics: on a REPLAN verdict from chunk validation, the runner must (a) stop chunk execution fail-closed, (b) preserve all evidence (the plan-loop round-indexed paths from PR 2 apply), (c) carry the validator's finding into a new plan round: re-enter the plan -> plan-review -> reconcile gates with the finding rendered into the planner prompt (mirror the REJECT_TEST feedback threading pattern), and (d) invalidate downstream chunk state explicitly — chunks derived from the rejected plan must not run against the new plan without re-chunking.
3. Budget: a bounded replan budget (mirror test_design_bounces_left; default 1), exhaustion -> HUMAN_DECISION. The budget must survive checkpoint resume (the field-driven round-trip makes this automatic — add the sentinel assertion anyway).
4. In unattended mode, exhaustion exits with a distinct code documented in --help, consistent with how SPEC_OR_TEST_BLOCKED and plan-review exhaustion are handled.
5. Tests at the same level as tests/test_reject_test_routing.py: drive the real run loop with stubbed droid seats; assert the finding reaches the planner prompt, chunk state is invalidated, budget decrements, exhaustion fails closed. Update KI-19 to note the route is now implemented; update the KI-14 entry if the first-attempt invalid-RED seat classification is affected by your changes (do not fix KI-14 here unless it falls out naturally — note it either way).
6. Update telemetry: if the replan round emits seat rows, phase_step values must come from vocab.PHASE_STEPS and SCHEMA.md + the tripwire test must be updated together.

## Validation

`/usr/bin/python3 -m pytest -q` must pass, ignoring ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds. Commit style: conventional, lowercase, imperative; reference KI-18/KI-19.

## Final report protocol

Write the full report to planning/review-cleanup/REPORT-7-plan-defect-route.md. Then your ENTIRE final chat message must be at most 3 lines:

    PR 7 done. Branch factory/plan-defect-route, <N> commits. KI-18: <already fixed + pinned | fixed here>.
    Tests: <N> passed, <M> skipped, 1 known env failure. Blockers/deferrals: <none | one short phrase>.
    Full report: planning/review-cleanup/REPORT-7-plan-defect-route.md

The supervising session reviews the branch before anything is pushed.
