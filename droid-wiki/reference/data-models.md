# Data models

Two groups of shapes appear in this repository, and they have very different standing.

- **Platform shapes** — what `droid` 0.186.0 actually emits. Observed and captured in `phase-0/evidence/`.
- **Method shapes** — the schemas `PRD.md` specifies for the plugin. Written down, agreed, **not yet built**.

Nothing in the second group has an implementation anywhere in the repository. Treat those field lists as a spec to build against, not as a description of running code.

## Platform shapes

### `droid exec -o json` result envelope

One JSON object per run, on stdout. A real capture, `phase-0/evidence/probe-4/reverify/raw/canary-run.json`, unmodified:

```json
{"type":"result","subtype":"success","is_error":false,"duration_ms":6112,"num_turns":2,
 "result":"`ls tests` shows a single entry: `locked_test.py`. No files were modified.",
 "session_id":"87da9701-e807-448d-90d3-71e83c1ca0ce",
 "usage":{"input_tokens":4,"output_tokens":193,"cache_read_input_tokens":15786,
          "cache_creation_input_tokens":15971,"factory_credits":45023}}
```

| Key | Type | Notes |
|---|---|---|
| `type` | string | `result` |
| `subtype` | string | `success` observed |
| `is_error` | bool | run-level only; see the warning below |
| `duration_ms` | int | wall clock |
| `num_turns` | int | `0` on a permission denial that killed the run |
| `session_id` | string | UUID; joins to `transcript_path` and to hook payloads |
| `result` | string | the agent's final text |
| `usage.input_tokens` | int | |
| `usage.output_tokens` | int | |
| `usage.cache_read_input_tokens` | int | |
| `usage.cache_creation_input_tokens` | int | |
| `usage.thinking_tokens` | int | present on reasoning runs |
| `usage.factory_credits` | int | per run, which is what makes per-role cost attribution work without Missions |

**The envelope carries no model field.** Checked across all nine Probe 2 runs. A caller that reads only `-o json` cannot tell which model ran, which is the gap that pushed model verification into the session store and then into a hook. See [Probe 2](../probes/probe-2-fallback-safety.md).

**Run-level `is_error: false` does not mean the work happened.** In Probe 2's T5 both tool calls were denied by a hook, and the envelope still reported `num_turns=3`, `is_error=false`, exit 0. Assert on the hook's own log and on per-tool `is_error` inside the transcript, never on the envelope alone. This is the silent-green shape again: failed work reporting success.

### Session transcript JSONL

Path form:

```text
~/.factory/sessions/<cwd-slug>/<session-id>.jsonl
```

The slug is the working directory with separators flattened, e.g. `-private-tmp-probe-4-repo`. The file is one JSON object per line. The fields Phase 0 read:

| Field | Notes |
|---|---|
| `message.modelId` | resolved model, **per message** — a mid-run change would be visible |
| `message.reasoningEffort` | e.g. `high`; per message, same property |
| startup context block | the environment block injected before the first turn carries a `Model:` line, e.g. `Model: GPT-5.4 Mini` |
| tool call entries | the tool name and its input |
| `tool_result` entries | carry `is_error` per call — the only place a denied tool call is visible |

Two consequences. First, `message.modelId` is the answer to "which model actually ran," and reading it is undocumented for this purpose. Second, the same file is readable by any later agent with `Grep`, which makes it a confidentiality surface as well as an evidence one — see [Security](../security.md).

### Hook input payload

