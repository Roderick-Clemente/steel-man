# telemetry/SCHEMA.md

Schema for the §13 efficacy evaluation's data files. Three JSONL files; append-only. Lives in this public repo because the schema is part of the convention; the **rows themselves are git-ignored** (see `.gitignore`).

The aggregator (`telemetry/aggregate.py`) reads these paths from `$TELEMETRY_DATA_DIR` (default `./telemetry`) or `--data-dir`. Schema version recorded in front-matter.

## Front-matter (applies to every row)

| key            | type    | required | note |
|---             |---      |---       |---   |
| `schema_version` | string | yes | `"v3"` for rows written by the Phase 4.5 runner; `"v2"` for older Phase 3.2+ rows; `"v1"` for legacy rows. |
| `ts`             | ISO-8601 datetime UTC | yes | the time the row was appended. |

## runs.jsonl — one row per `droid exec` invocation

| key                   | type     | required | note |
|---                    |---       |---       |---   |
| `run_id`              | string   | yes | stable id; same id appears in commit-body `Telemetry-row:` line |
| `phase`               | string   | yes | `phase-0`, `phase-0-5`, `phase-1`, … |
| `branch`              | string   | yes | branch the run executed against |
| `role`                | enum     | yes | `planner` / `executor` / `validator` / `reviewer` / `test-designer` |
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
| `evidence_source`     | enum     | no | `in-session` (validator ran pytest itself) / `bundle` (validator read an EvidenceBundle). Required for Phase 3.2+ validator rows so the H-CI A/B is attributable. |
| `mcp_call_tokens`     | int      | no | tokens consumed by the MCP evidence-pull *request* (the call that fetches the bundle). Zero/absent when `evidence_source=in-session`. |
| `mcp_payload_tokens`  | int      | no | tokens of the *returned* EvidenceBundle that entered the agent's context (the bundle read). This is the replacement cost measured by the §3.2 fairness rule. Zero/absent when `evidence_source=in-session`. |
| `raw_test_output_tokens` | int   | no | tokens of the in-session raw pytest output that `mcp_payload_tokens` replaces. Recorded on the control arm (`evidence_source=in-session`) so the fairness ceiling `size(2)` is measured, not assumed. |

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
| `plan_section`      | string   | no | the plan section the finding is against (e.g. `Chunk plan / commands`). Absent on rows written before Phase 4.5's plan-review loop. |
| `risk_if_ignored`   | string   | no | what goes wrong if the finding is not acted on. This — not `raw_text_first_240`, which holds the plan's own claim — is the defect. Absent on older rows. |
| `verdict_blocking_total` | int | yes | total blocking-severity findings in the same review pass |

## dispositions.jsonl — one row per finding closed or explicitly not-closed

| key                       | type     | required | note |
|---                        |---       |---       |---   |
| `finding_id`              | string   | yes | matches `findings.jsonl` |
| `disposition`             | enum     | yes | `fixed` / `wontfix-with-reason` / `deferred` / `wontfix` / `reverted` / `overridden` |
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

## Migration v1 → v2 (Phase 3.2)

**Date:** 2026-08-07. **Driver:** Phase 3.2 evidence-tier externalization.

Changes:

1. **`role` enum extended** with `test-designer` (KI-4 fix). The Phase 3
   `runs.jsonl` rows already used `role: "test-designer"` ahead of the schema;
   v2 makes the schema match the data. No data migration needed for existing
   rows.

2. **Four new optional fields on `runs.jsonl`** for the H-CI fairness rule
   (SPIKE.md §3.2):
   - `evidence_source` — `in-session` (control) vs `bundle` (treatment). Marks
     which arm a validator row belongs to so the A/B is attributable.
   - `mcp_call_tokens` — the MCP request cost (treatment only).
   - `mcp_payload_tokens` — the bundle-read cost; the replacement for the raw
     test output. The fairness rule compares this against
     `raw_test_output_tokens`.
   - `raw_test_output_tokens` — the in-session pytest-output cost (control
     only). This is the `size(2)` ceiling the spike must instrument.

   All four are optional. Legacy v1 rows omit them; the aggregator treats
   missing as "not applicable" (the field did not exist when the row was
   written). No backfill.

3. **`schema_version` front-matter** bumped from `"v1"` to `"v2"`. The
   aggregator continues to read v1 rows for back-compat; v2 rows carry the new
   fields.

## Migration v2 → v3 (Phase 4.5 runner)

**Driver:** the §13 efficacy series needs per-row seat outcome, funnel
position, and run provenance. Before v3 the runner wrote `branch` as a
hardcoded string (not the branch the run executed against), and the
`executor` / `test-designer` seats emitted **no** `runs.jsonl` rows at all —
only planner and plan-reviewer calls were recorded.

All additions are optional for readers; v1/v2 rows are unchanged and the
aggregator accepts `schema_version` in `{v1, v2, v3}`.

