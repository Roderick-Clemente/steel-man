#!/usr/bin/env python3
"""Reconstruct Phase 2 + Phase 3 telemetry rows from committed envelopes and
merge them with existing Phase 3.2 rows in telemetry/runs.jsonl.

This is the auditable recipe for Phase 4 Track A, Task A4. It does NOT
overwrite existing rows — it reads them, generates new rows from committed
envelopes, deduplicates by run_id, and appends only new rows.

Phase 2 (5 envelopes in phase-2/build-evidence/):
  - planner (claude-opus-5)
  - plan-review-grok-4.5, plan-review-gemini-3.1-pro-preview
  - brief-review-grok, brief-review-gemini

Phase 3 (13 envelopes in phase-3/build-evidence/):
  - 3 chunks × (test-author, executor, validator-grok, validator-gemini)
  - chunk 1 also has an executor-openai-failure envelope

Both Phase 2 and Phase 3 rows use schema_version "v2" but set evidence_source
to null — they predate the Phase 3.2 evidence provider.

Usage:
    python3 phase-4/reconstruct-telemetry.py [--dry-run]
"""
import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir))
RUNS_PATH = os.path.join(REPO_ROOT, "telemetry", "runs.jsonl")
PHASE2_EVID = os.path.join(REPO_ROOT, "phase-2", "build-evidence")
PHASE3_EVID = os.path.join(REPO_ROOT, "phase-3", "build-evidence")

# model_id -> (provider, family). providerLock/apiProviderLock == provider
# (envelope does not surface the observed lock in the CLI version used; see
# phase-3/gen-telemetry.py KI-3 note).
MODEL_META = {
    "claude-opus-5": ("anthropic", "claude-family"),
    "glm-5.2": ("zhipu", "glm-family"),
    "grok-4.5": ("xai", "grok-family"),
    "gemini-3.1-pro-preview": ("google", "gemini-family"),
    "gpt-5.4-mini": ("openai", "openai-family"),
}

PHASE2_BRANCH = "factory/phase-2-slice"
PHASE3_BRANCH = "factory/phase-3-profile"

# Phase 2 runs: (run_id, role, model_id, decision, envelope_filename, reviewer_panel)
# decision: plan-review APPROVE → ACCEPT per the mapping noted in
# brief-review-grok finding 4 and findings.md reconciliation.
PHASE2_RUNS = [
    ("r-phase2-planner", "planner", "claude-opus-5", None,
     "planner-envelope.json", None),
    ("r-phase2-plan-review-grok", "reviewer", "grok-4.5", "ACCEPT",
     "plan-review-grok-4.5-envelope.json",
     ["grok-4.5", "gemini-3.1-pro-preview"]),
    ("r-phase2-plan-review-gemini", "reviewer", "gemini-3.1-pro-preview", "ACCEPT",
     "plan-review-gemini-3.1-pro-preview-envelope.json",
     ["grok-4.5", "gemini-3.1-pro-preview"]),
    ("r-phase2-brief-review-grok", "reviewer", "grok-4.5", "ACCEPT-WITH-NITS",
     "brief-review-grok-envelope.json",
     ["grok-4.5", "gemini-3.1-pro-preview"]),
    ("r-phase2-brief-review-gemini", "reviewer", "gemini-3.1-pro-preview", "ACCEPT",
     "brief-review-gemini-envelope.json",
     ["grok-4.5", "gemini-3.1-pro-preview"]),
]

# Phase 3 runs: (run_id, role, model_id, decision, envelope_filename)
# Adapted from phase-3/gen-telemetry.py.
PHASE3_RUNS = [
    # chunk 1
    ("r-phase3-c1-test-author", "test-designer", "claude-opus-5", None,
     "chunk1-test-author-envelope.json"),
    ("r-phase3-c1-executor-openai-fail", "executor", "gpt-5.4-mini", None,
     "chunk1-executor-openai-failure-envelope.json"),
    ("r-phase3-c1-executor", "executor", "glm-5.2", None,
     "chunk1-executor-envelope.json"),
    ("r-phase3-c1-validator-grok", "validator", "grok-4.5", "ACCEPT",
     "chunk1-validator-grok-envelope.json"),
    ("r-phase3-c1-validator-gemini", "validator", "gemini-3.1-pro-preview", "ACCEPT",
     "chunk1-validator-gemini-envelope.json"),
    # chunk 2
    ("r-phase3-c2-test-author", "test-designer", "claude-opus-5", None,
     "chunk2-test-author-envelope.json"),
    ("r-phase3-c2-executor", "executor", "glm-5.2", None,
     "chunk2-executor-envelope.json"),
    ("r-phase3-c2-validator-grok", "validator", "grok-4.5", "ACCEPT",
     "chunk2-validator-grok-envelope.json"),
    ("r-phase3-c2-validator-gemini", "validator", "gemini-3.1-pro-preview", "ACCEPT",
     "chunk2-validator-gemini-envelope.json"),
    # chunk 3
    ("r-phase3-c3-test-author", "test-designer", "claude-opus-5", None,
     "chunk3-test-author-envelope.json"),
    ("r-phase3-c3-executor", "executor", "glm-5.2", None,
     "chunk3-executor-envelope.json"),
    ("r-phase3-c3-validator-grok", "validator", "grok-4.5", "ACCEPT",
     "chunk3-validator-grok-envelope.json"),
    ("r-phase3-c3-validator-gemini", "validator", "gemini-3.1-pro-preview", "ACCEPT",
     "chunk3-validator-gemini-envelope.json"),
]


