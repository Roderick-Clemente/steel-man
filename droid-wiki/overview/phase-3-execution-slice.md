# Phase 3 — the end-to-end execution slice

**Phase 1 proved the loop can review code it wrote. Phase 2 proved it can
review a plan before code is written and reach a hash-bound approval. Phase 3
closes the loop: take that approved plan, build the feature for real, and run
the same cross-family panel on the code — plan → execute → review, end to
end, on one real slice.**

The slice is the same read-only `GET /profile` page from Phase 2's approved
plan-v1 (`sha256:72eccff5…`): render the session-authenticated user's
`username`, `email`, `full_name`, and a themed address for the demo identity
Jean-Luc Picard. Session-scoped, no `?id=` parameter, no write path. Small on
purpose; the point is the *loop*, not the feature.

The PRD §11 Phase 3 exit is verbatim: *"one complete run plus a replayable
demo and baseline comparison."*

## The execution loop (PRD §5.2–5.5)

Three chunks, each running the full cycle: test-authorship (independent family)
→ lock by content hash → valid-RED → cheap executor → cross-family validation.
Only an ACCEPTED chunk unblocks the next.

### Model seats

| Role | Model | Family | Why |
|---|---|---|---|
| Orchestrator | Factory | — | Conducts, no role seat |
| Test-author | `claude-opus-5` | anthropic | ≠ executor family (invariant 1) |
| Executor | `gpt-5.4-mini` | openai | Cheap tier; cost hypothesis H3 |
| Validator 1 | `grok-4.5` | xai | ≠ executor family; pinned (§17.2) |
| Validator 2 | `gemini-3.1-pro-preview` | google | ≠ executor family; pinned (§17.2) |

### Chunk 1 — profile read model (data layer)

`get_user_profile(user_id) -> dict | None` in `models.py`, returning exactly
`{"username", "email", "full_name", "address"}` from named columns (not
`SELECT *`). Address from a config constant with env override (A4).

| role | model | duration | num_turns | tokens | decision |
|---|---|---|---|---|---|
| test-author | claude-opus-5 | _TBD_ | _TBD_ | _TBD_ | wrote `test/test_profile_model.py` |
| executor | gpt-5.4-mini | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| validator (grok) | grok-4.5 | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| validator (gemini) | gemini-3.1-pro-preview | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

<!-- Results to be filled in after execution: valid-RED classification,
GREEN verification, cross-family verdicts, any findings. -->

### Chunk 2 — route + template (delivery layer)

`handle_profile()` in `api/profile.py`, `templates/profile.html`, registered in
`app.py`. Auth guard mirroring `api/dashboard.py`. DB is source of truth, not
session. Stale session fails closed (A5). DB-vs-session test (A3).

| role | model | duration | num_turns | tokens | decision |
|---|---|---|---|---|---|
| test-author | claude-opus-5 | _TBD_ | _TBD_ | _TBD_ | wrote `test/test_profile_route.py` |
| executor | gpt-5.4-mini | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| validator (grok) | grok-4.5 | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| validator (gemini) | gemini-3.1-pro-preview | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

### Chunk 3 — demo seed identity

Seed tuple at `models.py:431` → `("demo", "jpicard@starfleet.fed", "Jean-Luc
Picard")`. `username` stays `"demo"`. A1 integration test binds the Picard
identity in `GET /profile`.

| role | model | duration | num_turns | tokens | decision |
|---|---|---|---|---|---|
| test-author | claude-opus-5 | _TBD_ | _TBD_ | _TBD_ | wrote `test/test_profile_seed.py` |
| executor | gpt-5.4-mini | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| validator (grok) | grok-4.5 | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| validator (gemini) | gemini-3.1-pro-preview | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

## Cross-family validation results

<!-- To be filled in after all chunks complete. Key questions:
- Did both validators agree on every chunk?
- What was the first_seen_in_panel_position distribution?
- Were any findings blocking/high?
- Did the cheap executor need retries? -->

## Operational findings

<!-- To be filled in. Carry-forward from Phase 2 KNOWN-ISSUES:
- KI-1: autonomy floor for Execute (validators need --auto high)
- KI-2: --auto high + Execute is a write vector
- New findings from this phase? -->

## Tokens spent

<!-- To be filled in from telemetry rows. -->

## What Phase 3 leaves for Phase 4+

A complete loop demonstrated end to end: plan → execute → review on one real
slice. The framework is usable on real work. Phase 4 generalises across stacks;
Phase 5 hardens the loop's own invariants.

The human merge gate (PRD §6) remains: the slice is presented, not merged.
