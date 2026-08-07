# telemetry/SCHEMA.md

Schema for the §13 efficacy evaluation's data files. Three JSONL files; append-only. Lives in this public repo because the schema is part of the convention; the **rows themselves are git-ignored** (see `.gitignore`).

The aggregator (`telemetry/aggregate.py`) reads these paths from `$TELEMETRY_DATA_DIR` (default `./telemetry`) or `--data-dir`. Schema version recorded in front-matter.

## Front-matter (applies to every row)

| key            | type    | required | note |
|---             |---      |---       |---   |
| `schema_version` | string | yes | `"v1"` for now. |
| `ts`             | ISO-8601 datetime UTC | yes | the time the row was appended. |

## runs.jsonl — one row per `droid exec` invocation

| key                   | type     | required | note |
|---                    |---       |---       |---   |
| `run_id`              | string   | yes | stable id; same id appears in commit-body `Telemetry-row:` line |
| `phase`               | string   | yes | `phase-0`, `phase-0-5`, `phase-1`, … |
| `branch`              | string   | yes | branch the run executed against |
| `role`                | enum     | yes | `planner` / `executor` / `validator` / `reviewer` |
| `model_id`            | string   | yes | the `--model` value passed |
| `provider`            | string   | yes | openai / google / xai / anthropic / fireworks / … |
| `family`              | string   | yes | openai-family / gemini-family / grok-family / claude-family / … |
| `providerLock`        | string   | yes | observed provider lock from inner session |
| `apiProviderLock`     | string   | yes | observed API provider lock from inner session |
| `num_turns`           | int      | yes | from envelope |
| `input_tokens`        | int      | yes | `usage.input_tokens` |
| `output_tokens`       | int      | yes | `usage.output_tokens` |
| `cache_read_tokens`   | int      | no  | often zero/missing in some providers |
| `thinking_tokens`     | int      | no  | often zero/missing in some providers |
| `duration_ms`         | int      | yes | wall clock |
| `is_error`            | bool     | yes | run-level error flag (NOT the per-tool flag) |
| `decision`            | string   | no  | `ACCEPT` / `ACCEPT-WITH-NITS` / `REJECT` / `null` |
| `reviewer_panel`      | string[] | when role=reviewer | ordered list of modelIds on the panel |
| `review_target_branch`| string   | when role=reviewer | the branch the review was against |
| `verdict_text_first_240` | string | no | truncated verdict text (first 240 chars) |
| `envelope_path`       | string   | no | path to raw envelope on disk for the audit run |

## findings.jsonl — one row per finding surfaced in a review pass

| key                | type     | required | note |
|---                 |---       |---       |---   |
| `finding_id`       | string   | yes | `F-<short-hash-of-content-or-pointer>` |
| `phase`            | string   | yes | |
| `ts`               | ISO-8601 | yes | |
| `surface`          | string   | yes | `file:line` or section pointer |
| `category`         | enum     | yes | `correctness` / `security` / `performance` / `readability` / `spec-deviation` / `other` |
| `severity`         | enum     | yes | `blocking` / `major` / `minor` / `nit` |
| `source_role`      | string   | yes | `validator` / `reviewer` (the row is appended by the reviewer) |
| `source_run_id`    | string   | yes | `runs.jsonl` row for the run that surfaced this finding |
| `source_model_id`  | string   | yes | the model that surfaced this finding |
| `source_family`    | string   | yes | |
| `panel_size_at_surfacing` | int | yes | how many models were on the panel at the time |
| `first_seen_in_panel_position` | int | yes | 1..N (1 = first reviewer, N = Nth). 0 = caught by all reviewers identically (rare; recorded as 'shared-not-unique'). |
| `raw_text_first_240` | string | no | the finding's first 240 chars, no chain-of-thought |
| `verdict_blocking_total` | int | yes | total blocking-severity findings in the same review pass |

## dispositions.jsonl — one row per finding closed or explicitly not-closed

| key                       | type     | required | note |
|---                        |---       |---       |---   |
| `finding_id`              | string   | yes | matches `findings.jsonl` |
| `disposition`             | enum     | yes | `fixed` / `wontfix-with-reason` / `deferred` / `wontfix` / `reverted` |
| `disposition_reason`      | string   | when `wontfix-with-reason` | the explicit reason |
| `disposition_commit_sha`  | string   | yes | the commit that closed (or tracked) the finding |
| `disposition_model_id`    | string   | yes | the model that wrote the fix |
| `disposition_tokens_input`  | int    | no  | total tokens spent on the fix |
| `disposition_tokens_output` | int    | no  | |
| `disposition_duration_ms` | int      | no  | |
| `disposition_at`          | ISO-8601 | yes | |

## How the §13 efficacy questions read these files

- *How many bugs of given severity does the Nth reviewer find?* → `findings.jsonl ⨝ runs.jsonl` on `source_run_id` and `source_role=reviewer`; group by `first_seen_in_panel_position`, count by `severity`.
- *How many of those are actually fixed?* → `findings.jsonl ⨝ dispositions.jsonl` on `finding_id`; `count(disposition=fixed) / count(surface)`, segmented by severity.
- *Cost of each review and fix in tokens?* → two complementary paths, both used by `telemetry/aggregate.py`:
  - *Review cost*: from `findings.jsonl` → unique `source_run_id` → `runs.jsonl`: sum `input_tokens + output_tokens`. Each reviewer run contributes once regardless of how many findings it surfaced (round-1 cross-family fix; previous version double-counted).
  - *Fix cost*: from `dispositions.jsonl` where `disposition=fixed`: sum `disposition_tokens_input + disposition_tokens_output`. One row per fixed finding.
  - Disposition rows should carry `disposition_tokens_*` (written at the moment of the fix run). When absent on a row, the canonical fallback is to join `dispositions ⨝ runs` on `disposition_commit_sha == run_id` (the run that produced the disposition's diff) and sum run tokens. That fallback is not yet implemented in `aggregate.py` — see `tools/conventions/model-discipline.md` for the migration gate.

## Stability

When schema changes, increment `schema_version` and write a migration note into this file under a new heading. The aggregator refuses to read rows with `schema_version` higher than the one it was written against, so old aggregates can be re-run for back-compat.
