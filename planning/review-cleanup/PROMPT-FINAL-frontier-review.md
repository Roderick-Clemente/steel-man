# Final frontier review — adversarial-sprint-dev review-cleanup stack

You are the final reviewer on a 7-PR stacked refactoring of the adversarial-sprint-dev repo. A prior review session (frontier) found bugs in a mega-PR, and a supervised multi-agent crew (mixed models, frontier supervisor) split that mega-PR into a clean stack, fixed every finding, and pushed all 7 branches. Your job is a holistic final review of the complete stack before the PRs open on GitHub.

## The repo

- Local clone: `/Users/factory/work/adversarial-sprint-dev`
- Remote: `github.com:Roderick-Clemente/adversarial-sprint-dev.git`
- Read `AGENTS.md` first — it governs conventions (treat repo as public, branch by author, no secrets/names/hiring context).
- The runner lives in `tools/sprint-loop.py` (~2,700 lines) plus the `tools/sprint_loop/` package. It orchestrates an adversarial sprint: a planner designs chunks, a test-designer writes locked tests, an executor implements against them, validators review, and gates fail-closed at every layer.

## The WHY — original review findings

The original branch `factory/schema-v3-and-subagent-executor` was a 7,257-line, 14-commit, 32-file mega-PR. A four-subagent parallel review found:

**P1 (high-confidence correctness):**
1. KI-16 dead retry path — a REJECT_IMPLEMENTATION retry re-enters `run_chunk_inner`, `validate_red` fails with "Invalid RED: test passed" because the rejected implementation is GREEN at HEAD, and the relaxation only covers `verify_mode or redesign_round` — not the impl-retry round. The executor never receives the validator's feedback. The PR's own experiment doc corroborates: "KI-16 — DID NOT FIRE."
2. `VERDICT: REPLAN` offered in validator.md but the orchestrate-review.py parser regex had no REPLAN token — a validator following the prompt gets parsed as a stray prose word or UNKNOWN.
3. pytest warnings-summary lines trip collection-phase signatures in `valid-red.py` — a valid RED with a conftest warning classifies as "Invalid RED: conftest error."

**P2 (verified, concrete triggers):**
- `load_checkpoint` drops fields the new flows depend on (`chunks_file`, `pilot_spec_file`, `chunk.retry_count`, `chunk.rejection_feedback`).
- Plan-review loop overwrites prior-round evidence at fixed paths while `plan_sha256_at_time_of_review` references the destroyed text.
- All-skipped regression suite (0 passed, N skipped, exit 0) passes the gate as green evidence — the exact vacuous-green the gate fails closed on for locked tests.
- `SPEC_OR_TEST_BLOCKED` regex is `.search()` over entire result text (narrating the string hard-blocks a GREEN chunk); meanwhile executor.md instructs emitting the bare string without the `RESULT:` prefix (parser never sees a genuine block).
- planner.md claims "You have no file-writing tool" but `DEFAULT_ENABLED_TOOLS[Role.PLANNER]` includes `Execute`.
- SCHEMA.md v3 enums don't match emitters; front matter still says v2.
- RUN-LEDGER scorecard doesn't reconcile with KNOWN-ISSUES.md.

**P3 (minor but real):**
- Validator telemetry stamps hardcoded branch literal.
- Inner pytest timeout (300s) can't fire before callers kill the process at 300s.
- test-designer.md documents an `--accepted-assertion` parse that no code implements.
- Dead first `main()` shadowed via `noqa: F811`.
- KI numbering skips KI-17 with no explanation.

**Approach flaws:**
- 5 separable concerns in one mega-PR — should have been 4-5 PRs.
- Signal vocabularies (verdicts, phase steps, result signals) live in 3+ hand-synced places with no single source of truth.
- Checkpoint save/load asymmetry (asdict-everything vs hand-restored field list) is a standing bug factory.
- Control flow routes on regexes over free-form prose instead of parsing the last tagged line.
- `sprint-loop.py` is ~2,700 lines mixing CLI, state machine, formatting, telemetry, and policy.

