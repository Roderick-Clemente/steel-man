# Operator prompt — review-cleanup stack, PR 3: RED structural classification + validator evidence

Repo: /Users/factory/work/adversarial-sprint-dev (all work stays local; do NOT push, do NOT open a PR, do NOT touch untracked *.orig files or untracked evidence/ dirs).

Goal: PR 3 of a stacked split of branch factory/schema-v3-and-subagent-executor. Base: factory/planner-integrity (must exist; stop and report if not).

## Steps

1. `git checkout -b factory/red-structural-classification factory/planner-integrity`
2. Cherry-pick in order: `7217ae7 0197c96 5c7024b` (KI-9 structural RED classification; validator prompt rendering + full-suite evidence; KI-12/KI-13 docs)
3. Fix these verified review findings, each as its own commit:

   a. **[P1] Warnings summary trips collection-phase signatures.** tools/phase-1-scripts/valid-red.py (~line 212): step 4's fallback matches COLLECTION_PHASE_SIGNATURES against `outside_failures_region(combined)`, but pytest's `warnings summary` section is also outside FAILURES and routinely cites file paths. Reproduced: 1 collected test + real assertion failure + a single `tests/conftest.py:5: PytestDeprecationWarning` line classifies as "Invalid RED: conftest error", blocking a valid RED for any pilot whose conftest warns. Fix: exclude the warnings-summary section from the step-4 scan region (mirroring the FAILURES exclusion) or restrict the fallback to head + short-summary ERROR lines. Add a regression test whose fixture is captured real pytest output containing a warnings summary (match the existing pin-the-observed-failure style in tests/test_valid_red_structure.py). File a new KI entry in tools/KNOWN-ISSUES.md for this (next free number — note the KI-17 check below), status FIXED, following the existing entry format.

   b. **[P3] Dead code.** INVALID_RED_SIGNATURES in valid-red.py is production dead code — classify() never reads it and there are no production callers despite the "retained for callers" comment. Delete it and point the partition test at the three real signature lists.

   c. **[P3] Timeout budget can never fire.** tools/phase-3.2-evidence/local_backend.py (~line 243): the inner per-pytest timeout was raised to 300s but both callers cap the ENTIRE producer process at 300s (per_chunk._run_step(..., timeout=300); orchestrate-review.py step1 subprocess.run(..., timeout=300), where TimeoutExpired propagates uncaught). Thread one timeout budget through: callers' outer budget must exceed the sum of inner steps, and orchestrate-review step1 must catch TimeoutExpired and fail closed with a diagnosable message instead of a bare traceback. Add a test for the fail-closed path.

   d. **KI-17 gap.** Check whether KNOWN-ISSUES.md at this stage skips KI-17 with no explanation; if so add a one-line tombstone note explaining the gap (or renumber if you can prove nothing references the later ids yet — tombstone is safer).

4. Validation: `/usr/bin/python3 -m pytest -q` must pass, ignoring ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds (duplicated local git history; pre-existing).
5. Commit style: conventional, lowercase, imperative; reference KI-9 and the new KI id.

Constraints: follow AGENTS.md (treat repo as public; technical, sourced, fair). Keep scope strictly to this package.

## Final report protocol

Write the full report (branch name, commit list, new KI number filed, test results, any deferrals) to planning/review-cleanup/REPORT-3-red-classification.md. Then your ENTIRE final chat message must be at most 3 lines, in exactly this shape:

    PR 3 done. Branch factory/red-structural-classification, <N> commits.
    Tests: <N> passed, <M> skipped, 1 known env failure. Blockers/deferrals: <none | one short phrase>.
    Full report: planning/review-cleanup/REPORT-3-red-classification.md

The supervising session reviews the branch before anything is pushed.
