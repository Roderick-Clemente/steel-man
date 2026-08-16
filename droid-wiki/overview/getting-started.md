# Getting started

## Prerequisites

- Python 3.10+
- `pytest>=9.0` and `pytest-cov` (install via `pip install -r requirements.txt`)
- Git
- A Factory `droid` CLI install (only needed for live sprint runs, not for tests) — the only working adapter today
  - Factory works today; the adapter seam in `tools/adapters/` exists so others can follow without rewriting the gates
  - If you want to wire up Codex, Claude Code, or Ollama, reach out — happy to help

## Clone and test

```bash
git clone https://github.com/Roderick-Clemente/adversarial-sprint.git
cd adversarial-sprint
pip install -r requirements.txt
python3 -m pytest -q
```

Expected: **233 passed, 3 skipped**. The skips are honest: `telemetry/runs.jsonl` is the system-of-record and is gitignored, so tests that assert on its contents have nothing to assert against outside a real run.

## Run a sprint (adopt the method on your own project)

The runner is invoked through a per-pilot overlay, not the framework CLI directly. See [adopting the method](../how-to-contribute/adopting-the-method.md) for the full setup guide. Quick version:

```bash
# 1. Install the overlay into your pilot repo
mkdir -p <PILOT_REPO>/.adversarial-sprint/bin
cp templates/overlay/sprint-loop-config.template.json \
   <PILOT_REPO>/.adversarial-sprint/sprint-loop-config.json
cp templates/overlay/sprint-loop-chunks-example.template.json \
   <PILOT_REPO>/.adversarial-sprint/chunks.json
cp templates/overlay/bin/run-sprint \
   <PILOT_REPO>/.adversarial-sprint/bin/run-sprint
chmod +x <PILOT_REPO>/.adversarial-sprint/bin/run-sprint

# 2. Edit the config: set framework_root, pilot_root, validators, API keys

# 3. Dry-run wiring test
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --dry-run --non-interactive

# 4. Real run (you stay in the seat)
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint
```

You need: a pilot repo with tests, Factory API keys (or model API keys for each family in your panel), and an `EVIDENCE_SIGNING_KEY` environment variable. See [adopting the method](../how-to-contribute/adopting-the-method.md) for details.

## Key entry points

| What | Where |
|---|---|
| Full spec (problem, invariants, phases) | `PRD.md` |
| Operating discipline (§1-§24, each with the incident behind it) | `tools/OPERATING-RULES.md` |
| Sprint loop runner | `tools/sprint-loop.py` |
| Runner package | `tools/sprint_loop/` |
| Agent-facing skill | `skills/adversarial-sprint/SKILL.md` |
| Sprint invocation skill | `skills/sprint-invocation/SKILL.md` |
| CI workflow | `.github/workflows/adversarial-sprint-ci.yml` |

## Where to read next

- [The method](../method.md) - the GROK, CHUNK, EXECUTE workflow
- [Features](../features/index.md) - the code: sprint loop runner, token gates, plan-lint, evidence provider, CI
- [Findings](../findings/index.md) - what the live runs discovered
- [How to contribute](../how-to-contribute/index.md) - how to jump in
