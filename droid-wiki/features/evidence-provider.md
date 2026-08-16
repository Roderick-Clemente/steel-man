# Evidence provider

A neutral producer runs the deterministic tier once -- pytest, the locked-hash check, and an optional Bandit security scan -- and emits a compact, signed bundle. Validators read the bundle instead of re-running pytest in-session, saving context tokens and removing a write vector from the review seat.

## How it works

The evidence provider is a separation-of-concerns play. The producer (`tools/phase-3.2-evidence/local_backend.py`) is the only seat that executes the deterministic tier. It composes tools the repo already has -- pytest for structured test results, `phase-1/scripts/verify-green.py` for the locked-hash check, and Bandit for the security lens -- normalizes everything into a single JSON bundle, signs it, and writes it to disk. The consumer (`tools/phase-3.2-evidence/consumer.py`) verifies the signature, checks the test results, and reaches an evidence verdict (ACCEPT / REJECT / FAIL_CLOSED) without ever touching pytest.

The signing is HMAC-SHA256 under a key supplied via the `EVIDENCE_SIGNING_KEY` environment variable. If the key is absent, the backend generates a random one and warns that the signature is valid only for the same process -- any cross-agent scenario requires the key to be set explicitly.

## Bundle schema (v1)

The bundle is a flat JSON object with these top-level fields:

| Field | Contents |
|---|---|
| `bundle_schema_version` | `"v1"` |
| `producer` | `"local"` |
| `change` | `commit_sha`, `locked_test_sha_observed` |
| `tests` | `passed`, `failed`, `skipped`, `suite_exit_code`, compact `failures` records |
| `provenance` | `producer_run_id` (UUID), `started_at`, `finished_at`, `tool_versions` |
| `coverage` | Optional `lines_pct` from pytest-cov |
| `security` | Optional Bandit findings, new-vs-baseline tagged, allowlist-suppressed |
| `signature` | `algorithm` (`HMAC-SHA256`), `value`, `key_id` |

The `failures` array carries one compact record per failing test: nodeid, assertion line, and a 300-character short message. This is deliberately smaller than raw pytest output, which is the whole point.

## Token fairness accounting

The fairness rule (SPIKE section 3.2): the win is real only if `tokens(bundle read) < tokens(raw pytest output it replaces)`. `tools/phase-3.2-evidence/token_accounting.py` measures both sides using the standard chars-divided-by-4 proxy. The control arm is the raw pytest stdout a validator would have ingested in-session; the treatment arm is the bundle JSON. The module emits `saving_tokens`, `saving_pct`, and a boolean `fairness_rule_holds`. It is a proxy, not a tokenizer-accurate count, but it is sufficient to show the mechanism works directionally.

## The KI-2 fix

Validators consuming the bundle run with no `Execute` tool -- only `Read`, `Glob`, `Grep`, and `LS`. This is a preventive fix for a known issue (KI-2): a validator seat that can run shell commands has a write vector into the pilot repo, which undermines the integrity of the evidence it is supposed to be judging. Dropping `Execute` closes that vector. The orchestrator supports both arms (in-session pytest vs bundle) so the comparison is apples-to-apples, but the bundle arm is the one that removes the write vector.

## Security scan integration

With `--security-scan`, the backend runs Bandit across the pilot tree, excluding `.venv`, `.git`, and `node_modules` to avoid drowning the signal in installed-package debt. Two filters then apply:

1. **New-vs-baseline** (`diff_vs_baseline`): a finding is marked `is_new: true` if no baseline finding shares its `(rule_id, file, line)` tuple. This focuses attention on regressions, not historical debt.
2. **Curated allowlist** (`apply_allowlist`): suppresses known-acceptable findings scoped to specific `(rule_id, file, line)` tuples -- never whole files, so a real future secret in the same file still trips.

## Key source files

| File | Role |
|---|---|
| `tools/phase-3.2-evidence/local_backend.py` | Producer: runs pytest, verify-green, Bandit; normalizes and signs the bundle |
| `tools/phase-3.2-evidence/consumer.py` | Consumer: verifies signature, checks results, reaches evidence verdict; orchestrator gate variant |
| `tools/phase-3.2-evidence/token_accounting.py` | Token fairness measurement (control vs treatment arms) |
| `planning/phase-3.2/SPIKE.md` | Design rationale for the evidence provider spike |

See also [features index](index.md), [sprint-loop runner](sprint-loop-runner.md), [chunk token gates](chunk-token-gates.md).
