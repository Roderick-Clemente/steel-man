# PR 2A — checkpoint follow-up report

**Branch:** `factory/planner-integrity`
**Commits:** `1e4b086`, `54b9979`

## 1. BLOCKER — field-driven ChunkState restore (`1e4b086`)

The RunState restore was made field-driven in `2899cb5`, but the nested
ChunkState restore remained hand-curated. It dropped 10 of 22 fields:
`retry_count`, `rollback`, `evidence_source`, `gate_decision`,
`gate_reason`, `rejection_feedback`, `findings`, `test_designer_run_id`,
`executor_run_id`, `validator_run_ids`.

**Fix:** Applied the same `dataclasses.fields(ChunkState)` iteration.
Special cases:

- `status` → `ChunkStatus` enum conversion.
- `gate_decision` → `GateDecision(raw) if raw else None`. The serialized
  form is a string value (e.g. `"ACCEPT"`) or JSON `null`. Checked
  `ChunkState.to_dict()` — it serializes via `.value` when set, `None`
  otherwise. The restore handles both: non-null strings are converted to
  the enum; null stays `None`.
- `findings` → nested `Finding` dataclass list, mirroring the
  `plan_findings` handling.
- `verify_mode` → kept as an explicit special case with comment:
  `bool(c.get("verify_mode", False)) or rs.verify_mode` (deliberate OR
  inheriting the run-level flag).

**Test:** Replaced the hand-written round-trip test with a programmatic
sweep that iterates `dataclasses.fields()` for both `RunState` and
`ChunkState`, sets a distinct sentinel value per field (respecting
types/enums), writes a checkpoint, loads it, and asserts every
non-skipped field equals its sentinel. Additional tests: `verify_mode`
OR inheritance, `gate_decision=None` round-trip, unknown JSON keys
ignored.

## 2. NIT — last-match assertion parse (`54b9979`)

`parse_accepted_assertion` used `re.search()` (first match). A designer
narrating the line format early in its message would shadow the final
authoritative line.

**Fix:** Changed to `re.findall(...)[-1]`, consistent with the verdict
parser's last-occurrence discipline. Updated the existing
`test_parse_takes_first_occurrence` → `test_parse_takes_last_occurrence`
and added `test_narrated_line_does_not_win_over_final_authoritative_line`.

## Test results

```
213 passed, 3 skipped, 1 failed
```

The sole failure is the pre-existing known environmental failure
`tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds`
(duplicated local git history). No new failures.

## Deferrals

None.
