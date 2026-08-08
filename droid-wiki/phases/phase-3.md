# Phase 3 — Execution Sprint

Phase 3 executed the Phase 2 plan end-to-end: a read-only `GET /profile` page in the QuantumBank pilot, built in three chunks using the full adversarial loop. The human plan-approval gate was already passed, and the plan was frozen at hash `sha256:72eccff5…`.

## Key source files

| File | Purpose |
|---|---|
| `/Users/factory/work/adversarial-sprint-dev/phase-3/README.md` | Execution brief: objective, model seats, chunk split, per-chunk loop |
| `/Users/factory/work/adversarial-sprint-dev/phase-3/RUN-COMMANDS.md` | Exact `droid exec` commands for each role and chunk |
| `/Users/factory/work/adversarial-sprint-dev/phase-3/KNOWN-ISSUES.md` | Operational findings during execution (KI-1 through KI-4) |
| `/Users/factory/work/adversarial-sprint-dev/phase-2/plan-v1.md` | The plan Phase 3 executed |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/lock.py` | Test locking, reused from Phase 1 |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/valid-red.py` | RED validation, reused from Phase 1 |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/verify-green.py` | GREEN verification, reused from Phase 1 |
| `/Users/factory/work/adversarial-sprint-dev/phase-1/hooks/locked-test-guard.py` | Hook blocking test edits, reused from Phase 1 |

## Model seats

| Role | Model | Family | Notes |
|---|---|---|---|
| Test-author | `claude-opus-5` | anthropic | Different family from executor (invariant #1) |
| Executor | `glm-5.2` | zhipu | Planned `gpt-5.4-mini` (openai) was unavailable; substituted with human approval |
| Validator 1 | `grok-4.5` | xAI | Pinned, different family from executor |
| Validator 2 | `gemini-3.1-pro-preview` | google | Pinned, different family from executor |

## Test file split

The plan called for one `/Users/factory/work/quantum-bank--llms-txt-pilot/test/test_profile.py`, but the per-chunk lock-and-execute loop needs each chunk's tests locked before that chunk's implementation. A single file locked after chunk 1 would block the chunk 2 test-author from adding tests. So the tests were split into three files, one per chunk:

| File | Chunk | Tests |
|---|---|---|
| `/Users/factory/work/quantum-bank--llms-txt-pilot/test/test_profile_model.py` | 1 | `get_user_profile` unit: key-set contract, `None` for unknown, address non-empty |
| `/Users/factory/work/quantum-bank--llms-txt-pilot/test/test_profile_route.py` | 2 | Route + template: auth redirect, no-leak, field presence, stale session (A5), DB-vs-session (A3) |
| `/Users/factory/work/quantum-bank--llms-txt-pilot/test/test_profile_seed.py` | 3 | Seed identity: fresh-DB Picard fields, login still works |

## Per-chunk loop

For each chunk, in order:

1. **Test-author** writes the chunk's test file from the plan + amendments.
2. **Lock** the test file by SHA-256.
3. **Valid-RED** — the test must fail for the expected behavioral reason.
4. **Executor** implements to GREEN, touching only the chunk's allowed implementation files.
5. **GREEN verification** — hash matches + test passes.
6. **Cross-family validation** — both validators review the diff + test evidence. Reject triggers a cheap retry, capped at 2 rounds.
7. Only an accepted chunk unblocks the next.

## Chunk specs

- **Chunk 1 — profile read model:** `get_user_profile(user_id: int) -> dict | None` in `/Users/factory/work/quantum-bank--llms-txt-pilot/models.py`, returning exactly `{"username", "email", "full_name", "address"}` or `None`. Address came from a module-level constant `PROFILE_DEMO_ADDRESS` with an env override.
- **Chunk 2 — route + template:** `handle_profile()` in new `/Users/factory/work/quantum-bank--llms-txt-pilot/api/profile.py`, registered as `@app.route("/profile")` in `/Users/factory/work/quantum-bank--llms-txt-pilot/app.py`. Unauthenticated requests redirect to login. Missing user → redirect to login. Template is standalone `/Users/factory/work/quantum-bank--llms-txt-pilot/templates/profile.html`.
- **Chunk 3 — demo seed identity:** The seed tuple at `/Users/factory/work/quantum-bank--llms-txt-pilot/models.py:431` became `("demo", "jpicard@starfleet.fed", "Jean-Luc Picard")`. `username` stayed `"demo"` because it is the login credential.

## Known issues

- **KI-1:** The planned openai executor (`gpt-5.4-mini`) was unavailable for hours, returning `Exec failed` with 0 turns. `glm-5.2` was substituted with human approval. The failed openai envelope is preserved in `/Users/factory/work/adversarial-sprint-dev/phase-3/build-evidence/chunk1-executor-openai-failure-envelope.json`.
- **KI-2:** The validator is nominally read-only but has `Execute` at `--auto high`, which is a theoretical write vector. Mitigation: `git status --porcelain` after every validator run. No stray writes were observed across all six validator runs.
- **KI-3:** The JSON envelope does not surface `providerLock` / `apiProviderLock`, so the telemetry rows record the known provider from the pinned `--model` instead of an observed lock.
- **KI-4:** `/Users/factory/work/adversarial-sprint-dev/telemetry/SCHEMA.md` omits the `test-designer` role, even though the PRD defines it as a separate seat. Phase 3 recorded it anyway.

## Outcome

All three chunks completed on `factory/phase-3-profile`. The full suite reached 99 passed. The slice was presented at the human merge gate but was not self-merged; final merge is a separate human decision.

## Relationship to other phases

- Phase 3 consumed the plan and amendments from [Phase 2](phase-2.md).
- Phase 3 reused the locking and verification scripts from [Phase 1](phase-1.md).
- Phase 3.1 used the Phase 3 run as its control arm and deliberately degraded the test-author seat.
- Phase 3.2 externalized the deterministic evidence that Phase 3 validators had to produce in-session.
