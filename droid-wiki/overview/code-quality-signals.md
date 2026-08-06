# Code-quality signals — beyond the bug

**The framework's headline is correctness-on-the-hidden-tests**;
secondary metrics live in [`by-the-numbers.md`](../by-the-numbers.md).
This page is the third tier: dimensions the loop surfaces even when no
specific defect has been written down.

The §13 efficacy lever is not "count the bugs". The lever is *"how
many dimensions of code quality is the loop measuring on every
slice that runs through it"*. Five of those dimensions are
operationalised already; the rest are queued.

## 5 measurable signals beyond "we found a bug"

### 1. Placebiticity — would the test catch the no-op?

The locked test is **non-placebic** iff it would not pass on a no-op
implementation. Phase 1's locked test passes [`method/sprint-template.md`
items 6–11](../method/sprint-template.md):

- **Real Werkzeug behavior.** The test sends `GET /llms.txt` through
  Flask's `client` fixture. Werkzeug's `mimetype="text/plain"`
  handler appends `charset=utf-8` once; the param form appends it twice.
  Werkzeug does this for real, not in a stub.
- **No SUT mock.** The test does not patch `api/llms_txt`. It calls
  the deployed endpoint.
- **Real client GET.** No runner-level mock of Flask's request-handling
  path.
- **Contracts that catch the doubled-charset defect on actual Werkzeug
  output.** Asserting `charset_count == 1` on the header value `chunks`.

A test that mocks its own subject, asserts on body text, or verifies a
return code without behavioral evidence is *placebic*. The locked test
classifier flags placebiticity as a quality-rubric fail (see
[`findings/silent-green.md`](../findings/silent-green.md) for the upstream
case study). The phrase-in-pass-output check we removed from
`verify-green.py` is exactly the workaround for a placebic test.

Catch in the wild: Phase 0 Probe 1 had a "test" that passed because it
asserted on a return code without exercising the system's
response-body path. The classifier rejected it.

### 2. Cross-family calibration divergence

When the panel issues a decision for the same slice, the overlap
between findings is partial. Phase 1 case study:

| defect family | Grok caught | Gemini caught |
|---|---|---|
| Hook security bypass (glob short-circuit, `MultiEdit` missing) | no | yes (×3) |
| Valid-red signature gap (service unavailable / empty selection) | yes | no |
| Case-sensitivity disagreement between red and green checks | yes | no |
| Ledger-completeness (recorded RED not mechanically re-run via script) | yes | no |
| Hook lock-manifest unprotected (round-1 finding) | no | yes |

The signal: a single-family reviewer misses **3 of 5** defects. This
is the calibration-divergence metric captured as
`first_seen_in_panel_position` in `telemetry/SCHEMA.md`.
When the same defect is found by both reviewers, it is recorded with
`first_seen_in_panel_position=0` ("shared-not-unique"). When only one
reviewer reports it, the position is the reviewer index.

The §13 efficacy subset: a panel's yield on a slice equals the union
of its members' yields. Calibration divergence (the unique-to-one
count) measures how much each family brings that the others miss.
A future efficacy target: maximise yield per marginal-cost reviewer.

### 3. Spec-compliance coverage per PRD exit criterion

Findings cite `criterion: spec-compliance | phase-0.5-handoff | test-quality`.
The mapping is forced by the reviewer rubric in
[`method/sprint-template.md`](../method/sprint-template.md).

Phase 1 covered all four PRD §11 exit criteria (a–d); reviewers cited
specific sub-criteria per finding. The audit trail is per-criterion,
not per-glob. This makes it possible to compute *"% PRD §11 exits
matched in a single round"* — the kind of metric that catches coverage
holes (e.g., "rubric (a) was touched in 0 of 12 rounds").

For the §13 efficacy subset, we want to track per-PRD-exit-criterion
coverage over time:

- Number of rounds where criterion X had at least one finding.
- Number of findings per criterion per round.
- Trend lines: is the framework converging on coverage or oscillating?

### 4. Time-to-correctness — RED→GREEN path

The recorded slice's path:

1. **test-designer** wrote the locked test (one turn on a flight).
2. RED observed via designer's envelope: pytest exit non-zero, error
   string contains the lock's `accepted_assertion` phrase.
3. **lock** written → sha256 recorded.
4. **executor** wrote the minimal implementation: `mimetype="text/plain"`
   (or the corresponding content-type header) → Werkzeug sets
   `Content-Type: text/plain; charset=utf-8` — one token.
5. GREEN verified: sha256 unchanged (the test was not edited),
   pytest exit 0, the same assertion phrase still in the test source.

End-to-end: minutes, not hours. Compare with the time-to-fix on a
human reviewer's first-pass hypothetical:

> "Could you change `api/llms_txt.py` to use `text/plain` without the
> doubled-charset?"

→ ask one human reviewer, wait 30–60 minutes, get a one-line fix,
then run a test suite. The phased-loop path compresses this. The
metric is *minutes per RED-to-GREEN cycle* with the lock-hash
guarantee.

Important nuance: this metric varies by slice complexity. Useful for
*within-slice* trend lines, not as an absolute target.

### 5. Cost per finding — and the marginal cost per extra reviewer

Tokens in / findings-out is the §13 efficacy lever. Phase 1 case study
totals:

- **3 rounds × 2 panels = 6 reviewer sessions.**
- ~3.4M input tokens (mostly cache reads of the same slice tree).
- ~98k output tokens (model text).
- ~22 findings across all 6 sessions (major + minor + nit).
- **Cost per finding: ~155k tokens in**, driven by cache reuse.

Marginal cost of the second reviewer per round: ~250k–500k input
tokens. Marginal benefit: **3 of 5 defects caught** (security family)
were caught only by the second reviewer (Gemini, in this slice).
The marginal-cost-vs-marginal-yield curve is the efficacy ROI.

## Where these numbers live

- **Tokens, durations, num_turns:** `telemetry/runs.jsonl`
  (one row per reviewer invocation).
- **Findings with `first_seen_in_panel_position`:** `telemetry/findings.jsonl`.
- **Dispositions** (fixed / wontfix / deferred / reverted): `telemetry/dispositions.jsonl`.
- **Aggregate queries** (per-reviewer yield, fix-rate-by-severity,
  cost-per-finding): `telemetry/aggregate.py`.
- **Summary numbers:** [`by-the-numbers.md`](../by-the-numbers.md) — the
  at-a-glance rollup.

## What does NOT measure quality

These are useful in conventional CI but aren't adversarial. The
framework's claim is that anisotropic reviewers + enforced
invariants + reproducible harnesses produce quality in dimensions
conventional CI misses.

- **Lines of code.** Often correlated with productivity, sometimes
  inversely with focus. Tooling surface minus context-weight is the
  better signal.
- **Raw test count.** Lockable tests are about *quality*, not count.
  Six placebic lockable tests are worse than one non-placebic.
- **Build success rate.** The binary "did it compile" doesn't verify
  behavioral correctness. That's what the slice does.
- **Single-model verdict.** No anisotropy; no signal that the verdict
  generalises.
- **Test "passing" without verification.** A passing test on a
  no-op implementation is the headline failure mode this framework is
  shaped to detect. The placebiticity sensor is in §1 above.

The most useful reformulation of "code quality" the loop surfaces is:
**the slice's evidentiary chain is reproducible, anisotropic, and
non-placebic**. Three surfaces, each measurable on a single round.
