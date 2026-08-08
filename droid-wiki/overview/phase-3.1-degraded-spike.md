# Phase 3.1 — the degraded loop spike

**Phase 3 built the `/profile` feature with the full invariant set intact.
Phase 3.1 deliberately broke invariant #1 — let the same model family write
the tests *and* the code — to measure what happens when independence is
removed from the test-author seat.**

The question is operational, not theoretical: when frontier models are
exhausted or unavailable, can a cheap-tier model fill both the test-author
and executor seats with frontier models restricted to cross-family
validation only? This is the "token window" scenario — the framework hits a
budget or availability wall and must decide: stop (invariant #7) or degrade
gracefully?

## The one variable

Everything identical to Phase 3 except the **test-author seat**:

| Seat | Phase 3 (control) | Phase 3.1 (degraded) |
|---|---|---|
| Test-author | `claude-opus-5` (anthropic) | **`glm-5.2` (zhipu)** — same family as executor |
| Executor | `glm-5.2` (zhipu) | `glm-5.2` (zhipu) — unchanged |
| Validators | `grok-4.5` (xai) + `gemini-3.1-pro-preview` (google) | unchanged, still pinned |

This deliberately violates invariant #1 (test-author ≠ executor family).
Panel-acceptance rule for this run: **unanimous-accept required** (any REJECT
blocks).

## Headline result: panel-dependent, not a clean pass or a hard floor

The same-family test-author encoded exactly the test-independence bias
invariant #1 exists to prevent — in **1 of 3 chunks**. Two independent
backstops behaved differently:

1. The **deterministic hash-locked GREEN gate** (`verify-green.py`, which
   runs the locked test *in isolation*) caught it every time — it is
   family-blind and did not degrade.
2. **Cross-family validation split**: `grok-4.5` caught it (`REJECT_TEST`,
   correct attribution to the test, not the code); `gemini-3.1-pro-preview`
   ran the full suite, *explicitly observed the same standalone failure in
   writing*, then rationalized it away and returned `ACCEPT`.

So frontier cross-family **validation alone did not reliably compensate**
for the lost test-independence. A single-validator configuration using
gemini would have shipped the degraded test. A **multi-model panel with
any-reject-blocks did** compensate, because grok's REJECT dominated.

After one capped test-author retry (fed the cross-family finding), the
degraded seat restored independence and the panel reached unanimous ACCEPT.

## Per-chunk outcome

| Chunk | Same-family bias? | verify-green (standalone) | grok | gemini | Panel verdict |
|---|---|---|---|---|---|
| 1 r1 | **YES** — omitted `init_db` seeding fixture; test only green via suite order | **REFUSED** (`no such table: users`) | **REJECT_TEST** | ACCEPT (noted-but-dismissed) | **REJECTED** |
| 1 r2 (retry) | fixed: autouse `tmp_path` + `init_db()` | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |
| 2 | no (tests use `client` fixture → self-seeding) | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |
| 3 | no (model-layer test seeded standalone) | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |

The bias appeared **only** where a test exercised the model layer directly
with no `client` fixture to lazily initialize the DB — i.e. exactly the seam
where independent test authorship carries weight.

## The chunk-1 bias, precisely

The Phase 3 control test-author (claude-opus-5) wrote a self-contained test:

```python
@pytest.fixture(scope="module", autouse=True)
def seeded_demo_user():
    models.init_db()   # test seeds its own schema -> standalone-green
```

The degraded same-family author (glm-5.2) omitted any DB setup. Its test
passed **only** inside full-suite ordering (an earlier test's `client`/`app`
import initialized the shared temp DB); standalone it failed with
`sqlite3.OperationalError: no such table: users`.

It slipped past **valid-RED** because the `getattr(models,'get_user_profile',None)`
existence guard short-circuits and asserts *before* touching the DB — so at
RED time the DB path never ran. The defect only surfaced at **GREEN**, when
the implemented function actually queried the missing table.

## Token cost

| Seat | Control (Phase 3) | Degraded (Phase 3.1) | Delta |
|---|---|---|---|
| test-designer | 17,945 (3 runs) | 159,250 (4 runs) | +141,305 |
| executor | 68,723 (4 runs) | 94,042 (4 runs) | +25,319 |
| validator | 453,918 (6 runs) | 1,035,761 (8 runs) | +581,843 |
| **total** | **540,586 (13 runs)** | **1,289,053 (16 runs)** | **2.38x** |

The honest cost story is **structural**: the degraded loop is only cheaper
than the frontier-author control **if it passes first try**. A single
same-family test-independence miss erases the test-author savings by forcing
a full retry cycle plus extra validator passes. Cross-family token counts
are not directly comparable (per-provider cache accounting), so read the
multiplier as directional, not a price.

## What this fed back into the PRD

The finding was incorporated into PRD §17.6 as a binding rule: the
combination *deterministic standalone gate + fail-closed ≥2-family panel +
retry-on-reject* is the recommended hardening for **every** run, degraded
or not. Single-reviewer acceptance is treated as insufficient independence.
The cheap same-family author is classified as a **survivable degradation
for outages only**, not a default and not a saving.

This is the project's best example of the learning loop working as
intended — not the code loop, the *feedback* loop. An empirical finding
from a controlled experiment changed a PRD invariant in the same session.

## Method findings for the backlog

- **M1:** The `getattr`-existence-guard RED pattern can mask DB/fixture-
  dependency defects until GREEN. valid-RED could optionally run the locked
  test in a pristine isolated environment to surface environmental coupling
  earlier.
- **M2 (KI-4 recurs):** `role: "test-designer"` still not in SCHEMA.md's
  enum at the time; later fixed in Phase 3.2's v1→v2 schema bump.
- **M3:** Worktree isolation required copying the untracked `.factory/`
  (hook registration) and symlinking `.venv`, and pointing the hook at a
  phase-3.1-specific locks dir so it would not falsely block on Phase 3's
  locks.
- **M4:** glm-5.2 chunk-2 test-author exec exited on the `--auto low`
  autonomy gate *after* writing the file. Autonomy-gate behavior is
  family-dependent; the deterministic gates remained the source of truth.

## Related: per-seat fallback registry

During Phase 3 chunk 1 the planned openai executor (`gpt-5.4-mini`) was
down for hours (KI-1). The human approved substituting `glm-5.2`. This
raised the idea of a first-class **per-seat fallback registry**: each seat
lists candidate model IDs with family tags; the orchestrator resolves the
first available candidate that still satisfies separation constraints.

This is **resilience, not a panel** — executor fallback buys availability
and cost-tiering, not independence. The panel belongs at the review seat
only. See `phase-3.1/SPIKE.md` for the full design note.
