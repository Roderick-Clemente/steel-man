# Phase 3.2 — the evidence provider

**Phase 3.1 proved what breaks when you remove an invariant. Phase 3.2
attacks the cost structure: 84% of Phase 3's token spend was the
cross-family validation panel re-running pytest and reading raw stdout.
The evidence provider externalizes that deterministic tier into a compact,
signed bundle that validators consume instead of re-running tests.**

The core design decision: **CI is a mode, not a dependency.** The loop
must run with zero CI. So the primitive is an abstract evidence-provider
interface with a local backend as the default, and Harness as one
interchangeable backend behind the same interface.

## What was built

| Component | What it does |
|---|---|
| `evidence/bundle_schema_v1.json` | Frozen EvidenceBundle v1 JSON Schema. Compact by construction: failures are `{nodeid, assertion_line, short_message}`, never full tracebacks. |
| `evidence/local_backend.py` | Runs `verify-green.py` (locked-hash check), pytest (structured results), Bandit (security, new-vs-baseline + allowlist), normalizes to bundle, signs with HMAC-SHA256. Uses `os.urandom(32)` when key unset. |
| `evidence/consumer.py` | `ValidatorConsumer` (verify signature, check tests, reach evidence verdict) + `OrchestratorGate` (cross-check `locked_test_sha_observed` against lock manifest, fail closed on mismatch). |
| `evidence/token_accounting.py` | Fairness rule instrumentation: measures `raw_test_output_tokens` (control) vs `mcp_payload_tokens` (treatment). |
| `evidence/security_allowlist.json` | Curated allowlist scoped to `(rule_id, file, line)` tuples. |
| `telemetry/SCHEMA.md` | Bumped v1→v2: added `test-designer` role, `evidence_source` / MCP token fields for H-CI fairness. |

## Demo result

On the locked `/profile` model chunk (chunk 1):

- **Bundle:** 919 bytes (~229 tokens). 103 passed, 0 failed, 0 new security
  findings. Signed with HMAC-SHA256.
- **Validator consumer:** `ACCEPT` — signature valid, 103 passed, 0 failed.
  No pytest re-run.
- **Orchestrator gate:** `PASS` — `locked_test_sha_observed` matches the
  lock manifest.
- **Token accounting:** fairness rule **holds** at combined-output scope —
  bundle (229 tokens) < combined raw test output (511 tokens) = **55.2%
  saving** on the test-output-read slice.

**Important nuance:** for the locked test alone (3 tests), the raw output is
already so compact (222 tokens) that the bundle (229 tokens) is slightly
*larger*. The win materializes when the full regression suite (103 tests) is
included, because raw output scales with test count while the bundle does
not. This is directional data, not a definitive H-CI result.

## The orchestration gap

During Phase 3.2, the cross-family review process was discovered to be ad
hoc — run by an AI agent manually executing `droid exec` commands instead
of by a scripted pipeline. The `tools/orchestrate-review.py` script (17.6KB)
was built to solve this and **ran with partial success**: 12 telemetry rows
in `runs.jsonl`, 10 from orchestrated runs with real decisions (ACCEPT,
REJECT, ACCEPT-WITH-NITS, ERROR, UNKNOWN).

Residual flakiness: ERROR/UNKNOWN rows on some gemini runs (provider API
failures, not empty-envelope bugs), and a non-hermetic stray-write check
that STOPs on pre-existing dirty-tree paths (false positive). The script
also bypasses both the adapter shim (`tools/adapters/factory.py`) and the
model-discipline wrapper (`tools/run-with-model.sh`) despite citing both
in its docstring.

This gap triggered `tools/OPERATING-RULES.md` §8 (scope-shift rule) —
written retroactively as a lesson learned.

## The H-CI experiment (designed, not yet run)

**Hypothesis (H-CI):** routing deterministic evidence through a provider
reduces average token cost at equal acceptance quality.

The experiment: same locked chunk, same models/prompts/diff, only the
evidence source changes. Run N times with provider tokenizers. Phase 3 =
control arm (in-session pytest); 3.2 bundle = treatment arm.

**Fairness rule (mandatory):** the bundle enters the validator's context
and costs input tokens to read. The win is real only if
`tokens(bundle read) < tokens(raw test output it replaces)`. Offloading is
not free.

**Predicted outcome:** partial win. The validator still pays for diff+spec
read and verdict reasoning — CI only moves the test-output-read slice. The
ceiling on H-CI's saving is the size of that slice.

A null result is valid data (PRD §13): if the bundle doesn't save tokens,
the bigger lever is panel size and validator context discipline, not
evidence externalization.

## Security lens: three lessons from the first real Harness run

1. **Gate on NEW findings vs a baseline**, not total history. Gitleaks
   failed the build on legacy debt while its own report said
   `newIssuesCount: 0`.
2. **The scanner is not an oracle.** Gitleaks flagged `SPLIT_CLIENT_KEY`
   (a public-by-design client-side key) as `generic-api-key` on pure
   entropy. The security tier needs a curated allowlist scoped to the
   specific known-public value.
3. **Diff-scoped vs history-scoped are both valid at their scope.** The
   diff/new scope gates the merge; the history scope is a standing baseline
   report, never a merge blocker on its own.

## What remains (follow-ons)

1. **Harness backend** (SPIKE §2.3 flavor b): pull native tests/coverage/
   SARIF via Harness MCP. Proves the interface generalizes.
2. **Full N-run H-CI experiment** with provider tokenizers.
3. **MCP wiring**: inbound (Harness MCP) and outbound (git push/merge
   trigger).
4. **3.3 visual/behavioral tier**: extends the same interface with
   screenshot/DOM evidence.
5. **Framework-repo dogfood**: run the framework's own deterministic
   assets through the same bundle contract.
6. **Semgrep** as a second scanner behind the same interface (Bandit is
   Python-only).

## Telemetry schema migration (v1 → v2)

The SCHEMA bump added:
- `test-designer` to the `role` enum (KI-4 fix from Phase 3).
- `evidence_source` — `in-session` (control) vs `bundle` (treatment) for
  H-CI A/B attribution.
- `mcp_call_tokens` / `mcp_payload_tokens` / `raw_test_output_tokens` —
  the fairness-rule instrumentation fields.

All new fields are optional. Legacy v1 rows omit them. No backfill needed.
