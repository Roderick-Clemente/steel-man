# Phase 4.5 — Build notes

What was built, in 7 chunks. Each chunk is a separate commit per
`AGENTS.md` ("commits are the baton"). Each chunk has a
script-runnable check that exits 0 against its own deliverable
(`OPERATING-RULES.md` §11).

## Inventory

### Chunks landed

1. **State + Config + tests + §18 rule** (`8f5ecda`)
   - `tools/sprint_loop/{__init__,state,config}.py`
   - `tests/test_sprint_loop.py` (29 tests)
   - `pytest.ini`
   - `tools/OPERATING-RULES.md` §18 (compose / chunk / fix friction /
     review / distill)
   - In-line primitive fix: `tools/run-with-model.sh` refuses
     `--mission` per Phase 0 GO-NO-GO.
   - State: ✅ — `python3 -m py_compile tools/sprint_loop/*.py`
     → 0 exit; `pytest tests/` → 29 pass.

2. **Droid wrapper + Track B backends** (`011362d`)
   - `tools/sprint_loop/droid.py` — single source of `droid exec`
     invocation; uses `tools/run-with-model.sh` (OPERATING-RULES §14).
   - `tools/sprint_loop/backends.py` — `ValidationBackend` protocol;
     `LocalBackend` shells out to `tools/orchestrate-review.py`;
     `CIBackend` is `NotImplementedError` per Phase 4.5 prompt.
   - Tests: ✅ — adds 8 tests covering droid wrapper + backends
     (dry-run path, missing-orchestrator, missing chunk keys, ci
     refusal, factory names).

3. **Role prompts + renderer** (`caba6cd`)
   - `tools/sprint_loop/prompts/{planner,plan-reviewer,test-designer,executor,validator}.md`
   - `tools/sprint_loop/prompts/render.py` — safe substitution;
     unknown `{{key}}` placeholders remain in the output (loud
     failure beats silent).
   - Tests: ✅ — adds 6 tests covering template list, anti-implementation
     invariant (§13), substitution behavior, minimal-context coverage.

4. **Per-chunk inner loop** (`969fcbd`)
   - `tools/sprint_loop/per_chunk.py` — composes the project's own
     scripts: `lock.py`, `valid-red.py`, `verify-green.py`,
     `local_backend.py`, `LocalBackend.validate`.
   - §7 fail-closed checks: bundle signature verified against
     `EVIDENCE_SIGNING_KEY`; locked-test SHA cross-checked against
     the manifest.
   - Tests: ✅ — adds 7 tests for each step + render helpers.

5. **Runner orchestrator + examples + integration tests** (`489b673`)
   - `tools/sprint-loop.py` — top-level entry; planner → 2 plan
     reviewers → reconcile (stdin pause) → chunking →
     per-chunk inner loop → per-chunk commit on the sprint branch.
   - `examples/sprint-loop-config.json` + `examples/sprint-loop-chunks-example.json`
   - Tests: ✅ — adds 2 integration tests (dry-run end-to-end;
     family-guard refuse on unknown model).

6. **Track C CI flavor (a)** (`825fa0c`)
   - `.github/workflows/adversarial-sprint-ci.yml` — runs
     `local_backend.py` then `orchestrate-review.py` per PR;
     gate decision becomes a PR status check that blocks merge.
   - `phase-4.5/CI-GATE.md` — companion doc covering signing-key
     distribution, droid install requirement, the
     `[chunk:<id>]` PR-title convention.
   - State: ✅ — yaml.safe_load parses; no new runner tests
     required (CI is a wrapper around the existing primitives).

7. **Docs + adversarial review pass** (this commit)
   - `phase-4.5/{RUN-PROMPT,ASSUMPTIONS,KNOWN-ISSUES,BUILD-NOTES}.md`
   - `phase-4.5/PLAN.md` (the chunked plan that drove the build)
   - `phase-4.5/adversarial_review/` (cross-family structural review
     findings + dispositions, written as a deliberate exercise of
     §18's "review at the end")

## How to run

```bash
# Sanity
PYTHONPATH=tools /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python -m py_compile tools/sprint-loop.py tools/sprint_loop/*.py tests/test_sprint_loop.py
PYTHONPATH=tools /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python -m pytest tests/ -v

# Dry-run end-to-end against the example config + chunks file
PYTHONPATH=tools /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python \
  tools/sprint-loop.py \
  --config examples/sprint-loop-config.json \
  --chunks-file examples/sprint-loop-chunks-example.json \
  --dry-run --non-interactive

# Real run (interactive; pauses at reconcile for accept/reject/amend)
export EVIDENCE_SIGNING_KEY="$( python3 -c 'import secrets; print(secrets.token_hex(32))' )"
PYTHONPATH=tools /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python \
  tools/sprint-loop.py \
  --config /path/to/your/cfg.json \
  --chunks-file /path/to/your/chunks.json
```

## What's NOT done (clean nulls per OPERATING-RULES §12)

See `KNOWN-ISSUES.md`. The headline unexercised paths:

1. **End-to-end pilot run** (KN1) — runner is dry-run-tested, not
   piloted against real `droid exec` + real pytest against real pilot.
2. **Reconciliation under real disagreement** (KN2) — clean null per
   PRD §13.
3. **`--validation-backend=ci`** — stub per the prompt's "interface
   only."

## Residual handover notes

- The runner's invariant enforcement is structural (preflight
  family guard, §7 fail-closed). Operator override paths
  (`--skip-reconcile`, `--allow-test-author-collide`) are explicit
  flags — never default-on.
- Telemetry rows are git-ignored (`telemetry/*.jsonl` in
  `.gitignore`). The runner appends rows; it does NOT `git add` them.
- The runner's `factory/sprint-<run-id>-<ts>` branch is local; the
  runner NEVER `git push`es. Human gates the merge (invariant #8).
- Cross-family separation model map lives at
  `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`. Add a new model
  there BEFORE deploying new droid models to the loop.
- `--validation-backend=ci` raise()s; the CI workflow file
  inlines the evidence + orchestrator path directly without
  going through the runner process.

## Cross-references

- PRD §11 Phase 4.5 — the deliverable spec.
- PRD §17 — model discipline (the runner §17.2 guard enforces this).
- `tools/OPERATING-RULES.md` §1–§17, plus §18 (this build added).
- `tools/conventions/model-discipline.md` — cross-family panel
  defaults (gemini-2.5-pro, grok-4.5 primary; claude-opus-4-8 fallback).
- `tools/conventions/commit-body-recipe.md` — per-chunk commit body
  shape.
- `phase-4.5/CI-GATE.md` — CI workflow companion.
- `phase-4.5/PLAN.md` — the chunked plan that drove the build.
- `phase-4.5/ASSUMPTIONS.md` — gap log per Phase 3.2 convention.
- `phase-4.5/KNOWN-ISSUES.md` — clean-null gaps + ergonomic nits.
- `ROADMAP-REVIEW.md` — full project audit; Phase 4.5 is bounded by
  the §4.6 sections.
