# Phase 3.1 — Degraded Loop Spike

Phase 3.1 asked what happens when the adversarial loop is deliberately degraded. The one variable was the test-author seat: instead of `claude-opus-5` (anthropic), it used `glm-5.2` (zhipu), the same family as the executor. This violates invariant #1 — test-author and executor must be different families — and measures whether the remaining backstops can compensate.

The branch was `factory/phase-3.1-degraded`, isolated from the pilot base at `8a10711d`. The control arm was the Phase 3 run recorded in `/Users/factory/work/adversarial-sprint-dev/telemetry/runs.jsonl` (~541k tokens total).

## Key source files

| File | Purpose |
|---|---|
| `/Users/factory/work/adversarial-sprint-dev/phase-3.1/SPIKE.md` | Hypothesis, method, and relationship to Phase 3 |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.1/RESULTS.md` | Full numbers and per-chunk outcome |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.1/prompts/` | Path-adapted copies of the Phase 3 prompts |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.1/prompts/chunk1-test-author-retry.md` | Retry prompt fed the cross-family finding |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.1/build-evidence/` | Envelopes, including round-1 preserved as `*-r1-*` |
| `/Users/factory/work/adversarial-sprint-dev/phase-3.1/gen-telemetry.py` | Telemetry generator |

## The one variable

| Seat | Phase 3 (control) | Phase 3.1 (degraded) |
|---|---|---|
| Test-author | `claude-opus-5` (anthropic) | `glm-5.2` (zhipu) — same family as executor |
| Executor | `glm-5.2` (zhipu) | `glm-5.2` (zhipu) — unchanged |
| Validators | `grok-4.5` (xAI) + `gemini-3.1-pro-preview` (google) | Unchanged |

## Headline result

The outcome was **panel-dependent**, not a clean pass or a hard floor.

- The same-family test-author encoded a test-independence bias in **chunk 1 only**: it omitted the standalone DB-seeding fixture that the frontier control included. Chunks 2 and 3 matched the control because they used the `client` fixture.
- The **deterministic gate** (`/Users/factory/work/adversarial-sprint-dev/phase-1/scripts/verify-green.py` running the locked test in isolation) caught the bias every time. It is family-blind and did not degrade.
- **Cross-family validation split:** `grok-4.5` caught it (`REJECT_TEST`, correctly attributed to the test); `gemini-3.1-pro-preview` observed the identical standalone failure in writing but dismissed it and returned `ACCEPT`. A single-gemini configuration would have shipped the weakened test.
- After **one capped test-author retry** fed the cross-family finding, the cheap seat restored test independence (with a `tmp_path` + `init_db()` fixture that was arguably more robust than the control) and the panel reached unanimous `ACCEPT`.

## Per-chunk outcome

| Chunk | Same-family bias? | `verify-green` standalone | `grok-4.5` | `gemini-3.1-pro-preview` | Panel verdict |
|---|---|---|---|---|---|
| 1 r1 | Yes — omitted `init_db` seeding | REFUSED (`no such table: users`) | REJECT_TEST | ACCEPT (noted but dismissed) | REJECTED |
| 1 r2 (retry) | Fixed | ACCEPTED | ACCEPT | ACCEPT | ACCEPT |
| 2 | No | ACCEPTED | ACCEPT | ACCEPT | ACCEPT |
| 3 | No | ACCEPTED | ACCEPT | ACCEPT | ACCEPT |

## The chunk-1 bias, precisely

The Phase 3 test-author wrote a self-contained test with a module-scoped autouse fixture that called `models.init_db()`. The degraded same-family author omitted DB setup. Its test passed only inside the full suite ordering, where an earlier test's `client` fixture initialized the shared temp DB. Standalone it failed with `sqlite3.OperationalError: no such table: users`.

It slipped past valid-RED because the existence guard `getattr(models, 'get_user_profile', None)` asserted before touching the DB. The defect only surfaced at GREEN, when the implemented function queried the missing table. The lesson: the `getattr`-existence-guard RED pattern can mask DB/fixture dependency defects until GREEN.

## Cost delta

| Seat | Control (Phase 3) | Degraded (Phase 3.1) | Δ |
|---|---|---|---|
| test-designer | 17,945 tokens | 159,250 tokens | +141,305 |
| executor | 68,723 tokens | 94,042 tokens | +25,319 |
| validator | 453,918 tokens | 1,035,761 tokens | +581,843 |
| **total** | **540,586 tokens (13 runs)** | **1,289,053 tokens (16 runs)** | **+748,467 (2.38×)** |

About half the delta came from the chunk-1 rejection and retry, which forced a fresh test-author, executor, and two validators to run twice. Validator token counts are also noisy across families (gemini reports much larger `input_tokens` than grok for comparable work), so the 2.38× figure should be read as structural rather than exact. The real lesson: the degraded loop only saves money if it passes first try.

## Implications

- **Invariant #1 is not a tunable knob you can silently drop.** Dropping independent-family test authorship reintroduced the exact class of defect the invariant targets.
- **It is not an absolute hard floor either**, provided two conditions hold: (a) a family-blind deterministic gate that runs locked tests in isolation, and (b) a multi-model validation panel with any-reject-blocks semantics.
- **The documented fallback is conditional:** cheap same-family authorship plus a standalone gate plus a ≥2-model fail-closed panel plus mandatory retry-on-reject. Drop either backstop and the degradation becomes silent.

## Follow-up experiments

The spike proposes a program of low-stakes slices to grow the sample size before relaxing §17.6: repeat the degraded loop across N≥10 slices, measure the panel-split rate, track the retry-cost curve, and A/B the backstops by removing each one in turn. The framework should strengthen first and relax only on evidence.

## Related idea: per-seat fallback registry

During Phase 3 the openai executor was unavailable. Human approval substituted `glm-5.2`. Phase 3.1 raises the idea of a small ordered fallback registry per non-separation-critical seat (planner, executor), resolved by a collision guard that fails closed on `unknown`. This is a resilience feature, not a review panel; validator seats stay pinned because family multiplicity there buys independence, not availability.
