# Phase 3 — droid exec run commands

Operational reference for each role invocation. Run sequentially (zero-buffer
budget). Capture every envelope to `phase-3/build-evidence/`.

## Paths

- Framework: `/Users/factory/work/adversarial-sprint-dev`
- Pilot: `/Users/factory/work/quantum-bank--llms-txt-pilot`
- Prompts: `phase-3/prompts/`
- Evidence: `phase-3/build-evidence/`
- Locks: `phase-1/locks/` (hook default; holds both Phase-1 and Phase-3 locks)

## Chunk 1 — profile read model

### Test-author (claude-opus-5, anthropic)
```bash
cd /Users/factory/work/adversarial-sprint-dev
DROID_MODEL_ID=claude-opus-5 droid exec \
  --model claude-opus-5 --auto low \
  --cwd /Users/factory/work/quantum-bank--llms-txt-pilot \
  -f phase-3/prompts/chunk1-test-author.md \
  -o json > phase-3/build-evidence/chunk1-test-author-envelope.json \
  2> phase-3/build-evidence/chunk1-test-author-stderr.log
```

### Lock the test
```bash
cd /Users/factory/work/quantum-bank--llms-txt-pilot
python3 /Users/factory/work/adversarial-sprint-dev/phase-1/scripts/lock.py \
  test/test_profile_model.py \
  "profile key-set equals contract" \
  --pilot-root /Users/factory/work/quantum-bank--llms-txt-pilot \
  --locks-dir /Users/factory/work/adversarial-sprint-dev/phase-1/locks
```

### Valid-RED
```bash
cd /Users/factory/work/quantum-bank--llms-txt-pilot
python3 /Users/factory/work/adversarial-sprint-dev/phase-1/scripts/valid-red.py \
  --pilot-root /Users/factory/work/quantum-bank--llms-txt-pilot \
  --test-file test/test_profile_model.py \
  --accepted-assertion "profile key-set equals contract" \
  --python .venv/bin/python -o json
```

### Executor (gpt-5.4-mini, openai)
```bash
cd /Users/factory/work/adversarial-sprint-dev
DROID_MODEL_ID=gpt-5.4-mini droid exec \
  --model gpt-5.4-mini --auto low \
  --cwd /Users/factory/work/quantum-bank--llms-txt-pilot \
  -f phase-3/prompts/chunk1-executor.md \
  -o json > phase-3/build-evidence/chunk1-executor-envelope.json \
  2> phase-3/build-evidence/chunk1-executor-stderr.log
```

### Verify GREEN
```bash
cd /Users/factory/work/quantum-bank--llms-txt-pilot
python3 /Users/factory/work/adversarial-sprint-dev/phase-1/scripts/verify-green.py \
  --pilot-root /Users/factory/work/quantum-bank--llms-txt-pilot \
  --lock-file /Users/factory/work/adversarial-sprint-dev/phase-1/locks/test/test_profile_model.py.lock.json \
  --test-file test/test_profile_model.py \
  --python .venv/bin/python
```

### Validator 1 (grok-4.5, xAI)
```bash
cd /Users/factory/work/adversarial-sprint-dev
DROID_MODEL_ID=grok-4.5 droid exec \
  --model grok-4.5 --auto high \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd /Users/factory/work/quantum-bank--llms-txt-pilot \
  -f phase-3/prompts/chunk1-validator.md \
  -o json > phase-3/build-evidence/chunk1-validator-grok-envelope.json \
  2> phase-3/build-evidence/chunk1-validator-grok-stderr.log
```

### Validator 2 (gemini-3.1-pro-preview, google)
```bash
cd /Users/factory/work/adversarial-sprint-dev
DROID_MODEL_ID=gemini-3.1-pro-preview droid exec \
  --model gemini-3.1-pro-preview --auto high \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd /Users/factory/work/quantum-bank--llms-txt-pilot \
  -f phase-3/prompts/chunk1-validator.md \
  -o json > phase-3/build-evidence/chunk1-validator-gemini-envelope.json \
  2> phase-3/build-evidence/chunk1-validator-gemini-stderr.log
```

### Post-validator check (KI-2 mitigation)
```bash
cd /Users/factory/work/quantum-bank--llms-txt-pilot
git status --porcelain  # check for stray writes by validators
```

---

## Chunk 2 — route + template

Same pattern; swap `chunk1` → `chunk2`, test file → `test/test_profile_route.py`,
accepted assertion → `"profile requires authenticated session"`.

## Chunk 3 — demo seed identity

Same pattern; swap `chunk3` → `chunk3`, test file → `test/test_profile_seed.py`,
accepted assertion → `"seeded identity is Jean-Luc Picard"`.

---

## Telemetry row (after each droid exec call)

Append to `telemetry/runs.jsonl` (gitignored):
```json
{"schema_version":"v1","ts":"<ISO-8601>","run_id":"<id>","phase":"phase-3","branch":"factory/phase-3-profile","role":"<role>","model_id":"<model>","provider":"<provider>","family":"<family>","providerLock":"<lock>","apiProviderLock":"<lock>","num_turns":<n>,"input_tokens":<n>,"output_tokens":<n>,"duration_ms":<n>,"is_error":<bool>,"decision":"<verdict>","envelope_path":"phase-3/build-evidence/<file>"}
```
