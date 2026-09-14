# Operator prompt — review-cleanup stack, PR 5: experiment reframe + ledger reconciliation

Repo: /Users/factory/work/adversarial-sprint-dev (all work stays local; do NOT push, do NOT open a PR, do NOT touch untracked *.orig files or untracked evidence/ dirs).

Goal: PR 5 of a stacked split — documentation. Base: factory/rejection-routing-and-feedback (must exist; stop and report if not).

## Steps

1. `git checkout -b factory/executor-experiment-docs factory/rejection-routing-and-feedback`
2. `git cherry-pick 9074d37` (executor experiment results + KI-18). Conflict guidance: tools/KNOWN-ISSUES.md now ends with KI-17 and KI-19 (filed by PRs 3-4 of this stack); insert the cherry-picked KI-18 entry BETWEEN them so the file stays in numeric order, and keep all existing entries.
3. Rewrite tools/EXPERIMENT-cheap-vs-expensive-executor.md so the claims match the evidence. Keep ALL raw data tables untouched. Required stance (operator-approved): "these are our findings; we made framework enhancements and will rerun; the data leans toward gpt-5.2 having lower total cost of ownership, but this is still being tested." Specifically:

   a. Executive summary: replace "hypothesis busted ... decisively" with a directional finding. Lead with the executor-only comparison (the clean signal: 371,917 vs 85,394 credits, 4.4x) and state explicitly that n=1 per arm.

   b. Add a run-to-run variance caveat using the experiment's own control seats as evidence: reviewer seats with identical inputs varied 66K vs 128K and 176K vs 128K credits across arms — that is the noise floor a single run cannot rise above.

   c. Propagate the two Section-7 caveats up into every section that currently ignores them: (i) the ~209K gemini-validator manual-re-run confound — present full-pipeline totals both with and without that seat, and soften the "~30% cheaper" headline accordingly; (ii) KI-18 broke the controlled variable (Arm B ran a 20-test suite vs Arm A's 7), which contaminates the lines-produced and code-quality-parity comparisons in Sections 5 and 1 — add the asterisk where those claims are made.

   d. Reframe the conclusion around the sharper transferable insight: credits = price-per-token x volume, and VOLUME dominated (32,747 vs 6,339 output tokens; 20 vs 13 turns) — the "cheap executor" hypothesis was ill-posed, not merely false. State the rerun plan: >=3 runs per arm, KI-18 fixed so the locked suite is a true constant, before any "busted/confirmed" verdict.

   e. Soften "code quality parity": it currently rests on two validators (who disagreed procedurally) finding no bugs; label it "no defect found by either validator; independent review of the two diffs pending."

4. Reconcile tools/RUN-LEDGER.md (~line 171) against tools/KNOWN-ISSUES.md at THIS branch's HEAD: recount found/fixed/open/closed-as-limitation from the actual entry statuses (KI-5 is OPEN; KI-6 is withdrawn and needs its own bucket; include KI-18 and every KI filed by PRs 3-4 in this stack). The arithmetic must reconcile exactly. Numbering note: KI-17 exists on this stack (warnings-summary misclassification, filed FIXED by PR 3) — there is NO gap at 17 and no tombstone is needed; the sequence is contiguous through KI-18.
5. Update the KNOWN-ISSUES.md summary/header counts if any exist, and verify every KI cross-reference in the experiment doc still points at a real entry. Also update the KI-19 entry status line to record the accepted residual: the REPLAN removal leaves HUMAN_DECISION as the only outlet for a plan-defect judgment from chunk validation; an implemented plan-defect route is planned as a fast follow (do not renumber anything).
6. Validation: no code changes expected; run `/usr/bin/python3 -m pytest -q` anyway to prove the stack is green (ignore ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds). Re-read AGENTS.md's "treat this repo as public" section and confirm the rewritten doc stays technical, sourced, and fair.
7. Commit style: `docs:` prefix, lowercase imperative.

## Final report protocol

Write the full report (branch name, before/after summary of each claim you changed, final ledger arithmetic, any deferrals) to planning/review-cleanup/REPORT-5-experiment-docs.md. Then your ENTIRE final chat message must be at most 3 lines, in exactly this shape:

    PR 5 done. Branch factory/executor-experiment-docs, <N> commits.
    Ledger reconciles: <yes | issue phrase>. Tests: green except 1 known env failure.
    Full report: planning/review-cleanup/REPORT-5-experiment-docs.md

The supervising session reviews the branch before anything is pushed.
