# PR 5 Report — experiment reframe + ledger reconciliation

**Branch:** `factory/executor-experiment-docs`
**Base:** `factory/rejection-routing-and-feedback`
**Commits:** 2 (1 cherry-pick + 1 rewrite/reconciliation)

---

## Cherry-pick and conflict resolution

Cherry-picked `9074d37` (executor experiment results + KI-18). Conflict in
`tools/KNOWN-ISSUES.md`: HEAD had KI-17 and KI-19 (from PRs 3–4); the
cherry-picked commit added KI-18. Resolved by inserting KI-18 between KI-17
and KI-19, preserving numeric order. All existing entries kept intact.

---

## Experiment doc claim changes (before → after)

### Section 1 — Executive summary

- **Before:** "outcome 2 materialized: gpt-5.2 wins on total cost — the
  'cheap executor' hypothesis is busted." Single-paragraph declarative.
- **After:** "the data leans toward gpt-5.2 having lower total cost of
  ownership, but several confounds prevent a conclusive verdict." Leads with
  executor-only comparison (4.4×, the clean signal). States n=1 per arm.
  Adds run-to-run variance caveat (plan-reviewer seats varied 50–94% on
  comparable inputs). Adds rerun plan (≥3 runs per arm, KI-18 fixed).

### Section 3 — Per-seat key observations

- **Before:** Three bullets; third acknowledged gemini re-run artifact but
  did not quantify the impact on the headline.
- **After:** Four bullets. Added "executor gap is intrinsic; gemini gap is
  confounded." Quantified: excluding gemini validator seats, gap narrows
  from ~30% to ~15%. Added run-to-run variance caveat from plan-reviewer
  data.

### Section 4 — Validator verdict analysis (Arm B agreement)

- **Before:** "the validators diverged, but only on process integrity...
  on the code itself they both judged it acceptable."
- **After:** Same, plus: "Arm B's validators reviewed code written against
  a 20-test suite (post-redesign) while Arm A's reviewed code against the
  original 7-test suite (KI-18), so the two verdict sets are not directly
  comparable on code quality."

### Section 5 — Code quality comparison

- **Before:** Lines table with no caveats. No explicit quality assessment
  subsection.
- **After:** Added KI-18 caveat on lines comparison (20-test vs 7-test
  suite may have driven the diff size difference). Added "Code quality
  assessment" subsection: "No defect was found by either validator in
  either arm; independent review of the two diffs is pending. The 'no
  defects' signal rests on two validators (who disagreed procedurally on
  Arm B) finding no bugs — it is not a confirmed parity claim."

### Section 6 — Outcome determination

- **Before:** "Result: hypothesis 2. The 'expensive' executor won
  decisively." Caveat at end acknowledged gemini confound but still
  declared "code quality is at parity."
- **After:** "Directional result: the data leans toward hypothesis 2, but
  a single run with known confounds cannot confirm it." Three evidence
  bullets (executor-only, full-pipeline with/without, run-to-run variance).
  Reframed conclusion: "credits = price-per-token × volume, and volume
  dominated... the 'cheap executor' hypothesis was ill-posed, not merely
  false." Explicit rerun plan with conditions.

### Section 7 — Framework health (validator crash bullet)

- **Before:** Noted crash, manual re-run, and operator action item.
- **After:** Same, plus quantified cost impact: Arm A gemini 289,313 vs
  Arm B 80,220 (~209K delta). Full-pipeline totals excluding gemini: Arm A
  788,578 vs Arm B 671,347 (~15% gap).

---

## Ledger reconciliation

**RUN-LEDGER.md line 171** — updated summary from the KI-1–16 count to
KI-1–19:

| Bucket | Count | KIs |
|---|---|---|
| Found | 19 | KI-1 through KI-19 |
| Fixed | 13 | KI-1, 2, 3, 4, 7, 8, 9, 10, 11, 15, 16, 17, 19 |
| Open | 3 | KI-5, KI-13, KI-18 |
| Partially fixed | 1 | KI-14 |
| Closed as limitation | 1 | KI-12 |
| Withdrawn | 1 | KI-6 |
| **Total** | **19** | |

Arithmetic: 13 + 3 + 1 + 1 + 1 = 19 ✓

---

## KNOWN-ISSUES.md changes

- **KI-19 status:** Added accepted residual note — REPLAN removal leaves
  `HUMAN_DECISION` as the only outlet for a plan-defect judgment from chunk
  validation; implemented plan-defect route planned as fast follow.
- **No header counts** existed in the file; none needed adding.
- **Cross-references verified:** experiment doc references KI-10, KI-15,
  KI-16, KI-18 — all exist in KNOWN-ISSUES.md.
- **KI numbering:** contiguous 1–19, no gaps, no tombstones.

---

## Tests

```
469 passed, 3 skipped, 1 failed
```

The 1 failure is the known environmental test
`tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds`
(chunk-13 fixture subject matches 2 commits on this stacked branch).
All other tests green.

---

## AGENTS.md compliance

Reviewed against "treat this repo as public" section. All rewritten text
is technical, sourced from the experiment's own data, and fair. No
names, credentials, strategy, or hiring context. Unflattering findings
(confounds, ill-posed hypothesis, noise floor) are honest engineering
assessment per the guidelines.

---

## Deferrals

None. All spec items completed.
