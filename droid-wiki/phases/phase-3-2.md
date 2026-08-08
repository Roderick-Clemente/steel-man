# Phase 3.2 — Evidence Provider Build

Phase 3.2 built the local evidence provider: a neutral producer that runs the deterministic tier (pytest, locked-hash check, and a security scan) once and emits a compact, signed `EvidenceBundle` that validators and the orchestrator consume instead of re-running pytest in-session. This is the zero-CI milestone from the run prompt.

## Key source files

| File | Purpose |
|---|---|
| `/Users/factory/work/adversarial-sprint-dev/phase-3.2/BUILD-NOTES.md` | What was built, how to run it locally, and demo results |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.2/ASSUMPTIONS.md` | Decisions and gaps where the spec did not fully determine what to build |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/bundle_schema_v1.json` | Frozen EvidenceBundle v1 JSON Schema |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/local_backend.py` | Local backend adapter: runs verify-green + pytest + Bandit, normalizes to bundle, signs it |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/consumer.py` | Validator and orchestrator consumers |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/token_accounting.py` | Fairness-rule instrumentation comparing raw test output tokens vs bundle payload tokens |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/security_allowlist.json` | Curated allowlist for `(rule_id, file, line)` security findings |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-bundle.json` | Demo signed bundle for the locked `/profile` model chunk |
| `/Users/factory/work/adversarial-sprint-dev/telemetry/SCHEMA.md` | Schema v1→v2 bump: added `test-designer` role and MCP token fields |

## What was built

### Components

- **`/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/local_backend.py`** — Runs `/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/verify-green.py` (locked-hash check), pytest (structured results), and Bandit (new-vs-baseline + allowlist), then normalizes everything into the bundle and signs it with HMAC-SHA256.
- **`/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/consumer.py`** — Two consumers:
  - `validate`: verifies the signature and returns an evidence verdict (`ACCEPT` / `REJECT`).
  - `gate`: cross-checks `locked_test_sha_observed` against the lock manifest and fails closed on mismatch.
- **`/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/token_accounting.py`** — Measures the fairness rule: `raw_test_output_tokens` (what the validator would have read in-session) vs `mcp_payload_tokens` (the bundle it reads instead).
- **`/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/bundle_schema_v1.json`** — Compact by construction: failures are `{nodeid, assertion_line, short_message}`, never full tracebacks. Security findings only carry new findings, not the 294 baseline items.
- **`/Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/security_allowlist.json`** — Scoped to specific `(rule_id, file, line)` tuples, learned from the gitleaks/SPLIT_CLIENT_KEY false-fail.

### Demo artifacts

- `/Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-bundle.json` — 919 bytes, signed, 103 tests passed, 0 failures, 0 new security findings.
- `/Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-raw-pytest.txt` — Raw output of the locked test (what the bundle replaces).
- `/Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-raw-pytest-full-suite.txt` — Raw output of the full regression suite.
- `/Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-raw-pytest-combined.txt` — Combined output the Phase 3 validator actually consumed.
- `/Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-token-accounting.json` — Fairness rule result.
- `/Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/bandit-baseline.json` — Baseline Bandit scan (294 pre-existing findings) for new-vs-baseline comparison.

## Demo result

Running the locked `/profile` model chunk end-to-end:

- **Bundle:** 919 bytes, ~229 tokens. 103 passed, 0 failed, 0 new security findings.
- **Validator consumer:** `ACCEPT` — signature valid, 103 passed, 0 failed, suite exit 0. No pytest re-run.
- **Orchestrator gate:** `PASS` — `locked_test_sha_observed` matches the lock manifest (`8041e607…`), suite green.
- **Token accounting:** fairness rule **holds** — bundle read (229 tokens) < combined raw test output (511 tokens) = **55.2% saving** on the test-output-read slice of the validator run.

### Important nuance

For the locked test alone (3 tests, all passing), raw pytest output is so compact that the bundle is slightly larger. The win materializes when the full regression suite is included, because raw output scales with test count while the bundle does not. This is directional data, not a definitive H-CI result; the real experiment needs multiple runs with provider tokenizers.

## How to run it locally

```bash
export EVIDENCE_SIGNING_KEY="your-secret-key-here"

# Produce the bundle
$PYTHON /Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/local_backend.py \
  --pilot-root $PILOT \
  --framework-root /Users/factory/work/adversarial-sprint-dev \
  --test-file test/test_profile_model.py \
  --lock-file /Users/factory/work/adversarial-sprint-dev/phase-1/locks/test/test_profile_model.py.lock.json \
  --output /Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-bundle.json \
  --python $PYTHON --full-suite --security-scan \
  --security-allowlist /Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/security_allowlist.json \
  --security-baseline /Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/bandit-baseline.json

# Validator consumes the bundle
$PYTHON /Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/consumer.py validate \
  --bundle /Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-bundle.json

# Orchestrator gate
$PYTHON /Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/consumer.py gate \
  --bundle /Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-bundle.json \
  --lock-file /Users/factory/work/adversarial-sprint-dev/phase-1/locks/test/test_profile_model.py.lock.json

# Token accounting
$PYTHON /Users/factory/work/adversarial-sprint-dev/phase-3.2/evidence/token_accounting.py \
  --raw-output /Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-raw-pytest-combined.txt \
  --bundle /Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-bundle.json \
  --output /Users/factory/work/adversarial-sprint-dev/phase-3.2/build-evidence/chunk1-token-accounting.json
```

## Key assumptions and decisions

- **Signature scheme:** HMAC-SHA256 with a key from `EVIDENCE_SIGNING_KEY`. If the env var is unset, the backend generates a random key and warns that the signature is valid only for same-process verification. The consumer refuses to verify without an explicit key. A hardcoded default key was caught by a cross-family reviewer as forgeable and fixed.
- **Token estimation:** `chars // 4` as a proxy, sufficient for directional comparison. The real experiment should use provider tokenizers.
- **Bandit only:** Semgrep was recommended but not installed; Bandit was available and covers Python. The interface is scanner-agnostic, so Semgrep can be added later behind the same contract.
- **New security findings only:** The 294 baseline Bandit findings are excluded from the bundle to keep it compact. The gate keys on new-vs-baseline.
- **Full-suite flag:** When set, the `tests` section carries the full regression suite results, not just the locked test. This matches what Phase 3 validators actually consumed.
- **No MCP wiring:** Local mode only. The Harness MCP inbound edge is explicitly out of scope for this run.

## What remains

- Harness backend (flavor b): pull native tests/coverage/SARIF via Harness MCP.
- Full N-run H-CI experiment comparing local vs in-session evidence.
- MCP wiring for inbound and outbound edges.
- Phase 3.3 visual tier, which inherits the same bundle abstraction.
- Framework-repo dogfood: run the framework's own deterministic assets through the same bundle contract.
- Semgrep as a second scanner behind the same interface.
