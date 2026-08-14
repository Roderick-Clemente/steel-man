#!/usr/bin/env python3
"""Generate telemetry/runs.jsonl rows for Phase 3.1 (degraded loop) from the
captured envelopes.

Same recipe as phase-3/gen-telemetry.py, but:
  - phase == "phase-3.1", branch == "factory/phase-3.1-degraded"
  - the test-author seat is the degraded cheap family (glm-5.2), i.e. the one
    variable under test (test-author == executor family).

Run-level numbers (num_turns, usage.*, duration_ms, is_error) are read from the
raw envelopes, not transcribed. This generator is idempotent w.r.t. the phase:
it strips any existing phase-3.1 rows from runs.jsonl and appends fresh ones,
leaving phase-3 (control) rows untouched.

KI-3 still applies: the -o json envelope does not surface providerLock/
apiProviderLock, so those are set to the known provider for the pinned model.
"""
import json
import os

EVID = os.path.join(os.path.dirname(__file__), "build-evidence")
RUNS = os.path.join(os.path.dirname(__file__), os.pardir, "telemetry", "runs.jsonl")
BRANCH = "factory/phase-3.1-degraded"
PHASE = "phase-3.1"

MODEL_META = {
    "glm-5.2": ("zhipu", "glm-family"),
    "grok-4.5": ("xai", "grok-family"),
    "gemini-3.1-pro-preview": ("google", "gemini-family"),
}

# (run_id, role, model_id, decision, envelope_filename)
# The one variable under test: the test-designer seat is glm-5.2 (zhipu) — the
# SAME cheap family as the executor. Validators stay pinned cross-family.
ROWS = [
    # ---- chunk 1, round 1 (REJECTED under unanimous-accept panel rule) ----
    ("r-phase31-c1-test-author-r1", "test-designer", "glm-5.2", None,
     "chunk1-test-author-r1-envelope.json"),
    ("r-phase31-c1-executor-r1", "executor", "glm-5.2", None,
     "chunk1-executor-r1-envelope.json"),
    ("r-phase31-c1-validator-grok-r1", "validator", "grok-4.5", "REJECT_TEST",
     "chunk1-validator-grok-r1-envelope.json"),
    ("r-phase31-c1-validator-gemini-r1", "validator", "gemini-3.1-pro-preview", "ACCEPT",
     "chunk1-validator-gemini-r1-envelope.json"),
    # ---- chunk 1, round 2 (capped test-author retry; panel ACCEPT) ----
    ("r-phase31-c1-test-author-r2", "test-designer", "glm-5.2", None,
     "chunk1-test-author-r2-envelope.json"),
    ("r-phase31-c1-executor-r2", "executor", "glm-5.2", None,
     "chunk1-executor-r2-envelope.json"),
    ("r-phase31-c1-validator-grok-r2", "validator", "grok-4.5", "ACCEPT",
     "chunk1-validator-grok-r2-envelope.json"),
    ("r-phase31-c1-validator-gemini-r2", "validator", "gemini-3.1-pro-preview", "ACCEPT",
     "chunk1-validator-gemini-r2-envelope.json"),
    # ---- chunk 2 (panel ACCEPT; note: test-author exec hit an autonomy gate
    #      AFTER writing the file — is_error true, artifact intact) ----
    ("r-phase31-c2-test-author", "test-designer", "glm-5.2", None,
     "chunk2-test-author-envelope.json"),
    ("r-phase31-c2-executor", "executor", "glm-5.2", None,
     "chunk2-executor-envelope.json"),
    ("r-phase31-c2-validator-grok", "validator", "grok-4.5", "ACCEPT",
     "chunk2-validator-grok-envelope.json"),
    ("r-phase31-c2-validator-gemini", "validator", "gemini-3.1-pro-preview", "ACCEPT",
     "chunk2-validator-gemini-envelope.json"),
    # ---- chunk 3 (panel ACCEPT) ----
    ("r-phase31-c3-test-author", "test-designer", "glm-5.2", None,
     "chunk3-test-author-envelope.json"),
    ("r-phase31-c3-executor", "executor", "glm-5.2", None,
     "chunk3-executor-envelope.json"),
    ("r-phase31-c3-validator-grok", "validator", "grok-4.5", "ACCEPT",
     "chunk3-validator-grok-envelope.json"),
    ("r-phase31-c3-validator-gemini", "validator", "gemini-3.1-pro-preview", "ACCEPT",
     "chunk3-validator-gemini-envelope.json"),
]


def build_rows(ts: str):
    out = []
    for run_id, role, model_id, decision, fname in ROWS:
        path = os.path.join(EVID, fname)
        with open(path) as fh:
            env = json.load(fh)
        usage = env.get("usage", {}) or {}
        provider, family = MODEL_META[model_id]
        verdict = (env.get("result") or "")[:240]
        out.append({
            "schema_version": "v1",
            "ts": ts,
            "run_id": run_id,
            "phase": PHASE,
            "branch": BRANCH,
            "role": role,
            "model_id": model_id,
            "provider": provider,
            "family": family,
            "providerLock": provider,
            "apiProviderLock": provider,
            "num_turns": env.get("num_turns", 0),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
            "thinking_tokens": usage.get("thinking_tokens", 0),
            "duration_ms": env.get("duration_ms", 0),
            "is_error": bool(env.get("is_error", False)),
            "decision": decision,
            "verdict_text_first_240": verdict,
            "envelope_path": "phase-3.1/build-evidence/" + fname,
        })
    return out


def main():
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    existing = []
    if os.path.exists(RUNS):
        with open(RUNS) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("phase") != PHASE:
                    existing.append(row)

    new_rows = build_rows(ts)
    with open(RUNS, "w") as fh:
        for row in existing + new_rows:
            fh.write(json.dumps(row) + "\n")
    print(f"kept {len(existing)} non-{PHASE} rows; wrote {len(new_rows)} {PHASE} rows to {os.path.relpath(RUNS)}")


if __name__ == "__main__":
    main()