**Experiment/data flaws:**
- n=1 per arm, but the executive summary claims "decisively busted."
- ~209K of the full-pipeline gap is a confounded manual re-run (gemini validator).
- KI-18 broke the controlled variable (Arm B ran a 20-test suite vs Arm A's 7).
- "Code quality parity" rests on two noisy validators finding no bugs.
- The sharper finding (volume dominated, not price tier) was buried.

## The HOW — stacked-PR execution

The mega-PR was split into 7 stacked branches, each basing on the previous:

| # | Branch | Cherry-picks from original | Findings fixed |
|---|---|---|---|
| 1 | `factory/v3-telemetry-schema` | b74cf96 (telemetry v3) | Front matter v2→v3, `overridden` disposition, validator branch literal, enum alignment, dead guard |
| 2 | `factory/planner-integrity` | 9a52ed2 031a63c b911a38 da4b02f (KI-7/8 + plan-review loop) | Field-driven checkpoint restore (RunState + ChunkState), round-indexed plan evidence, strip Execute from planner, implement ACCEPTED_ASSERTION parse, `test-design` enum |
| 3 | `factory/red-structural-classification` | 7217ae7 0197c96 5c7024b (KI-9 + validator evidence + docs) | Warnings-summary exclusion (KI-17), dead INVALID_RED_SIGNATURES removal, shared timeout budget, KI-17 renumber from KI-14 collision |
| 4 | `factory/rejection-routing-and-feedback` | a404ddf d80c924 cecd984 116b710 7009844 (routing + feedback + blocked signal) | KI-16 dead retry path fixed, REPLAN removed (KI-19), SPEC_OR_TEST_BLOCKED last-line parse, shared regression refusal (all-skipped fix), vocab.py single source of truth, checkpoint round-trip for retry fields, `test-design-rerun` enum |
| 5 | `factory/executor-experiment-docs` | 9074d37 (experiment + KI-18) | Experiment reframe (n=1 label, confound quantified, KI-18 asterisks, volume-dominates conclusion, parity softened), ledger reconciliation through KI-19, KI-19 residual noted |
| 6 | `factory/runner-hygiene` | (no cherry-picks, cleanup only) | Dead main() removed, force-accept helper extracted, shared conftest fixtures, tool lists rendered from DEFAULT_ENABLED_TOOLS, PLAN_HASH footer aligned |
| 7 | `factory/plan-defect-route` | (no cherry-picks, fast follow) | KI-18 verified-and-pinned (already fixed by stack, regression test added), REPLAN implemented for real (vocab.py → parser → routing → bounded budget → exit code 7 → checkpoint round-trip → telemetry), KI-19 closed |

**Execution protocol:**
- Each PR was built by a separate bot session (mixed models: mid-tier for 1/6, frontier for 2/3/5, strongest for 4, DeepSeek V4 Pro for 7).
- A supervisor session (this one, frontier → GLM for the final PR) reviewed every branch before push: diff inspection, test runs, finding verification, scope creep checks.
- Two fix rounds were needed: PR 2A (ChunkState restore was still hand-curated) and PR 3A (KI-14 id collision with PR 4's cherry-pick).
- All prompt files and bot reports live in `planning/review-cleanup/` (PROMPT-1 through PROMPT-7, REPORT-2A through REPORT-7).

## The WHAT — current state

All 7 branches are pushed to origin. All are green except one known environmental test failure (`tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds` — duplicated local git history makes the fixture subject non-unique; pre-existing, not caused by any PR in this stack).

The original mega-branch `factory/schema-v3-and-subagent-executor` still exists and should be retired with a pointer to the stack once the PRs open.

## Punch list applied since the prior frontier review

A prior frontier review (REPORT-FINAL-frontier-review.md) found 7 issues. A punch list (PROMPT-FINAL-punchlist.md) was applied to the PR 7 branch (factory/plan-defect-route, the stack top) with 4 commits:

- **N-1 [P1] fixed**: `_main_inner`'s `_make_role` now derives tool lists from `DEFAULT_ENABLED_TOOLS[role]` instead of hardcoded literals; test extended to assert on the RunState `main()` constructs, not just the dict.
- **N-2 [P2] filed as KI-20**: REPLAN route validated on single-chunk runs; multi-chunk replan re-entry limitation documented as OPEN.
- **N-4 [P2] fixed**: RUN-LEDGER scorecard reconciled (14 fixed, 2 open + KI-20 = 3 open, "nineteen" issues, experiment section updated).
- **N-5 [P3] fixed**: Variance range corrected to ~38–94%.

Fast follows deferred (not in this stack): N-3 (resume drops seat assignments), N-6 (backends.py dead code), N-7 (vocab.py depth gaps).

## Your review scope

Do a holistic final review of the complete stack AFTER the punch list. Specifically:

1. **Cross-PR integration**: check out each branch in order (1→7) and verify the full test suite passes. Look for integration issues that only surface when all changes are combined (the individual PRs were each tested on their own branch, but the stack has not been tested as a single combined diff against main).

2. **The three P1 fixes**: independently verify each against the code:
   - KI-16: `run_chunk_inner` relaxation now includes `implementation_retry_round`; trace a REJECT_IMPL → retry path and confirm the executor prompt on round 2 contains the validator's finding.
   - REPLAN: verify vocab.py drives the validator.md prompt block, the orchestrate-review parser, and the routing in `run_chunk_with_retries` — and that the contract test ties them together.
   - Warnings-summary: verify `outside_failures_region` (or equivalent) now excludes the warnings summary, and that a valid RED with a conftest warning passes classification.

3. **The vocab.py extraction**: is it the right depth? Does it cover all the signal strings that previously drifted? Are there any remaining hand-synced copies that should have been consolidated?

4. **The REPLAN route (PR 7)**: this is the newest and hardest change. Verify:
   - The outer plan/chunks loop correctly re-enters planning on REPLAN.
   - Chunk state is genuinely invalidated (re-derived from chunks file, not reused from the rejected plan).
   - The replan budget survives checkpoint resume.
   - Exit code 7 is wired correctly in both interactive and unattended modes.
   - Evidence is archived (not deleted) on a replan round.

5. **The experiment doc**: read `tools/EXPERIMENT-cheap-vs-expensive-executor.md` on `factory/executor-experiment-docs` and verify the claims match the data tables. Confirm the 4.4x executor signal is present and labeled n=1. Confirm the confound math (with/without the 209K gemini seat) is correct. Confirm the ledger reconciles.

6. **Commit history quality**: scan `git log --oneline` across the stack. Are the commit messages clean, conventional, and properly scoped? Is there anything that would read poorly to an outside reviewer (per AGENTS.md's "treat this repo as public")?

7. **Any remaining findings from the original review that were not addressed**: check whether anything was silently dropped or deferred without documentation.

## Output

Write your review to `planning/review-cleanup/REPORT-FINAL-frontier-review.md`. Structure it as:
- **Stack integration verdict**: does the combined stack pass? Any integration-only issues?
- **P1 fix verification**: confirm or reject each of the three P1 fixes.
- **New findings**: any issues introduced by the stack itself, or missed by the prior reviews. Use [P0]-[P3] priority tags.
- **Quality assessment**: is this capstone-ready? What would you change before opening the PRs?
- **PR body recommendations**: for each of the 7 PRs, a 2-3 sentence suggested body (the supervisor will draft the final versions).

If the stack is clean, say so plainly. Do not pad with caveats.

## Final report protocol

Your ENTIRE final chat message must be at most 3 lines:

    Final review done. Stack: <clean | N issues found>. P1 fixes: <all verified | issue phrase>.
    Full report: planning/review-cleanup/REPORT-FINAL-frontier-review.md
