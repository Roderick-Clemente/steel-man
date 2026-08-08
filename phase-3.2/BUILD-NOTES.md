# Phase 3.2 — Build Notes

## What was built

The **local evidence provider** — the zero-CI milestone from RUN-PROMPT.md
steps 1–3 + 5. A neutral producer runs the deterministic tier (pytest + locked
hash + security scan) once and emits a compact signed `EvidenceBundle` that
validators and the orchestrator consume instead of re-running pytest in-session.

### Components

| File | What it does |
|---|---|
| `phase-3.2/evidence/bundle_schema_v1.json` | Frozen EvidenceBundle v1 JSON Schema (SPIKE §2.1). Compact by construction: failures are `{nodeid, assertion_line, short_message}`, never full tracebacks. |
| `phase-3.2/evidence/local_backend.py` | Local backend adapter (SPIKE §2.2, flavor a). Runs verify-green.py (locked-hash check → `locked_test_sha_observed`), pytest (structured results), Bandit (security lens, new-vs-baseline + allowlist), normalizes to the bundle, signs it (HMAC-SHA256). |
| `phase-3.2/evidence/consumer.py` | Validator + orchestrator consumers (SPIKE §5, §4.1). `validate` — verifies signature, checks test results, reaches evidence verdict. `gate` — cross-checks `locked_test_sha_observed` against the lock manifest, fails closed on mismatch. |
| `phase-3.2/evidence/token_accounting.py` | §3.2 fairness rule instrumentation. Measures `raw_test_output_tokens` (control) vs `mcp_payload_tokens` (treatment) so the ceiling is measured, not assumed. |
| `phase-3.2/evidence/security_allowlist.json` | Curated allowlist scoped to specific `(rule_id, file, line)` tuples (SPIKE §4.4 lesson 2 — the gitleaks/SPLIT_CLIENT_KEY false-fail). |
| `telemetry/SCHEMA.md` | Bumped v1→v2: added `test-designer` role (KI-4 fix), `evidence_source` / `mcp_call_tokens` / `mcp_payload_tokens` / `raw_test_output_tokens` fields for the H-CI fairness rule. Migration note included. |

### Demo artifacts (`phase-3.2/build-evidence/`)

| File | What it is |
|---|---|
| `chunk1-bundle.json` | The signed EvidenceBundle for the locked `/profile` model chunk (chunk 1). 103 tests passed, 0 failures, 0 new security findings. 919 bytes. |
| `chunk1-raw-pytest.txt` | Raw pytest output for the locked test (3 tests, `-v`). The in-session cost being replaced. |
| `chunk1-raw-pytest-full-suite.txt` | Raw pytest output for the full regression suite (103 tests, `-q`). |
| `chunk1-raw-pytest-combined.txt` | Combined raw output (locked + full suite) — what the Phase 3 validator actually consumed. |
| `chunk1-token-accounting.json` | Fairness rule result: bundle 229 tokens < combined raw 511 tokens (55.2% saving on the test-output-read slice). |
| `bandit-baseline.json` | Baseline Bandit scan (294 pre-existing findings, excl .venv) for new-vs-baseline comparison. |

## How to run it locally (zero CI)

```bash
# Paths
FRAMEWORK=/Users/factory/work/adversarial-sprint-dev-3.2-build
PILOT=/Users/factory/work/quantum-bank--llms-txt-pilot
PYTHON=$PILOT/.venv/bin/python

# 1. Set the signing key (required for both backend and consumer)
export EVIDENCE_SIGNING_KEY="your-secret-key-here"

# 2. Produce the bundle (locked-hash check + pytest + security scan)
cd $FRAMEWORK
$PYTHON phase-3.2/evidence/local_backend.py \
  --pilot-root $PILOT \
  --framework-root $FRAMEWORK \
  --test-file test/test_profile_model.py \
  --lock-file phase-1/locks/test/test_profile_model.py.lock.json \
  --output phase-3.2/build-evidence/chunk1-bundle.json \
  --python $PYTHON \
  --full-suite \
  --security-scan \
  --security-allowlist phase-3.2/evidence/security_allowlist.json \
  --security-baseline phase-3.2/build-evidence/bandit-baseline.json

# 2. Validator consumes the bundle (no pytest re-run, requires EVIDENCE_SIGNING_KEY)
$PYTHON phase-3.2/evidence/consumer.py validate \
  --bundle phase-3.2/build-evidence/chunk1-bundle.json

# 3. Orchestrator gate (locked-sha cross-check, requires EVIDENCE_SIGNING_KEY)
$PYTHON phase-3.2/evidence/consumer.py gate \
  --bundle phase-3.2/build-evidence/chunk1-bundle.json \
  --lock-file phase-1/locks/test/test_profile_model.py.lock.json

# 4. Token accounting (fairness rule)
$PYTHON phase-3.2/evidence/token_accounting.py \
  --raw-output phase-3.2/build-evidence/chunk1-raw-pytest-combined.txt \
  --bundle phase-3.2/build-evidence/chunk1-bundle.json \
  --output phase-3.2/build-evidence/chunk1-token-accounting.json
```

## Demo result

The end-to-end demo on the locked `/profile` model chunk (chunk 1):

- **Bundle:** 919 bytes (~229 tokens). 103 passed, 0 failed, 0 new security
  findings. Signed with HMAC-SHA256.
- **Validator consumer:** `ACCEPT` — signature valid, 103 passed, 0 failed,
  suite exit 0. No pytest re-run.
- **Orchestrator gate:** `PASS` — `locked_test_sha_observed` matches the lock
  manifest (`8041e607…`), suite green.
- **Token accounting:** fairness rule **holds** — bundle read (229 tokens) <
  combined raw test output (511 tokens) = **55.2% saving** on the
  test-output-read slice (2) of the validator run.

### Important nuance

For the locked test alone (3 tests, all passing), the raw pytest output is
already so compact (222 tokens) that the bundle (229 tokens) is slightly
**larger** — the fairness rule does not hold at that scope. The win
materializes when the full regression suite (103 tests) is included, because
raw output scales with test count while the bundle does not. This is
directional data, not a definitive H-CI result: the real experiment needs
multiple runs with provider tokenizers, and the SPIKE's own prediction was a
"partial win" with the possibility of a null result (§3.5).

## What remains (follow-on, explicitly out of scope for this run)

1. **Harness backend** (SPIKE §2.3 flavor b): pull native tests/coverage/SARIF
   via Harness MCP. Proves the interface generalizes beyond "just run our
   script."
2. **Full N-run H-CI experiment** (SPIKE §3): run the same locked chunk through
   local vs in-session evidence, N times, same models/prompts/diff. Only the
   evidence source changes. Use provider tokenizers for exact token counts.
3. **MCP wiring**: the inbound edge (Harness MCP) and the outbound trigger
   (git push/merge). Local mode has no inbound edge; the bundle is produced
   in-process.
4. **3.3 visual tier**: extends the same interface with visual/behavioral
   evidence.
5. **Framework-repo dogfood** (SPIKE §7): run the framework's own deterministic
   assets through the same bundle contract. Separate target, must not feed the
   H-CI token A/B.
6. **Semgrep**: add as a second scanner behind the same interface (Bandit is
   Python-only; Semgrep is multi-language).