1. **New per-invocation fields on `runs.jsonl`** (rows with `role` in the
   seat enum):

   | key                 | type   | note |
   |---                  |---     |---   |
   | `seat_outcome`      | enum   | `ok` / `tool-error` / `empty-envelope` / `parse-fail` / `transient-exhausted` / `dry-run`. Artifact state of the call; `is_error` alone cannot distinguish "droid reported an error" from "no envelope was produced". |
   | `stderr_path`       | string | path to the captured stderr log |
   | `envelope_raw_bytes`| int    | size of the envelope file on disk (0 = missing/empty) |
   | `started_at`        | ISO-8601 | wall-clock start of the invocation |
   | `finished_at`       | ISO-8601 | wall-clock end of the invocation |
   | `run_label`         | string | experiment arm / operator label (`--run-label`; defaults to the run_id) |
   | `chunk_id`          | string | set on per-chunk seats (`test-designer`, `executor`); absent on plan-level seats |
   | `phase_step`        | enum   | `plan` / `plan-review` / `test-design` / `execute` |
   | `verdict_text_first_240` | string | existing key, carried on the in-memory `RunRecord`; emitted only when non-empty. The Phase 4.5 runner does not yet populate it (the reviewer verdict is parsed after the row is appended). |

   `branch` is now the actual `git branch --show-current` of the framework
   checkout.

2. **Flattened provenance keys**, stamped on every v3 row (runs, run
   summary, dispositions) so queries need no JSON paths:
   `framework_sha`, `framework_branch`, `pilot_root`, `pilot_head`,
   `plan_sha256`, `plan_round`, `flag_unattended`, `flag_force_accept`,
   `flag_verify_mode`, `flag_dry_run`, `flag_skip_reconcile`. Git values are
   `"unknown"` / `"detached"` when they cannot be read.

3. **New `role="run"` summary row in `runs.jsonl`** — exactly one per runner
   process, emitted on every exit path (normal return, `SystemExit`,
   uncaught exception). Seat-oriented queries must filter it out
   (`role != "run"`); `model_id` / `provider` / `family` are `"(n/a)"`.

   | key                     | type     | note |
   |---                      |---       |---   |
   | `run_id`                | string   | `r-run-<epoch-ms>` |
   | `phase`, `branch`       | string   | as for seat rows |
   | `exit_code`             | int      | process exit code |
   | `run_status`            | string   | final `RunStatus` value |
   | `status_message`        | string   | last operator-facing status text |
   | `reached_phase_step`    | enum     | furthest step reached: `start` / `planner` / `plan-review` / `reconcile` / `chunking` / `chunk-execution` / `test-design` / `red-gate` / `execute` / `verify-green` / `validate` / `completed` |
   | `findings_total`        | int      | plan-level findings count |
   | `findings_by_severity`  | object   | `{severity: count}` |
   | `plan_reviewer_verdicts`| object[] | `{model_id, verdict, bound_to_plan}`; `bound_to_plan` is whether the verdict's plan_sha256 matches the final plan |
   | `chunk_statuses`        | object[] | `{chunk_id, status, gate_decision, retry_count}` |
   | `force_accept_disposition` | string | the operator disposition text, if a force-accept fired |
   | + provenance keys       |          | see (2) |

4. **`dispositions.jsonl` v3 rows for force-accept.** A `--force-accept`
   override at the reconcile gate writes one row per overridden open
   `blocker|high` finding with `disposition="overridden"` (new enum value).
   `disposition_reason` is the operator's `--force-accept-reason` (or
   `"(not provided)"`), `disposition_model_id` is `"(operator)"`,
   `disposition_commit_sha` is `pilot_head`. Rows also carry `severity`,
   `category`, `source_run_id`, `source_model_id`, `run_label`,
   `framework_sha`, `plan_sha256`. Without these rows, reviewer precision
   (upheld vs. overridden) is not measurable from telemetry.

5. **`schema_version`** is `"v3"` on all rows written by the Phase 4.5
   runner. `findings.jsonl` rows written by the runner remain `"v2"`.

6. **Two new optional `findings.jsonl` fields**, `plan_section` and
   `risk_if_ignored`. Both are strings, both are optional, and both are
   absent on every row written before the plan-review loop landed;
   readers must treat missing as `""`. `schema_version` stays `"v2"` for
   `findings.jsonl` because the change is additive only.

   The reason they exist: plan reviewers emit a `claim` (the plan's own
   assertion, which the reviewer is *challenging*) alongside
   `risk_if_ignored` (the defect). Storing only `claim` — as
   `raw_text_first_240` did — makes a finding read as an approval when
   rendered, and leaves the actionable text nowhere on disk. No backfill;
   older rows keep `raw_text_first_240` as their only prose.


## plan_lint_runs.jsonl — one row per `plan-lint.py` invocation

Tool-specific telemetry for the deterministic pre-review tier
(`tools/plan-lint.py`). This file is separate from `runs.jsonl` because
plan-lint is a tool, not an agent run — it has no `model_id`, `role`,
`family`, or token counts. Shoehorning tool rows into `runs.jsonl` would
pollute the semantics of every downstream consumer (aggregate.py, the
calibration study). The file is git-ignored (see `.gitignore`).

| key                | type     | required | note |
|---                 |---       |---       |---   |
| `schema_version`   | string   | yes      | `"v2"` |
| `ts`               | ISO-8601 | yes      | time the row was appended |
| `tool`             | string   | yes      | `"plan-lint"` |
| `plan_path`        | string   | yes      | path to the plan markdown file |
| `plan_content_sha`  | string   | yes      | SHA-256 of the plan file content |
| `verdict`          | string   | yes      | `PASS` / `BLOCK` / `ERROR` |
| `finding_count`    | int      | yes      | number of findings (warnings + blocks) |
| `duration_ms`      | int      | yes      | wall clock duration in milliseconds |
