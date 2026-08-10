# Phase 3.1 — the budget-degraded loop (same-family test-author)

**Phase 3 ran the full loop with every invariant intact and stopped at the human
merge gate. Phase 3.1 asks the question that comes next: what happens when the
independent-family test-author is unavailable and the only seat you can fill is
the executor's own family?** This is the "token window" scenario — a frontier
model is exhausted or down, and the framework must decide whether to stop
(invariant #7) or degrade with a recorded exception.

The experiment deliberately violates invariant #1 (test-author ≠ executor
family) at exactly one seat — the test-author — while keeping the cross-family
validators pinned. It ran against the frozen Phase-3 base (same plan, same
3-chunk structure, same accepted assertions, same lock/RED/GREEN/validate
cycle). The money question: did the pinned cross-family validators (grok +
gemini) catch the same-family biases the lost test-independence let through?

The honest answer is **neither clean graceful-degradation nor a hard floor — it
was panel-dependent**, which is a more useful result than either hypothesis
predicted. A single-gemini configuration would have shipped the weakened test.
A two-model panel with any-reject-blocks did not. The deterministic standalone
gate caught it every time, family-blind, and is the cheapest and most reliable
backstop of the three. This evidence amended PRD §17.6 (see below).

Full write-up with numbers: `phase-3.1/RESULTS.md`. Design rationale:
`phase-3.1/SPIKE.md`. Execution recipe: `phase-3.1/RUN-PROMPT.md`. Telemetry
rows: `telemetry/runs.jsonl`, `phase == "phase-3.1"`.

## The one variable

Everything identical to Phase 3 except the test-author seat:

| Seat | Phase 3 (control) | Phase 3.1 (this run) |
|---|---|---|
| Test-author | `claude-opus-5` (anthropic) | **`glm-5.2` (zhipu)** — same family as executor |
| Executor | `glm-5.2` (zhipu) | `glm-5.2` (zhipu) — unchanged |
| Validators | `grok-4.5` (xai) + `gemini-3.1-pro-preview` (google) | **unchanged, still pinned** |

This is the exact failure mode invariant #1 exists to prevent: test-author =
executor family. The validators were deliberately left pinned cross-family —
the whole experiment is whether frontier cross-family *validation alone*
compensates for the lost test-independence. No second variable was introduced
(that is Phase 3.2's territory). Panel-acceptance rule for this run:
**unanimous-accept required** (any REJECT blocks).

## Headline result

**The same-family test-author encoded exactly the test-independence bias
invariant #1 targets — in 1 of 3 chunks.** Two independent backstops behaved
differently:

1. The **deterministic hash-locked GREEN gate** (`verify-green.py`, which runs
   the locked test *in isolation*) caught it every time. It is family-blind and
   did not degrade.
2. **Cross-family validation split.** `grok-4.5` caught it (`REJECT_TEST`,
   correctly attributed to the test, not the code). `gemini-3.1-pro-preview`
   ran the full suite, *explicitly observed the same standalone failure in
   writing*, then rationalized it away and returned `ACCEPT`.

So frontier cross-family **validation alone did not reliably compensate** for
the lost test-independence: a single-validator configuration using gemini would
have shipped the degraded test. A **multi-model panel with any-reject-blocks
did** compensate, because grok's REJECT dominated. After one capped test-author
retry (fed the cross-family finding), the degraded seat restored independence
and the panel reached unanimous ACCEPT.

## Per-chunk outcome

| Chunk | Same-family bias? | verify-green (standalone) | grok | gemini | Panel verdict |
|---|---|---|---|---|---|
| 1 (read model) r1 | **YES** — omitted `init_db` seeding fixture; test only green via suite order | **REFUSED** (`no such table: users`) | **REJECT_TEST** | ACCEPT (noted-but-dismissed) | **REJECTED** |
| 1 (read model) r2 (retry) | fixed: autouse `tmp_path` + `init_db()` | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |
| 2 (route + template) | no (tests use `client` fixture, self-seeding) | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |
| 3 (seed identity) | no (model-layer test seeded standalone) | ACCEPTED | ACCEPT | ACCEPT | **ACCEPT** |

Chunks 2 and 3 matched the Phase-3 control (0 findings). The bias appeared
**only** where a test exercised the model layer directly with no `client`
fixture to lazily initialize the DB — i.e. exactly the seam where independent
test authorship carries weight.

## The chunk-1 bias, precisely

The Phase-3 control test-author (claude-opus-5) wrote a self-contained test:

```python
@pytest.fixture(scope="module", autouse=True)
def seeded_demo_user():
    models.init_db()   # test seeds its own schema -> standalone-green
```

The degraded same-family author (glm-5.2) omitted any DB setup. Its test passed
**only** inside full-suite ordering — an earlier test's `client`/`app` import
initialized the shared temp DB; standalone it failed with
`sqlite3.OperationalError: no such table: users`.

It slipped past **valid-RED** because the `getattr(models,'get_user_profile',None)`
existence guard short-circuits and asserts *before* touching the DB — so at RED
time the DB path never ran. The defect only surfaced at **GREEN**, when the
implemented function actually queried the missing table. (Method finding M1:
the `getattr`-guard RED pattern can mask DB-dependency defects until GREEN.)

## Control vs degraded — the numbers

All figures verified against `telemetry/runs.jsonl` (phase-3 and phase-3.1
rows), not transcribed from the run agent's report.

### Token cost

| Seat | Control (phase-3) | Degraded (phase-3.1) | Delta |
|---|---|---|---|
| test-designer | 17,945 (3 runs) | 159,250 (4 runs) | +141,305 |
| executor | 68,723 (4 runs) | 94,042 (4 runs) | +25,319 |
| validator | 453,918 (6 runs) | 1,035,761 (8 runs) | +581,843 |
| **total** | **540,586 (13 runs)** | **1,289,053 (16 runs)** | **+748,467 (2.38x)** |

### Where cost lands

| Seat | Control share | Degraded share |
|---|---|---|
| validators | 84% | 80% |
| executor | 13% | 7% |
| test-designer | 3% | 12% |

The headline cost story held in both runs: **the review panel, not the
executor, dominates spend.** The degraded run's test-designer share rose (3% to
12%) because the retry added a full extra test-author pass, but validators
remained the cost center at 80%.

