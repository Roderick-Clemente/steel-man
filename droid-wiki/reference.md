# Reference

Dependencies, configuration surfaces, and the key documents that govern the framework. For the method itself, see [PRD.md](../PRD.md) and [the method overview](method.md); for the broader picture, see [overview](overview/index.md); for the findings that shaped these decisions, see [findings](findings/index.md).

## Dependencies

- **Python 3.10+** — the runner and all tooling are Python.
- **pytest >= 9.0** with **pytest-cov** — the test framework and coverage tool used by the evidence pipeline.
- **Factory droid CLI** — the execution substrate. Phase 0 evidence is scoped to `droid` 0.186.0; a CLI upgrade invalidates probe findings until re-run.

See `requirements.txt` for the pinned set.

## Configuration

### Per-pilot overlay

The runner is driven by a JSON config file copied from `templates/overlay/sprint-loop-config.template.json`. It paths the framework checkout and the pilot repo, sets `max_review_rounds` (default 2), pins per-role models, declares the validator panel, and controls fail-closed behavior. `EVIDENCE_SIGNING_KEY` must be set in the operator environment before launching — refusal is the §7 fail-closed behavior in live mode.

### MODEL_FAMILY_MAP

`tools/sprint_loop/config.py:MODEL_FAMILY_MAP` is the curated provenance map. Each entry maps a model ID to a `(provider, family)` tuple. The runner, the cross-family review gate (`tools/cross_family_review.py`), and the plan linter (`tools/plan-lint.py`) all read this same map. A model absent from the map resolves to `("unknown", "unknown")` and cannot satisfy a hard separation constraint. Adding a model requires editing this file — provenance is curated, not declared.

### Model discipline

`tools/conventions/model-discipline.md` is the operational form of PRD §17. Separation-bearing seats (plan reviewer, validator) must pin `--model` before running. The wrapper `tools/run-with-model.sh` refuses to invoke `droid exec` unless `$DROID_MODEL_ID` is set. Telemetry data (`runs.jsonl`, `findings.jsonl`, `dispositions.jsonl`) is git-ignored; the schema lives in `telemetry/SCHEMA.md`.

## Key documents

| Document | What it covers |
|---|---|
| `PRD.md` | Full specification, invariants, workflow, delivery plan |
| `tools/OPERATING-RULES.md` | Operating rules for planner, executor, and validator roles (§18) |
| `tools/KNOWN-ISSUES.md` | Tracked defects the validation pipeline exposed |
| `telemetry/SCHEMA.md` | Schema for the §13 efficacy evaluation data files |
| `tools/adapters/README.md` | The vendor-neutral `NormalizedEnvelope` contract |
| `tools/conventions/model-discipline.md` | Model pinning, cross-family review panel, telemetry placement |
