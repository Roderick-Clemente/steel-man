# Operator prompt — final frontier review punch list

Repo: /Users/factory/work/adversarial-sprint-dev. Stay on branch factory/plan-defect-route (verify with `git status`; stop and report if not on it or if tracked changes are dirty). Do NOT touch untracked *.orig files or untracked evidence/ dirs.

Context: the final frontier review (REPORT-FINAL-frontier-review.md) found 7 issues. Three need fixing before the PRs open; the rest are fast follows. Put all fixes on this branch as additional commits (it is the stack top — no downstream rebase needed).

## 1. [P1] N-1 — KI-7 fix is ineffective on the live path

PR 2 stripped `Execute` from `DEFAULT_ENABLED_TOOLS[Role.PLANNER]` (state.py) but `_main_inner` builds the planner seat with a hardcoded literal `"Read,Glob,Grep,LS,Execute"` that bypasses the dict. The test pins the dict nobody on the live path reads.

Fix:
- In `tools/sprint-loop.py::_main_inner`, change every `_make_role(..., "Read,Glob,Grep,LS,Execute")` (and any other hardcoded tool strings for planner/test-designer/executor/validator) to derive from `DEFAULT_ENABLED_TOOLS[role]` instead. Delete the literals.
- This also fixes the sibling drift the reviewer flagged: `DEFAULT_ENABLED_TOOLS` grants `ApplyPatch` to executor/test-designer (KI-2 invalid-id hazard) while `_main_inner` strips it — consolidating to one source makes the prompt `{{enabled_tools}}` rendering and the live invocation agree.
- Extend `tests/test_planner_no_execute.py` to assert on the RunState that `main()` actually constructs (e.g. via a `--dry-run` invocation that captures the constructed `rs.planner.enabled_tools`), not just the dict. The test must fail against the old hardcoded literal.

Commit message: `fix(planner): derive live tool allowlists from DEFAULT_ENABLED_TOOLS (KI-7, N-1)`

## 2. [P2] N-2 — REPLAN pass re-executes accepted chunks

On a replan round, `_chunking_and_chunk_loop` re-derives every chunk from index 0. Previously-accepted chunks are GREEN at HEAD, so `validate_red` rejects them ("Invalid RED: test passed"), the relaxation doesn't apply (fresh chunk, empty `rejection_kind`), and the run bricks at HUMAN_DECISION.

Decision: **file as KI now; fix is a fast follow.** The pilot currently runs single-chunk, so the REPLAN route is valid for its actual use case. Filing honestly is better than shipping an untested multi-chunk fix under time pressure.

- File a new KI entry (KI-20) in tools/KNOWN-ISSUES.md: "REPLAN route validated on single-chunk runs; multi-chunk replan pass re-runs accepted chunks and fails their RED gate." Status: OPEN. Severity: design gap. Note the three fix directions the reviewer proposed (track accepted chunk ids; extend GREEN relaxation to replan-pass chunks; or skip chunks whose scope is unchanged in the revised plan).
- Update the PR 7 body recommendation in REPORT-FINAL to note the validation envelope honestly: "exercised live-shaped on single-chunk runs; multi-chunk replan has a known re-entry limitation (KI-20)."
- Do NOT attempt the multi-chunk fix in this commit — it needs its own design pass and end-to-end test.

Commit message: `docs: file KI-20 (multi-chunk replan re-entry limitation)`

## 3. [P2] N-4 — RUN-LEDGER scorecard stale after PR 7

`tools/RUN-LEDGER.md` says "3 open (KI-5, KI-13, KI-18)" but PR 7 closed KI-18. Fix:
- "13 fixed" → "14 fixed" (add KI-18 to the fixed list)
- "3 open (KI-5, KI-13, KI-18)" → "2 open (KI-5, KI-13)"
- "Sixteen issues" → "Nineteen issues" (the "KI-7 shape" section says "four of the sixteen")
- The "Upcoming: two-arm executor experiment" section should reflect that the experiment is complete (PR 5 reports it with run ids), not gated on attempt 11
- Add KI-20 (from fix #2 above) to the ledger: 20 found, 14 fixed, 3 open (KI-5, KI-13, KI-20)

Commit message: `docs: reconcile RUN-LEDGER after KI-18 close and KI-20 file (N-4)`

## 4. [P3] N-5 — Experiment doc variance range

In `tools/EXPERIMENT-cheap-vs-expensive-executor.md` on this branch, change "~50–94% variance" to "~38–94% variance" (grok-4.5 is 48,220/128,100 ≈ 38%, not 50%).

Commit message: `docs: correct reviewer-variance range in experiment doc (N-5)`

## Not in this punch list (fast follows for a future PR)

- N-3 (checkpoint resume drops seat assignments): pre-existing, needs role reconstruction in `_main_inner` after `load_checkpoint`. File as KI-21 if not already tracked.
- N-6 (backends.py dead duplicate + branch fallback): hygiene, one commit.
- N-7 (vocab.py depth: plan-reviewer verdicts + reached_phase_step literals): refactor, one commit.

## Validation

`/usr/bin/python3 -m pytest -q` must pass, ignoring ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds.

## Final report protocol

Write the full report to planning/review-cleanup/REPORT-FINAL-punchlist.md. Then your ENTIRE final chat message must be at most 3 lines:

    Punch list done. Branch factory/plan-defect-route, 4 commits. N-1: fixed. N-2: KI-20 filed. N-4/N-5: fixed.
    Tests: <N> passed, <M> skipped, 1 known env failure. Blockers/deferrals: <none | phrase>.
    Full report: planning/review-cleanup/REPORT-FINAL-punchlist.md