def load_envelope(path):
    with open(path) as fh:
        return json.load(fh)


def make_row(run_id, phase, branch, role, model_id, decision, envelope_path_rel,
             evid_dir, ts, reviewer_panel=None):
    """Build a v2 runs.jsonl row from a committed envelope."""
    env = load_envelope(os.path.join(evid_dir, os.path.basename(envelope_path_rel)))
    usage = env.get("usage", {}) or {}
    provider, family = MODEL_META[model_id]
    verdict = (env.get("result") or "")[:240]

    row = {
        "schema_version": "v2",
        "ts": ts,
        "run_id": run_id,
        "phase": phase,
        "branch": branch,
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
        "envelope_path": envelope_path_rel,
        # Phase 2 and Phase 3 predate the evidence provider (Phase 3.2).
        # evidence_source is null — not in-session or bundle.
        "evidence_source": None,
    }

    if reviewer_panel is not None:
        row["reviewer_panel"] = reviewer_panel
        row["review_target_branch"] = branch

    return row


def main():
    dry_run = "--dry-run" in sys.argv
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Read existing rows.
    existing_rows = []
    existing_ids = set()
    if os.path.exists(RUNS_PATH):
        with open(RUNS_PATH) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                existing_rows.append(row)
                existing_ids.add(row["run_id"])

    print(f"Existing rows: {len(existing_rows)} (run_ids: {sorted(existing_ids)})")

    # 2. Generate Phase 2 rows.
    phase2_rows = []
    for run_id, role, model_id, decision, fname, panel in PHASE2_RUNS:
        env_rel = f"phase-2/build-evidence/{fname}"
        row = make_row(run_id, "phase-2", PHASE2_BRANCH, role, model_id,
                       decision, env_rel, PHASE2_EVID, ts, reviewer_panel=panel)
        phase2_rows.append(row)

    # 3. Generate Phase 3 rows.
    phase3_rows = []
    for run_id, role, model_id, decision, fname in PHASE3_RUNS:
        env_rel = f"phase-3/build-evidence/{fname}"
        row = make_row(run_id, "phase-3", PHASE3_BRANCH, role, model_id,
                       decision, env_rel, PHASE3_EVID, ts)
        phase3_rows.append(row)

    # 4. Merge: append only new rows (deduplicate by run_id).
    new_rows = []
    for row in phase2_rows + phase3_rows:
        if row["run_id"] not in existing_ids:
            new_rows.append(row)
        else:
            print(f"  SKIP (already exists): {row['run_id']}")

    merged = existing_rows + new_rows

    print(f"Phase 2 rows generated: {len(phase2_rows)}")
    print(f"Phase 3 rows generated: {len(phase3_rows)}")
    print(f"New rows to append: {len(new_rows)}")
    print(f"Merged total: {len(merged)}")

    if dry_run:
        print("\n--dry-run: not writing. New rows:")
        for row in new_rows:
            print(f"  {row['run_id']} | {row['phase']} | {row['role']} | "
                  f"{row['model_id']} | turns={row['num_turns']} | "
                  f"in={row['input_tokens']} out={row['output_tokens']} | "
                  f"dur={row['duration_ms']}ms | err={row['is_error']} | "
                  f"dec={row['decision']}")
        return

    # 5. Write merged result back.
    with open(RUNS_PATH, "w") as fh:
        for row in merged:
            fh.write(json.dumps(row) + "\n")

    print(f"\nWrote {len(merged)} rows to {os.path.relpath(RUNS_PATH, REPO_ROOT)}")


if __name__ == "__main__":
    main()
