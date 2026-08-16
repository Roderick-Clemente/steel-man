# Testing

The test suite is the executable evidence layer. 233 tests cover the gates, the runner state machine, plan lint, and the repo layout. They are the first thing you run after a clone and the last thing you run before a push.

Run the whole suite from the repo root:

```bash
python3 -m pytest -q
```

Expected: **233 passed, 3 skipped**. The skips are honest. `telemetry/runs.jsonl` is the system-of-record and is gitignored, so tests that assert on its contents have nothing to assert against outside a real run. No skip is hiding a failure.

## Markers

Two markers, declared in `/Users/factory/work/adversarial-sprint-dev/pytest.ini`:

- `unit` — pure data tests. No subprocess, no git state, no network. These are the default and the bulk of the suite.
- `integration` — tests that shell out to subprocess or read git state. They are slower and depend on the working tree being a real checkout.

Select with `-m unit` or `-m integration`. The `--strict-markers` flag in `pytest.ini` means a typo in a marker fails the run rather than silently passing.

## What the tests cover

The suite is spread across `/Users/factory/work/adversarial-sprint-dev/tests/`. The load-bearing files:

- `test_sprint_loop.py` — the runner state machine. The largest file. Covers the per-chunk inner loop, the reconcile gate, invoke options, and the family guard: planner/reviewer collisions, test-designer/executor collisions, validator/executor collisions, the two-distinct-validator-families requirement, and the unknown-model-resolves-to-unknown-family refusal.
- `test_plan_lint.py` — the deterministic pre-review tier in `tools/plan-lint.py`. Seven rules, each pinned by its own test.
- `test_sign_chunk_token.py` — HMAC-SHA256 chunk-completion token signing and verification. The token is what the next chunk refuses to start without.
- `test_chunk_sequence_gate.py` — the sequence gate in `tools/chunk_sequence_gate.py`. Refuses the next chunk when the prior token is missing or invalid.
- `test_cross_family_review.py` — the refusal-at-parse cross-family review gate in `tools/cross_family_review.py`. Pins that a same-family reviewer is refused.
- `test_layout_paths*.py` and `test_repo_layout.py` — the repo layout path constants. These assert that the directory structure matches what `tools/sprint_loop/config.py` declares, so a path drift breaks a test instead of a silent runtime error.
- `test_evidence_consolidation_d2.py`, `test_chunk_close_banner.py`, `test_persistent_referee_stub.py` — evidence shape, the operator-eye chunk-close banner, and the referee stub.

## Writing a test

Tests assert on artifacts, not on exit codes or plausible strings. If you are pinning a behavior, write a test that fails when the behavior breaks, not one that passes when the runner exits 0. The silent-green failure mode is the thing the suite exists to catch.

Negative fixtures live in `/Users/factory/work/adversarial-sprint-dev/tests/fixtures/` and are excluded from collection by `norecursedirs` in `pytest.ini`. They are inputs, never tests. Do not move them into `testpaths`.

## Where to read next

- [getting started](../overview/getting-started.md) for the clone-and-test loop
- [development workflow](development-workflow.md) for what to do before you push
- [patterns and conventions](patterns-and-conventions.md) for the operating rules the tests enforce
