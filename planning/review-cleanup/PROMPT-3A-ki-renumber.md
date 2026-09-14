# Operator prompt — review-cleanup stack, PR 3 follow-up (supervisor punch list)

Repo: /Users/factory/work/adversarial-sprint-dev. Stay on branch factory/red-structural-classification (verify with `git status` first; stop and report if the tree is not on it or not clean of tracked changes). The branch is UNPUSHED — history rewrite is safe and expected here. Do NOT push, do NOT open a PR, do NOT touch untracked *.orig files.

## Context — id collision found in supervising review

You filed the warnings-summary issue as KI-14. But PR 4 of this stack cherry-picks commit a404ddf, which files the ORIGINAL branch's `## Issue KI-14: An invalid RED still retries the executor` — a different issue with the same id, heavily cross-referenced by RUN-LEDGER.md tables and the experiment doc that PRs 4-5 cherry-pick. The original ids KI-14/15/16/18 must stay stable; YOUR new entry is the one that renumbers.

## Task — renumber your warnings-summary entry KI-14 -> KI-17

KI-17 is the number the original sequence skipped, so this fills the gap and makes numbering contiguous through KI-18 by the end of the stack.

1. In tools/KNOWN-ISSUES.md: retitle `## Issue KI-14: Warnings summary misclassified as a collection failure` to KI-17. Add one line to the entry noting the out-of-sequence number, e.g.: "Numbered KI-17: filed during the review-cleanup pass; KI-14-16 and KI-18 were already assigned on the branch this stack re-packages, and 17 was the unused number in that sequence."
2. Grep the WHOLE branch diff (`git diff factory/planner-integrity..HEAD`) for every other `KI-14` reference you introduced — test file names/docstrings, code comments, fixture text — and update them to KI-17. At this branch head no other KI-14 exists, so every current KI-14 string is yours.
3. Rewrite the three commit messages that cite KI-14 — `0389f28`, `9fd7ca5`, `6365ac5` — replacing `KI-14` with `KI-17`. Fold the content changes from steps 1-2 into the appropriate commits during the same rebase (the entry retitle belongs in the commit that filed it, 0389f28) rather than appending a fix-up commit; the final history must be the same 6-commit shape with identical code diffs apart from the renumber. Suggested mechanics: `git rebase -i factory/planner-integrity` driven non-interactively via GIT_SEQUENCE_EDITOR, or `git reset --soft` reconstruction — your choice, but verify afterward with `git log --oneline` (6 commits) and `git diff <old-tip>` (only KI-14->KI-17 strings differ; take the old tip SHA before you start).
4. Validation: `/usr/bin/python3 -m pytest -q` must pass, ignoring ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds. Also `grep -rn "KI-14" tools/ tests/` must return nothing on this branch.
5. Update planning/review-cleanup/REPORT-3-red-classification.md to reflect the renumber (it currently says KI-14 and claims no KI-17 gap handling was needed).

## Final report protocol

Append a short "3A follow-up" section to REPORT-3-red-classification.md. Then your ENTIRE final chat message must be at most 3 lines:

    PR 3A done. Branch factory/red-structural-classification rebased, 6 commits, new tip <sha>.
    grep KI-14: clean. Tests: <N> passed, <M> skipped, 1 known env failure.
    Full report: planning/review-cleanup/REPORT-3-red-classification.md

The supervising session re-reviews before push.