### Findings

| | count | severity | category |
|---|---|---|---|
| Phase 3 control | 0 | — | — |
| Phase 3.1 degraded (round 1) | 1 | blocking | test-independence / test-quality |
| Phase 3.1 degraded (round 2) | 0 | — | — |

The single finding was surfaced by **1 of 2** panel members (grok), first
position in the panel. Gemini recorded the same symptom but did not treat it as
blocking. After the capped retry, round-2 findings returned to 0.

### Caveats on the 2.38x cost number (do not over-read it)

- ~half the delta is the **chunk-1 rejection + retry** (8 extra runs the
  control never paid): a fresh test-author, executor, and two validators,
  twice.
- Validator input-token counts are **noisy and family-skewed**: gemini reports
  very large `input_tokens` (one run 478k) where grok reports ~17-43k for
  comparable work. This reflects differing input-vs-cache accounting across
  providers (KI-3 territory), not 30x more "thinking." Cross-family token sums
  are a rough signal, not an apples-to-apples price.
- The honest cost story is **structural**: the degraded loop is only cheaper
  than the frontier-author control **if it passes first try**. A single
  same-family test-independence miss erases the test-author savings by forcing a
  full retry cycle plus extra validator passes.

## Did the final code pass the same acceptance criteria?

Yes, after one retry. All three locked tests are standalone-GREEN under the
hash-locked gate; full suite **98 passed**; A1 satisfied; per-chunk `git diff`
scope clean; no stray writes across all 8 validator runs (KI-2 check clean).
The **implementation** (executor) was correct and unaffected throughout — the
only defect was in the degraded author's *test*.

## Verdict — what this means for invariant #1

**Invariant #1 is not a tunable knob you can silently drop.** Dropping
independent-family test authorship reintroduced precisely the class of defect
the invariant targets. It is also not an absolute hard floor *provided* two
conditions hold: (a) a family-blind deterministic gate that runs locked tests
in isolation, and (b) a **multi-model** validation panel with
any-reject-blocks. Remove either backstop and the degraded loop ships the
weakened test — gemini alone did.

This is **graceful-degradation with mandatory backstops**, not free
degradation. The documented fallback is conditional:

- **acceptable:** cheap same-family authorship + deterministic standalone gate +
  cross-family panel (>=2 families, fail-closed) + mandatory retry-on-reject.
- **not acceptable:** cheap authorship + frontier validation (singular) without
  the deterministic gate. A single-validator panel is explicitly insufficient
  for degrade-authored code.

The cheap seat needed the panel's feedback to self-correct; it did correct well
— the retry fixture was arguably more robust than the control's, using
`tmp_path` isolation rather than a module-scoped fixture.

## What this fed back into the PRD

This spike's evidence amended **PRD §17.6** ("Degrading the test-author family
invariant is an outage fallback, not a cost lever"). The amendment codifies:

1. The default is **not to degrade**. If an independent-family test-author
   cannot be seated, invariant #7 governs: **stop**.
2. When degradation is a documented response to a confirmed outage, **both**
   backstops are mandatory and non-negotiable: the family-blind deterministic
   standalone gate, and a fail-closed >=2-family panel with retry-on-reject.
3. A single-validator panel is **explicitly insufficient** for
   degrade-authored code.
4. The combination (gate + panel + retry) is the recommended hardening for
   **every** run, degraded or not.

The standing posture is deliberately strict on a sample size of 1: strengthen
first, relax only on evidence. §17.6 is bound by §17.2 and by invariants #1 and
#7. See `PRD.md` §17.6 for the full text.

## Implications for §13 efficacy and Phase 5 calibration

This run feeds the §13 efficacy surface as **evidence, not intuition**:

- Same-family authorship raised the blocking-finding rate from 0 to 1 over
  three chunks, all at the model-layer/no-fixture seam.
