# Operator prompt — review-cleanup stack, PR 6 (optional): hygiene sweep

Repo: /Users/factory/work/adversarial-sprint-dev (all work stays local; do NOT push, do NOT open a PR, do NOT touch untracked *.orig files or untracked evidence/ dirs).

Base: factory/executor-experiment-docs (must exist; stop and report if not). Create branch factory/runner-hygiene.

Scoped cleanup only, one commit each, full pytest green after every commit (ignore ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds — duplicated local git history; pre-existing):

1. Delete the dead first main() in tools/sprint-loop.py (~line 2072 at old head, shadowed via `noqa: F811`); fold any real help-rendering behavior into the surviving entrypoint.
2. Extract the ~35-line force-accept disposition block duplicated in reconcile_human_gate (~lines 1222 and 1345 at old head, already diverging on checkpoint-writing) into one helper; make the checkpoint behavior explicit.
3. Create tests/conftest.py with shared _load_runner_module/_run_state/stub-loop fixtures and migrate the three test files that paste near-identical copies (they have already drifted: one tracks td_phase_steps).
4. Render each seat's tool list into its prompt from DEFAULT_ENABLED_TOOLS instead of hand-written names (executor.md advertises Write/MultiEdit and test-designer.md advertises Write — identifiers state.py says reject the droid call).
5. Align planner.md's PLAN_HASH footer wording with actual behavior (run_planner hashes the message verbatim; no substitution occurs).

Do not refactor beyond these five items. Commit style: conventional, lowercase, imperative.

## Final report protocol

Write the full report (per-item diffstat, test results, any deferrals) to planning/review-cleanup/REPORT-6-hygiene.md. Then your ENTIRE final chat message must be at most 3 lines, in exactly this shape:

    PR 6 done. Branch factory/runner-hygiene, 5 commits.
    Tests: <N> passed, <M> skipped, 1 known env failure. Blockers/deferrals: <none | one short phrase>.
    Full report: planning/review-cleanup/REPORT-6-hygiene.md

The supervising session reviews the branch before anything is pushed.
