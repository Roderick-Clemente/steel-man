# Phase 3.1 — RESULTS: budget-degraded loop (cheap test-author + executor, frontier validation only)

**Status:** COMPLETE. All 3 chunks run under the degraded seat; presented for the
human merge gate; **not merged** (no self-merge).

**Branch:** `factory/phase-3.1-degraded` (isolated worktree at pilot base
`8a10711d`). **Control arm:** Phase 3 (`telemetry/runs.jsonl`, phase-3 rows).

## The one variable

Everything identical to Phase 3 except the **test-author seat**:

| Seat | Phase 3 (control) | Phase 3.1 (this run) |
|---|---|---|
| Test-author | `claude-opus-5` (anthropic) | **`glm-5.2` (zhipu)** — same family as executor |
| Executor | `glm-5.2` (zhipu) | `glm-5.2` (zhipu) — unchanged |
| Validators | `grok-4.5` (xai) + `gemini-3.1-pro-preview` (google) | **unchanged, still pinned** |

This deliberately violates invariant #1 (test-author ≠ executor family) at the
test-author seat. Panel-acceptance rule recorded for this run: **unanimous-accept
required** (any REJECT blocks). No second variable was introduced.

## Headline result

**Mixed / panel-dependent, not a clean pass and not a hard floor.**

The same-family test-author encoded exactly the test-independence bias invariant
#1 exists to prevent (chunk 1). Two independent backstops behaved differently:

1. The **deterministic hash-locked GREEN gate** (`verify-green.py`, which runs the
   locked test *in isolation*) caught it every time — it is family-blind and did
   not degrade.
2. **Cross-family validation was split**: `grok-4.5` caught it (`REJECT_TEST`,
   correct attribution to the test, not the code); `gemini-3.1-pro-preview` ran
   the full suite, *explicitly observed the same standalone failure in writing*,
   then rationalized it away and returned `ACCEPT`.

So frontier cross-family **validation alone did not reliably compensate** for the
lost test-independence: a single-validator configuration using gemini would have
shipped the degraded test. A **multi-model panel with any-reject-blocks did**
compensate, because grok's REJECT dominated. After one capped test-author retry
(fed the cross-family finding), the degraded seat restored independence and the
panel reached unanimous ACCEPT.

## Per-chunk outcome

| Chunk | Same-family bias? | verify-green (standalone) | grok | gemini | Panel verdict |
|---|---|---|---|---|---|
| 1 (read model) r1 | **YES** — omitted `init_db` seeding fixture; test only green via suite order | **REFUSED** (`no such table: users`) | **REJECT_TEST** | ACCEPT (noted-but-dismissed) | **REJECTED** |
| 1 (read model) r2 (retry) | fixed: autouse `tmp_path` + `init_db()` | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |
| 2 (route + template) | no (tests use `client` fixture → self-seeding) | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |
| 3 (seed identity) | no (model-layer test seeded standalone) | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |

Chunk 2/3 matched the Phase 3 control (0 findings). The bias appeared **only**
where a test exercised the model layer directly with no `client` fixture to
lazily initialize the DB — i.e. exactly the seam where independent test
authorship carries weight.

## The chunk-1 bias, precisely

The Phase 3 control test-author (claude-opus-5) wrote a self-contained test:

```python
@pytest.fixture(scope="module", autouse=True)
def seeded_demo_user():
    models.init_db()   # test seeds its own schema -> standalone-green
```

The degraded same-family author (glm-5.2) omitted any DB setup. Its test passed
**only** inside full-suite ordering (an earlier test's `client`/`app` import
initialized the shared temp DB); standalone it failed with
`sqlite3.OperationalError: no such table: users`.

It slipped past **valid-RED** because the `getattr(models,'get_user_profile',None)`
existence guard short-circuits and asserts *before* touching the DB — so at RED
time the DB path never ran. The defect only surfaced at **GREEN**, when the
implemented function actually queried the missing table. (Finding for the method:
the `getattr`-guard RED pattern can mask DB-dependency defects until GREEN.)

## Deliverable questions, answered with numbers

**1. Did the same-family tests encode biases the validators caught? Which ones?**
Yes — one blocking test-independence bias (chunk 1: missing standalone DB seed).
Caught by the deterministic gate always; caught by cross-family validation only
partially (1 of 2 validators). Chunks 2 and 3 encoded no bias.

**2. Did validator findings differ vs Phase 3 (0 findings)?**
Yes.

| | count | severity | category |
|---|---|---|---|
| Phase 3 control | 0 | — | — |
| Phase 3.1 degraded | 1 (round 1) | blocking | test-independence / test-quality |

The finding was surfaced by **1 of 2** panel members (grok), first-position in
the panel; gemini recorded the same symptom but did not treat it as blocking.
After the capped retry, round-2 findings returned to 0.