- **Panel position matters** — the catch was 1-of-2, so panel size >= 2 with
  fail-closed semantics is load-bearing here. This is the
  `first_seen_in_panel_position` signal Phase 5 will accumulate.
- The **deterministic standalone gate** is the cheapest and most reliable
  backstop and should not be treated as redundant to the panel.

## Method findings (for the backlog)

- **M1:** The `getattr`-existence-guard RED pattern can mask DB/fixture
  dependency defects until GREEN, because it asserts before exercising the
  subject. valid-RED could optionally run the locked test in a pristine
  isolated environment to surface environmental (non-behavioral) coupling
  earlier.
- **M2 (KI-4 recurs):** `role: "test-designer"` still not in `SCHEMA.md`'s
  enum.
- **M3:** Worktree isolation required copying the untracked `.factory/` (hook
  registration) and symlinking `.venv`, and pointing the hook at a
  phase-3.1-specific locks dir (`ADVERSARIAL_SPRINT_LOCKS_DIR`) so it would not
  falsely block on Phase 3's locks or clobber them. Recorded so the next spike
  does not rediscover it.
- **M4:** glm-5.2 chunk-2 test-author exec exited on the `--auto low` autonomy
  gate *after* writing the file (`is_error=true`, artifact intact). The control
  (claude) did not. Autonomy-gate behavior is family-dependent; the
  deterministic gates remained the source of truth.

## Follow-up experiments (grow n before relaxing §17.6)

§17.6 is deliberately strict on a **sample size of 1**. The way to earn any
relaxation is data, not argument. Proposed program, run on **low-stakes
features only** (read-only endpoints, copy/seed changes, non-security display
logic — the same risk tier as this `/profile` slice) so a missed defect is
cheap:

- **Repeat the degraded loop across N>=10 low-stakes slices.** Measure how
  often the same-family author introduces a test-independence (or other)
  defect, and where (the model-layer/no-fixture seam is the current suspect).
- **Measure the panel-split rate.** Here it was 1-of-2 (grok caught, gemini
  missed). Is that stable, model-pair-specific, or defect-category-specific?
  This is the number that decides whether ">=2 families, fail-closed" is
  sufficient or needs >=3.
- **Track the retry-cost curve.** Does the degraded loop ever come out cheaper
  net of retries, or is the first-pass-miss tax structural? Settle the
  token-accounting skew with same-family-normalized cost where possible.
- **A/B the backstops.** Re-run with each backstop removed in turn (gate-only;
  panel-only) to confirm neither alone is sufficient — the current claim rests
  on one observation.
- **Vary the cheap seat.** One cheap family in both seats (worst case, tested
  here) vs two *different* cheap families (middle ground) — does splitting the
  cheap seats recover independence without frontier authorship?

Gate on relaxing §17.6: a stable, low defect-escape rate **and** a panel-split
rate that the fail-closed >=2-family rule provably covers, across enough
low-stakes slices to matter.

## Relationship to Phase 3 and Phase 3.2

Phase 3 is the **control arm** — the full invariant set intact (frontier
test-author, cheap executor, frontier validators). Running 3.1 before 3
invalidates the comparison; there is no clean baseline to measure against. See
[Phase 3 — the end-to-end execution slice](phase-3-execution-slice.md) for the
control run, and [Phase 3 — the CI/CD evidence tier](phase-3-ci-tier.md) for
what happened when the merged slice went through an actual CI/CD pipeline.

Phase 3.2 is a **different variable**: it externalizes the deterministic
evidence tier (tests, lint, security scans) into CI rather than testing whether
the model panel alone compensates for a weakened invariant. The two experiments
are complementary, not overlapping.

## Reproduction

- Prompts (path-adapted copies of `phase-3/prompts/`, repo path swapped to the
  worktree — the only change): `phase-3.1/prompts/`.
- Retry prompt with the verbatim cross-family finding:
  `phase-3.1/prompts/chunk1-test-author-retry.md`.
- Envelopes: `phase-3.1/build-evidence/` (round-1 preserved as `*-r1-*`).
- Telemetry recipe: `phase-3.1/gen-telemetry.py` (idempotent per phase; numbers
  read from envelopes). Rows: `telemetry/runs.jsonl`, `phase == "phase-3.1"`.
- Gate logs: `chunk{1,2,3}-verify-green*.log`, `chunk1-fullsuite.log`.

## Known issues referenced

- **KI-1** — openai executor tier unavailable during Phase 3 (origin of the
  fallback-registry idea; see the execution-slice page).
- **KI-2** — validator write vector via `Execute` at `--auto high`; mitigated
  by post-run stray-write checks (clean across all 8 Phase-3.1 validator runs).
- **KI-3** — envelope does not surface `providerLock` / `apiProviderLock`;
  telemetry records the known pinned provider. Cross-family token sums are
  therefore noisy (the 2.38x caveat above).
- **KI-4** — telemetry `role` enum omits `test-designer`; rows use the
  canonical name pending a schema bump (M2 above).
