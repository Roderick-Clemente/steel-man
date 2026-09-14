# Operator prompt — review-cleanup stack, PR 2 follow-up (supervisor punch list)

Repo: /Users/factory/work/adversarial-sprint-dev. Stay on branch factory/planner-integrity (verify with `git status` first; stop and report if the tree is not on it or not clean of tracked changes). Do NOT push, do NOT open a PR, do NOT touch untracked *.orig files.

Context: the supervising review of your branch found one blocker and one nit in your fix commits. Fix both, each as its own commit.

## 1. BLOCKER — extend the field-driven checkpoint restore to ChunkState (commit 2899cb5 follow-up)

Your load_checkpoint fix made the RunState restore field-driven, but the nested `chunks` restore is still a hand-curated list — the exact class the fix was meant to kill. It currently drops 10 of 22 ChunkState fields on resume: retry_count, rollback, evidence_source, gate_decision, gate_reason, rejection_feedback, findings, test_designer_run_id, executor_run_id, validator_run_ids. retry_count and rejection_feedback are fields PR 4's retry-feedback features depend on surviving resume.

Fix:
- Restore ChunkState the same field-driven way: iterate `dataclasses.fields(ChunkState)`, skip constructor args (chunk_id, scope), special-case enum fields (status -> ChunkStatus; check whether gate_decision is a GateDecision enum or a plain string and handle accordingly) and nested dataclass fields (findings, if it holds Finding objects — mirror the plan_findings handling).
- PRESERVE the existing verify_mode inheritance semantics: `cs.verify_mode = bool(...) or rs.verify_mode`. That OR is deliberate; make it an explicit special case with a one-line comment.
- Make the round-trip test programmatic so it can never go stale: iterate dataclass fields for BOTH RunState and ChunkState, set a distinct sentinel value per field (respecting types/enums), write_checkpoint, load_checkpoint, assert every non-skipped field equals its sentinel. A future field added to either dataclass must fail this test loudly if restore drops it. Keep the existing named assertions if you like, but the programmatic sweep is the requirement.

## 2. NIT — parse_accepted_assertion should take the LAST match

`_ACCEPTED_ASSERTION_RE.search()` returns the FIRST multiline match. A designer that narrates the line format early in its message (e.g. quoting the instruction) wins over its final authoritative line. Take the last match instead (e.g. `findall(...)[-1]` or iterate matches), consistent with the verdict parser's last-occurrence discipline. Add a test: result text contains an early narrated `ACCEPTED_ASSERTION: wrong phrase` line and a final `ACCEPTED_ASSERTION: right phrase` line; assert the right phrase wins.

## Validation

`/usr/bin/python3 -m pytest -q` must pass, ignoring ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds (duplicated local git history; pre-existing).

Commit style: conventional, lowercase, imperative (e.g. "fix(checkpoint): field-driven restore for ChunkState too").

## Final report protocol

Write the full report (commit SHAs, the gate_decision type you found and how you handled it, test results, any deferrals) to planning/review-cleanup/REPORT-2A-checkpoint-followup.md. Then your ENTIRE final chat message must be at most 3 lines, in exactly this shape:

    PR 2A done. Branch factory/planner-integrity, 2 commits (<sha1>, <sha2>).
    Tests: <N> passed, <M> skipped, 1 known env failure. Blockers/deferrals: <none | one short phrase>.
    Full report: planning/review-cleanup/REPORT-2A-checkpoint-followup.md

The supervising session re-reviews before push.
