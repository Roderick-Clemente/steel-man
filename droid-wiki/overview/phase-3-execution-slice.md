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
| Executor | ~~`gpt-5.4-mini`~~ → `glm-5.2` | ~~openai~~ → zhipu | Cheap tier; cost hypothesis H3. Planned openai seat was down the whole window (KI-1); substituted `glm-5.2` with human approval. Separation preserved (zhipu ≠ anthropic/xai/google) |
| Validator 1 | `grok-4.5` | xai | ≠ executor family; pinned (§17.2) |
| Validator 2 | `gemini-3.1-pro-preview` | google | ≠ executor family; pinned (§17.2) |

The executor swap is the phase's first real operational finding: the seat where
*no* family invariant binds (§17.1) is exactly the seat that could be swapped
under an outage without touching independence. See KI-1 and the Phase-3.1
"per-seat fallback registry" note. A posterity A/B against `gpt-5.4-mini`
remains open for when openai recovers.

### Chunk 1 — profile read model (data layer)

`get_user_profile(user_id) -> dict | None` in `models.py`, returning exactly
`{"username", "email", "full_name", "address"}` from named columns (not
`SELECT *`). Address from a config constant with env override (A4).

| role | model | duration | num_turns | tokens | decision |
|---|---|---|---|---|---|
| test-author | claude-opus-5 | 69.1s | 8 | 4,030 | wrote `test/test_profile_model.py`; valid-RED, locked `8041e607` |
| executor (openai) | gpt-5.4-mini | 1.3s | 0 | 0 | **failed** (KI-1, provider down) |
| executor | glm-5.2 | 30.2s | 6 | 20,681 | GREEN 3/3, first try, +23 lines `models.py` |
| validator (grok) | grok-4.5 | 49.6s | 5 | 20,064 | **ACCEPT**, 0 findings |
| validator (gemini) | gemini-3.1-pro-preview | 45.9s | 7 | 98,700 | **ACCEPT**, 0 findings |

Valid-RED: intended assertion `profile key-set equals contract` ran and failed.
GREEN verified by hash-locked gate (sha `8041e607`), full suite 90 passed.
Both validators independently ran runtime key-set checks (confirmed `id` /
`created_at` absent) before accepting.

### Chunk 2 — route + template (delivery layer)

`handle_profile()` in `api/profile.py`, `templates/profile.html`, registered in
`app.py`. Auth guard mirroring `api/dashboard.py`. DB is source of truth, not
session. Stale session fails closed (A5). DB-vs-session test (A3).

| role | model | duration | num_turns | tokens | decision |
|---|---|---|---|---|---|
| test-author | claude-opus-5 | 90.9s | 10 | 5,969 | wrote `test/test_profile_route.py` (6 tests); valid-RED, locked `7c5579fd` |
| executor | glm-5.2 | 52.8s | 9 | 30,688 | GREEN 6/6, first try; `api/profile.py`, `templates/profile.html`, +6 lines `app.py` |
| validator (grok) | grok-4.5 | 45.5s | 3 | 32,250 | **ACCEPT**, 0 findings |
| validator (gemini) | gemini-3.1-pro-preview | 48.6s | 7 | 116,767 | **ACCEPT**, 0 findings |

Valid-RED: all 6 fail with behavioral `AssertionError` (404, route absent), not
import errors. GREEN verified by hash-locked gate (sha `7c5579fd`), full suite
96 passed. Both validators confirmed A3 (DB source of truth) and A5 (stale
session fails closed) directly.

### Chunk 3 — demo seed identity

Seed tuple at `models.py:431` → `("demo", "jpicard@starfleet.fed", "Jean-Luc
Picard")`. `username` stays `"demo"`. A1 integration test binds the Picard
identity in `GET /profile`.

| role | model | duration | num_turns | tokens | decision |
|---|---|---|---|---|---|
| test-author | claude-opus-5 | 131.7s | 20 | 7,946 | wrote `test/test_profile_seed.py` (3 tests); valid-RED, locked `8b0b2488` |
| executor | glm-5.2 | 28.9s | 8 | 17,354 | GREEN 3/3, first try; 1-line seed change in `models.py` |
| validator (grok) | grok-4.5 | 32.1s | 4 | 17,885 | **ACCEPT**, 0 findings |
| validator (gemini) | gemini-3.1-pro-preview | 58.6s | 11 | 168,252 | **ACCEPT**, 0 findings |

