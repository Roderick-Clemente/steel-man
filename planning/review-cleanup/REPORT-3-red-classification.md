# PR 3 report: RED structural classification and validator evidence

## Branch

`factory/red-structural-classification`, based on
`factory/planner-integrity`.

## Commit list

1. `0a70296` Classify RED on structure, not on substrings (KI-9)
2. `76c9983` fix(validate): render the validator prompt and evidence the full suite
3. `478aaff` docs: reclassify KI-12, file KI-13 (commit lands before the gate)
4. `03018b8` fix(valid-red): ignore warning summaries (KI-9, KI-17)
5. `b60fece` refactor(valid-red): remove unused signatures (KI-9, KI-17)
6. `b530f33` fix(evidence): budget producer timeout (KI-9, KI-17)

## Changes

- Excluded pytest's warnings-summary section from the collection-signature
  fallback and added a captured conftest-warning regression fixture.
- Filed **KI-17**, "Warnings summary misclassified as a collection failure,"
  with status `FIXED`.
- Removed the unused `INVALID_RED_SIGNATURES` production aggregate and made
  the partition test assert only the three signature lists used by
  `classify()`.
- Centralized evidence-producer step budgets. Pytest now has a 300-second
  inner budget, and both outer callers use a budget exceeding all enabled
  producer steps. `orchestrate-review.py` now catches an evidence timeout and
  returns a diagnosable fail-closed result.
- Added a regression test for the orchestrator timeout path and its budget.
- Filled the previously unused KI-17 number. The entry records that entries 14
  through 16 and KI-18 were already assigned in the branch sequence this
  stack repackages.

## Validation

- Focused RED classification tests: `11 passed`.
- Focused timeout, validator-evidence, and sprint-loop tests: `151 passed`.
- Full suite: `/usr/bin/python3 -m pytest -q` produced `394 passed`,
  `3 skipped`, and the one allowed known environmental failure:
  `tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds`. The failure
  is caused by duplicated local git history, which makes the fixture subject
  non-unique.
- Full suite with only that test deselected:
  `394 passed, 3 skipped, 1 deselected in 4.71s`.
- `py_compile` passed for the modified Python modules; `git diff --check`
  passed.

## Deferrals

None.

## 3A follow-up

The warnings-summary issue is KI-17. The three follow-up commits were rebased
so their messages cite KI-17, preserving the six-commit branch shape. The
tracked source and test directories contain no legacy issue-id references.
The required suite, with only the known environmental test deselected, passed:
`394 passed, 3 skipped, 1 deselected in 4.75s`.