Documented under [Configuration → hook payload contract](./configuration.md#hook-payload-contract). Summarised here because it is the join key between the other two shapes: the payload's `session_id` matches the envelope's, and its `transcript_path` points at the JSONL.

### Hook logs

Each rig writes its own JSONL, one object per invocation, to a path the rig chooses — deliberately outside `.factory/`, so the orchestrator owns the record rather than the platform. The shapes are per-rig, not a platform contract.

Locked-test guard, `phase-0/evidence/probe-4/reverify/rig/hook-protect2.py` → `raw/hooklog-protect2.jsonl`:

```json
{"saw_command": true, "saw_file_path": false, "tool_name": "Execute",
 "verdict": "allow", "why": null, "ts": "…", "session_id": "…"}
```

`saw_file_path: false` next to `saw_command: true` is the A4 failure condition recorded from inside the guard: the payload carried no path, so a path-only guard had nothing to match on.

Canary, `rig/hook-canary.py` → `raw/hooklog-canary.jsonl`. Its job is proving hooks fire at all, so it logs registration facts rather than verdicts: `hook_event_name`, `tool_name`, `session_id`, `cwd`, `permission_mode`, `transcript_path`, `tool_input_keys` (sorted), `file_path`.

Risk observer, `phase-0/evidence/probe-8/rig/hook-observe.py` → `raw/hooklog-observe-T7.jsonl`. Pairs the model's self-declared label with the command it labelled:

```json
{"command": "cd /private/tmp/probe-8/repo && echo 'note: probe 8' >> notes.txt && cat notes.txt",
 "declared_riskLevel": "medium",
 "declared_reason": "Creates/appends to a new file notes.txt in the project directory; easily reversible.",
 "file_path": null, "permission_mode": "auto-low", "tool_name": "Execute",
 "session_id": "e94d3365-f0db-4dab-8ebe-60af6b7a1204", "ts": "2026-08-02T23:59:44"}
```

Plugin canary, `phase-0/evidence/probe-6/plugin/hooks/canary.py`, adds `plugin_root_env` for the sole purpose of catching `DROID_PLUGIN_ROOT`. It caught it. The committed copy of its log at `phase-0/evidence/probe-6/raw/hooklog-plugin-canary.jsonl` is empty because it captures the post-uninstall state — zero invocations, which was itself the uninstall assertion. The fired line is quoted in `phase-0/evidence/probe-6/README.md`.

All rigs write with `sort_keys=True`, so key order in these files is alphabetical and not meaningful.

## Method shapes, specified in `PRD.md`

### Finding

The unit of adversarial review output, from §5.3:

```json
{
  "id": "F-001",
  "severity": "blocker|high|medium|low",
  "category": "semantic|factual|test-gap|scope|operability|style",
  "plan_section": "string",
  "claim": "string",
  "evidence": ["path:line or command/result"],
  "recommended_change": "string",
  "risk_if_ignored": "string",
  "status": "open|accepted|rejected|superseded",
  "disposition_rationale": "string"
}
```

`evidence` being a required array is the load-bearing part: a finding without a path, line, or command result is an opinion. Convergence is defined against these fields — no `blocker` or `high` may remain `open`, and every `factual`, `semantic`, `scope`, and `test-gap` finding needs a recorded disposition.

The PRD is candid that `status` and `disposition_rationale` are **not machine-verifiable** — "accepted" is irreducibly a judgment call. It draws the design conclusion explicitly: keep the schema light, because a skipped ledger is worse than none.

### RED record

The evidence that a test failed for the right reason, from §5.4:

```json
{
  "behavior": "observable outcome under test",
  "test_id": "path::test_name",
  "test_sha256": "hash of locked test content",
  "command": "exact test command",
  "expected_failure": "assertion and mismatch expected before implementation",
  "exit_code": 1,
  "observed_failure": "captured assertion output",
  "classification": "behavioral-red"
}
```

`test_sha256` is the field invariant #5 acts on: the RED hash must equal the GREEN hash, and any mutation invalidates the gate. `classification` exists to separate a valid `behavioral-red` from the invalid kinds — syntax and import errors, missing fixtures, unavailable services, empty test selection, timeouts, and unrelated assertion failures.

### Chunk

§5.5 defines a chunk by required content rather than a JSON schema, so these are fields to design, not keys to copy:

- one bounded outcome and observable success criteria
- dependencies and semantic interfaces, not merely overlapping file paths
- allowed implementation files and locked test files
- exact RED, focused GREEN, full-suite, lint, and build commands
- expected outputs or pass conditions
- risk level and human-review trigger
- rollback method
- retry and escalation behavior
- standardized result block

"Allowed implementation files and locked test files" is where this connects to the platform: the locked list is the manifest a `PreToolUse` guard enforces, and Probe 4 showed that enforcement has to cover `Execute` as well as `Edit`.

### Run artifact layout

§9. Every run writes to `.factory/adversarial-sprints/<run-id>/` or another configured artifact path:

```text
run.json                   # state, source commit, budgets, role/model map
goal.md                    # approved objective and boundaries
plan-v1.md ... plan-vN.md  # hashed plan history
findings.jsonl             # findings and dispositions
tests.json                 # locked test IDs, hashes, expected RED signatures
chunks/                    # independently executable chunk specs
evidence/                  # commands, exit codes, stdout/stderr, timestamps
validation/                # per-chunk verdicts and reasons
RESULTS.md                 # human-readable rollup and retrospective
```

`run.json` is the resumable state machine. A resumed run rechecks source commit, working-tree state, plan and test hashes, resolved model assignments, and completed gates before continuing; stale state pauses rather than replaying mutations.

Secrets and raw chain-of-thought are never written to artifacts, and command output is filtered for secrets before persistence.

Phase 0 used "another configured artifact path" — `phase-0/evidence/` — because `.factory/` is gitignored here and evidence written there would be invisible to git. The reasoning is in [Architecture](../overview/architecture.md).

## Implementation status

| Shape | Status |
|---|---|
| `-o json` result envelope | platform, observed across every probe |
| Session transcript JSONL | platform, observed; undocumented for model attribution |
| Hook input payload | platform, observed |
| Hook logs | implemented, as probe rigs |
| Finding | specified in `PRD.md` §5.3, not built |
| RED record | specified in `PRD.md` §5.4, not built |
| Chunk | specified in `PRD.md` §5.5 as required content, not built |
| Run artifact layout | specified in `PRD.md` §9, not built |

`PRD.md` §8 nominates `schemas/finding.schema.json` and `schemas/red-green.schema.json` as the two schemas that ship in v1; `run.schema.json` was deliberately deferred until the state machine stabilises.

## EvidenceBundle v1 (built, Phase 3.2)

The compact signed JSON artifact that validators consume instead of re-running pytest. Schema at `phase-3.2/evidence/bundle_schema_v1.json`.

| Field | Type | Notes |
|---|---|---|
| `bundle_schema_version` | string | `"v1"`, frozen |
| `producer` | enum | `local` or `harness` |
| `change.commit_sha` | string | the change under review |
| `change.locked_test_sha_observed` | string | SHA-256 the provider actually hashed and ran |
| `tests.passed/failed/skipped` | int | counts |
| `tests.suite_exit_code` | int | pytest exit code |
| `tests.failures[]` | array | `{nodeid, assertion_line, short_message}` — never full tracebacks |
| `coverage` | object | optional: `lines_pct`, `changed_lines_covered` |
| `security.findings[]` | array | optional: `{rule_id, severity, file, line, short_message, is_new, scope}` |
| `provenance` | object | `producer_run_id`, `started_at`, `finished_at`, `tool_versions` |
| `signature` | object | `algorithm: "HMAC-SHA256"`, `value`, `key_id` |

Compact by construction: failure records are one-liners, never full tracebacks. Security findings only carry `is_new=true` entries (baseline debt is excluded).

## Telemetry SCHEMA v2 (built, Phase 3.2)

The data schema for the evaluation's telemetry files. Full text at `telemetry/SCHEMA.md`. Bumped from v1 to v2 in Phase 3.2.

New fields on `runs.jsonl` (all optional, non-breaking for v1 rows):

| Field | Type | Notes |
|---|---|---|
| `evidence_source` | enum | `in-session` (control) or `bundle` (treatment) — marks which H-CI arm |
| `mcp_call_tokens` | int | tokens of the MCP evidence-pull request (treatment only) |
| `mcp_payload_tokens` | int | tokens of the bundle that entered agent context (treatment) |
| `raw_test_output_tokens` | int | tokens of the raw pytest output being replaced (control) |

The `role` enum was also extended with `test-designer` (KI-4 fix — Phase 3 data already used it, the schema just didn't list it).

## Related

- [Configuration](./configuration.md) — the settings that produce these shapes
- [Dependencies](./dependencies.md) — the version every observation is scoped to
- [Probe 2](../probes/probe-2-fallback-safety.md) — the missing model field and the transcript workaround
- [Probe 4](../probes/probe-4-hook-blocking.md) — the payload and hook log shapes in context
- [Probes](../probes/index.md) · [Glossary](../overview/glossary.md)
