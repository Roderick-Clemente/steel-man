#!/usr/bin/env python3
"""Generate telemetry/runs.jsonl rows for Phase 3 from the captured envelopes.

Rows are git-ignored (see telemetry SCHEMA.md); this generator is the auditable
recipe that produced them. Run-level numbers (num_turns, usage.*, duration_ms,
is_error) are read from the raw envelopes, not transcribed. Per-run metadata
(run_id, role, model, provider/family, decision) is the orchestrator's record.

Note (honest limitation): the `-o json` envelope in this Droid CLI version does
NOT surface providerLock/apiProviderLock, so those fields are set to the known
provider per tools/conventions/commit-body-recipe.md §13 ("...or the provider
name if it is not yet known"). Recorded as KI-3 in phase-3/KNOWN-ISSUES.md.

Note (schema gap): telemetry/SCHEMA.md's `role` enum is
planner/executor/validator/reviewer and omits `test-designer` (PRD §7's fifth
role). We emit the canonical role name anyway; see KI-4.
"""
import json
import os
import sys
from datetime import datetime, timezone

# chunk-D1-2a: this script used to live at phase-3/ with its evidence as a
# sibling directory. It now lives under tools/, so a self-relative
# "build-evidence" resolves to tools/phase-3-gen/build-evidence and does not
# exist. Resolve through the layout roots in sprint_loop.config instead of
# re-hardcoding "evidence/phase-3/..." — a literal prefix is what broke here,
# and it would break again on the next move.
_TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRAMEWORK_ROOT = os.path.dirname(_TOOLS_DIR)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.config import EVIDENCE_ROOT, phase_path  # noqa: E402

EVID = phase_path(_FRAMEWORK_ROOT, "evidence", "phase-3", "build-evidence")
OUT = os.path.join(_FRAMEWORK_ROOT, "telemetry", "runs.jsonl")
# Relative form for the telemetry row's envelope_path field. Forward slashes:
# the field is a portable record, not a local filesystem path.
_ENVELOPE_DIR_REL = "/".join((*EVIDENCE_ROOT.split(os.sep), "phase-3", "build-evidence"))
BRANCH = "factory/phase-3-profile"

# model_id -> (provider, family). providerLock/apiProviderLock == provider here
# (envelope does not surface the observed lock in this CLI version; see KI-3).
MODEL_META = {
    "claude-opus-5": ("anthropic", "claude-family"),
    "glm-5.2": ("zhipu", "glm-family"),
    "grok-4.5": ("xai", "grok-family"),
    "gemini-3.1-pro-preview": ("google", "gemini-family"),
    "gpt-5.4-mini": ("openai", "openai-family"),
}

# (run_id, role, model_id, decision, envelope_filename)
RUNS = [
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


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for run_id, role, model_id, decision, fname in RUNS:
        path = os.path.join(EVID, fname)
        with open(path) as fh:
            env = json.load(fh)
        usage = env.get("usage", {}) or {}
        provider, family = MODEL_META[model_id]
        verdict = (env.get("result") or "")[:240]
        row = {
            "schema_version": "v1",
            "ts": ts,
            "run_id": run_id,
            "phase": "phase-3",
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
            "envelope_path": _ENVELOPE_DIR_REL + "/" + fname,
        }
        rows.append(row)
    with open(OUT, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    print(f"wrote {len(rows)} rows to {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
