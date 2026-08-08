# Phase 3.2 — Review RUN-COMMANDS

Scripted cross-family review of the `factory/phase-3.2-evidence` branch.
Mirrors the Phase 3 `RUN-COMMANDS.md` pattern — mechanical, reproducible.

## Paths

- Framework worktree: `/Users/factory/work/adversarial-sprint-dev-3.2-build`
- Pilot: `/Users/factory/work/quantum-bank--llms-txt-pilot`
- Review prompt: `phase-3.2/reviews/review-prompt.md`
- Evidence: `phase-3.2/reviews/`

## Reviewer 1 (grok-4.5, xAI)

```bash
cd /Users/factory/work/adversarial-sprint-dev-3.2-build
DROID_MODEL_ID=grok-4.5 droid exec \
  --model grok-4.5 --auto high \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd /Users/factory/work/adversarial-sprint-dev-3.2-build \
  -f phase-3.2/reviews/review-prompt.md \
  -o json > phase-3.2/reviews/review-grok-envelope.json \
  2> phase-3.2/reviews/review-grok-stderr.log
```

## Reviewer 2 (gemini-3.1-pro-preview, google)

```bash
cd /Users/factory/work/adversarial-sprint-dev-3.2-build
DROID_MODEL_ID=gemini-3.1-pro-preview droid exec \
  --model gemini-3.1-pro-preview --auto high \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd /Users/factory/work/adversarial-sprint-dev-3.2-build \
  -f phase-3.2/reviews/review-prompt.md \
  -o json > phase-3.2/reviews/review-gemini-envelope.json \
  2> phase-3.2/reviews/review-gemini-stderr.log
```

## Post-review stray-write check (KI-2 mitigation)

```bash
cd /Users/factory/work/adversarial-sprint-dev-3.2-build
git status --porcelain  # check for stray writes by reviewers
```

## Telemetry rows (after each droid exec call)

Append to `telemetry/runs.jsonl` (gitignored):
```json
{"schema_version":"v2","ts":"<ISO-8601>","run_id":"r-phase32-review-grok","phase":"phase-3.2","branch":"factory/phase-3.2-evidence","role":"validator","model_id":"grok-4.5","provider":"xai","family":"grok-family","providerLock":"xai","apiProviderLock":"xai","num_turns":<n>,"input_tokens":<n>,"output_tokens":<n>,"duration_ms":<n>,"is_error":<bool>,"decision":"<verdict>","evidence_source":"in-session","envelope_path":"phase-3.2/reviews/review-grok-envelope.json"}
{"schema_version":"v2","ts":"<ISO-8601>","run_id":"r-phase32-review-gemini","phase":"phase-3.2","branch":"factory/phase-3.2-evidence","role":"validator","model_id":"gemini-3.1-pro-preview","provider":"google","family":"gemini-family","providerLock":"google","apiProviderLock":"google","num_turns":<n>,"input_tokens":<n>,"output_tokens":<n>,"duration_ms":<n>,"is_error":<bool>,"decision":"<verdict>","evidence_source":"in-session","envelope_path":"phase-3.2/reviews/review-gemini-envelope.json"}
```

Note: `evidence_source` is `in-session` because the reviewers are reviewing the
3.2 code itself (reading files, running commands), not consuming an
EvidenceBundle. The bundle path is for the H-CI experiment, not for reviewing
the provider that produces bundles.