Valid-RED: mixed run (2 fail, 1 pass) is valid — login already works pre-change;
the locked assertion `seeded identity is Jean-Luc Picard` ran and failed. GREEN
verified (sha `8b0b2488`), full suite 99 passed, login-route regression clean
(27 passed).

## Cross-family validation results

**Both validators accepted every chunk — 6 of 6 ACCEPT, zero findings.** The
cross-family panel (xAI + Google, both ≠ the zhipu executor) surfaced no
correctness, security, or spec-deviation issues on any chunk. So the
`findings.jsonl` / `dispositions.jsonl` files are empty by construction, and the
per-position yield question (does the Nth reviewer find what the first missed?)
has no data to answer *on this slice* — a clean run is a real outcome, not a
gap, but it means this slice does not exercise the disagreement path.

The executor never retried: `glm-5.2` reached GREEN on the first attempt in all
three chunks. That matters for H3 — a cheap executor that needs three tries is
not cheap (PRD §14) — and here it needed one each.

Independent verification, not self-report: every executor claim of GREEN was
re-checked by the orchestrator against the **hash-locked** test gate, and every
validator run was followed by a `git status` stray-write check (KI-2). No run
was trusted on its own account.

## Operational findings

- **KI-1 — openai executor tier down the entire window.** `gpt-5.4-mini` /
  `gpt-5.4` failed with `num_turns:0`, 0 tokens, ~1.2s, no message; distinct
  from the Phase-2 autonomy gate. Resolved by human-approved substitution to
  `glm-5.2`, all separations preserved. Posterity A/B open.
- **KI-2 — validator has a write vector** via `Execute` at `--auto high` (needed
  to run pytest). Mitigated detectively by a post-run stray-write check every
  chunk; all six came back clean. A read-only test runner would fix it
  preventively.
- **KI-3 — the result envelope does not surface `providerLock` /
  `apiProviderLock`** in this CLI version; telemetry records the known pinned
  provider per commit-body-recipe §13 rather than an observed lock.
- **KI-4 — telemetry `role` enum omits `test-designer`** (PRD §7's fifth role);
  rows use the canonical name pending a SCHEMA `schema_version` bump.

## Tokens spent

13 role runs (12 successful + 1 failed openai attempt at 0 tokens). Total
**≈540.6k tokens** input+output.

| seat | tokens | share |
|---|---|---|
| validators (grok + gemini, 6 runs) | 453,918 | 84% |
| executor (glm-5.2, 3 runs) | 68,723 | 13% |
| test-designer (claude-opus-5, 3 runs) | 17,945 | 3% |

The headline is where cost lands: **the review panel, not the executor.** The
cheap executor was 13% of spend; the two-model validation panel was 84%, and
within it `gemini-3.1-pro-preview` alone was ~384k (it ingests far more context
per run than `grok-4.5` — 96k–165k input vs 16k–30k). This sharpens the H3
framing — role-tiering makes the *executor* cheap, but total loop cost is
dominated by how many validators run and how much context each pulls. The
per-seat fallback registry (Phase 3.1) is a cost lever on the executor seat;
the bigger cost lever is panel size and validator context discipline.

These are raw input+output token counts from the envelopes, not credits; H3's
formal cost claim is the PRD §13 three-arm comparison, not this single run.

## What Phase 3 leaves for Phase 4+

A complete loop demonstrated end to end: plan → execute → review on one real
slice. The framework is usable on real work. Phase 4 generalises across stacks;
Phase 5 hardens the loop's own invariants.

The human merge gate (PRD §6) remains: the slice is presented, not merged.

This run is the **control arm** for [Phase 3.1 — the degraded
loop](phase-3.1-degraded-loop.md), which violates invariant #1 at the
test-author seat to measure whether cross-family validation alone compensates.
See also [Phase 3 — the CI/CD evidence tier](phase-3-ci-tier.md) for what CI
surfaced after the merge.