**3. Did the final code pass the same acceptance criteria?**
Yes, after one retry. All three locked tests are standalone-GREEN under the
hash-locked gate; full suite **98 passed**; A1 satisfied; per-chunk `git diff`
scope clean; no stray writes across all 8 validator runs (KI-2 check clean).
The **implementation** (executor) was correct and unaffected throughout — the
only defect was in the degraded author's *test*.

**4. Token-cost delta vs the ~541k control, per seat.**

| Seat | Control (phase-3) | Degraded (phase-3.1) | Δ |
|---|---|---|---|
| test-designer | 17,945 (3 runs) | 159,250 (4 runs) | +141,305 |
| executor | 68,723 (4 runs) | 94,042 (4 runs) | +25,319 |
| validator | 453,918 (6 runs) | 1,035,761 (8 runs) | +581,843 |
| **total** | **540,586 (13 runs)** | **1,289,053 (16 runs)** | **+748,467 (2.38x)** |

**Caveats on the cost number (important — do not over-read the 2.38x):**
- ~half the delta is the **chunk-1 rejection + retry** (8 extra runs the control
  never paid): a fresh test-author, executor, and two validators, twice.
- Validator input-token counts are **noisy and family-skewed**: gemini reports
  very large `input_tokens` (one run 478k) where grok reports ~17–43k for
  comparable work; this reflects differing input-vs-cache accounting across
  providers (KI-3 territory), not 30x more "thinking." Cross-family token sums
  are therefore a rough signal, not an apples-to-apples price.
- The honest cost story is **structural**: the degraded loop is only cheaper than
  the frontier-author control **if it passes first try**. A single same-family
  test-independence miss erases the test-author savings by forcing a full
  retry cycle plus extra validator passes.

## Implications

- **Invariant #1 is not a tunable knob you can silently drop.** Dropping
  independent-family test authorship reintroduced precisely the class of defect
  the invariant targets. It is also not an absolute hard floor *provided* two
  conditions hold: (a) a family-blind deterministic gate that runs locked tests
  in isolation, and (b) a **multi-model** validation panel with any-reject-blocks.
  Remove either and the degraded loop ships the weakened test (gemini alone did).
- **Invariant #7 boundary.** A documented, measured degradation is defensible
  *only* as "cheap same-family authorship + deterministic standalone gate +
  cross-family panel + mandatory retry-on-reject," not as "cheap authorship +
  frontier validation." The cheap seat needed the panel's feedback to self-correct;
  it did correct well (the retry fixture was arguably more robust than the
  control's, using `tmp_path` isolation).
- **§13 efficacy surface / Phase 5 calibration.** Feed in: (i) same-family
  authorship raises blocking-finding rate from 0 → 1 over three chunks, all at
  the model-layer/no-fixture seam; (ii) panel position matters — the catch was
  1-of-2, so panel size ≥ 2 with fail-closed semantics is load-bearing here;
  (iii) the deterministic standalone gate is the cheapest and most reliable
  backstop and should not be treated as redundant to the panel.

## Method findings (for the backlog)

- **M1:** The `getattr`-existence-guard RED pattern can mask DB/fixture-dependency
  defects until GREEN, because it asserts before exercising the subject. valid-RED
  could optionally run the locked test in a *pristine* isolated environment to
  surface environmental (non-behavioral) coupling earlier.
- **M2 (KI-4 recurs):** `role: "test-designer"` still not in `SCHEMA.md`'s enum.
- **M3:** Worktree isolation required copying the untracked `.factory/`
  (hook registration) and symlinking `.venv`, and pointing the hook at a
  **phase-3.1-specific locks dir** (`ADVERSARIAL_SPRINT_LOCKS_DIR`) so it would
  not (a) falsely block on Phase 3's locks or (b) clobber them. Recorded so the
  next spike does not rediscover it.
- **M4:** glm-5.2 chunk-2 test-author exec exited on the `--auto low` autonomy
  gate *after* writing the file (is_error=true, artifact intact). The control
  (claude) did not. Autonomy-gate behavior is family-dependent; the deterministic
  gates remained the source of truth.

## Reproduction

- Prompts (path-adapted copies of `phase-3/prompts/`, repo path swapped to the
  worktree — the only change): `phase-3.1/prompts/`.
- Retry prompt with the verbatim cross-family finding: `phase-3.1/prompts/chunk1-test-author-retry.md`.
- Envelopes: `phase-3.1/build-evidence/` (round-1 preserved as `*-r1-*`).
- Telemetry recipe: `phase-3.1/gen-telemetry.py` (idempotent per phase; numbers
  read from envelopes). Rows: `telemetry/runs.jsonl`, `phase == "phase-3.1"`.
- Gate logs: `chunk{1,2,3}-verify-green*.log`, `chunk1-fullsuite.log`.
