# External dogfood self-assessment — adversarial-sprint framework

**Source:** `Roderick-Clemente/evan-os` -> `DOGFOOD-SELF-ASSESSMENT.md`
(pilot repo's own commit). Mirrored here for
framework-affecting reading only.

**Pilot scope:** PRD -> cross-family PRD review (grok-4.5 +
gemini-3.1-pro-preview, both REJECT_PLAN) -> 6 spec fixes ->
chunk -> overlay dry-run (green). 32 findings surfaced. Python
sample app shipped (1285 lines, 21 pytest tests).

**Audit mode:** unflattering; surface-level verdict + §11 step
diagnosis + causal chain + EOS pilot agent's honest self-criticism.

**Why mirrored here:** the framework-affecting findings (telemetry
join, post-chunk code review absence, live-path preconditions) feed
chunk-14/chunk-15 and Phase 4.6+ scope. Cross-linked from
`phase-4.5/KNOWN-ISSUES.md` KN-A-1..KN-A-4.

---

## Headline

The `bin/run-sprint` runner fired **zero real model calls** in
this pilot. Only a `--dry-run --non-interactive` executed, so
every runner-emitted artifact in the pilot's evidence dirs is a
simulator stub. Proof, present in every envelope:

```json
"result": "[dry-run] No droid exec fired. Planned call: droid exec --model ..."
```

The real value (cross-family PRD review, 32 findings, both
REJECT_PLAN) and the entire shipped app came from operator-driven
work (ad-hoc `run-with-model.sh` invocations + hand-authoring),
not from the runner. **The runner's contribution to the actual
deliverable: 0 lines produced, 0 lines reviewed.**

## §11 step → driver (9 steps)

| §11 step | Driver | Evidence |
|---|---|---|
| 1. Pre-chunk PRD review | **HAND** | real models, ad-hoc via run-with-model.sh (NOT the runner) |
| 2. chunks.json | **HAND** | no planner produced it |
| 3. Plan for chunk 1 | **GAP** | simulated stub ("simulate a single acceptance slice") |
| 4. Plan-review (§5.3) | **GAP** | both reviewer envelopes "No droid exec fired" |
| 5. Reconcile gate | **RUNNER** | auto-accepted (--non-interactive); no human decision exercised |
| 6. Chunk-1 inner loop | **GAP** | executor+bundle fabricated (commit_sha `000…0`, tests_passed:1, epoch timestamps) |
| 7. Chunk commit | **HAND** | 34b86e3, 1285 lines, plain message — not the structured recipe |
| 8. Cross-family review of code | **GAP** | never happened; **author == validator** |
| 9. Telemetry | **partial** | 2 rows, both simulated reviewers; `dispositions.jsonl` missing; **run_id ≠ banner run_id** |

## Key evidence

- **Telemetry:** the pilot wrote 2 rows (both
  `"note":"dry-run: simulated; no droid exec fired"`), 0
  findings, `dispositions.jsonl` absent. The 54/71 totals on
  prior phases are historical, not pilot-attributable.
- **§15 truth-table:** dry-run was genuinely side-effect-free
  (H-2 holds). However the COMPLETED banner claimed
  `branch + commits: 7` that `git branch --list 'factory/sprint-*'`
  and `git log` both show as not-present (KN-J15 reproduced from
  a clean pilot). Live/act-2 guarantees: not exercised at all.
- **NEW post-pass-r4 finding:** banner
  `run_id=r-phase45-...` vs telemetry `run_id=r-dry-run-...` —
  **the audit trail cannot be joined to the banner.** An
  operator who trusts the banner cannot verify the trail.

## Verdict

> The pilot validated the framework's review philosophy and its
> dry-run plumbing. It did not validate the runner as a builder
> or as an act-2 structural guarantee.

A real §11 claim requires a live run (signing key set, real
models fired, JS-aware verifier per D-1, real toolchain per D-5)
with its branch + telemetry + committed checkpoint inspected
end-to-end.

## Why zero real model calls (causal chain)

1. **The framework prescribes dry-run first.** `phase-4.5/RUN-PROMPT.md`
   + overlay README both say: run `--dry-run --non-interactive`
   as the wiring test before spending real model credits. So the
   first (and only) invocation was the prescribed dry-run.
2. **Operator chose "dry-run first, pause before live."** When
   the EOS agent asked (AskUser: Live-vs-dry), the operator
   answered "dry-run wiring test first, pause before live."
   Dry-run by definition fires 0 real models; every step returns
   the "No droid exec fired" stub.
3. **At the pause, the live path was blocked by three concrete
   preconditions**, by design (PRD §7 fail-closed) and by
   environment:
   - `EVIDENCE_SIGNING_KEY` was unset → runner refuses live
     mode by §7 fail-closed.
   - D-1: `verify-green.py` was pytest-only, but the PRD stack
     was Next.js → live inner loop had nothing valid to verify-
     green against.
   - D-5: no Node/npm on the host → the PRD's stack couldn't be
     built at all.
4. **Operator redirected to "a sample app one way or another."**
   At that point the EOS pilot agent pivoted to hand-building a
   Python sample app rather than unblocking the runner (build
   the JS adapter, set a signing key, scaffold a toolchain, then
   run live). That delivered an app fast but meant the runner
   stayed at its single dry-run, and the code path went entirely
   around it.

So: **zero real model calls by the runner = dry-run-by-design**
(steps 1-2) **+ live-was-blocked** (step 3) **+ priority-shift-
to-ship-by-hand** (step 4).

## Honest self-criticism (from the EOS pilot agent)

> I offered a "force a live run as-is to observe exactly where
> D-1 fails" option, and I could have set a throwaway signing
> key to at least exercise the real planner/reviewer calls
> *before* the verifier blocked. I didn't circle back to that
> once the goal became "get an app," so the runner's builder
> path was never given a real test.

## Framework-level door-name → next-fix mapping

The framework-affecting findings recorded by this self-assessment
have been wired into `phase-4.5/KNOWN-ISSUES.md` KN-A-1..KN-A-4:

| Finding | Tracker |
|---|---|
| Runner fired 0 real model calls | KN-A-1 |
| Telemetry/banner run_id mismatch | KN-A-2 (chunk-14 owns) |
| Post-chunk adversarial code review never ran | KN-A-3 (chunk-15 owns) |
| Live mode = 4-precondition conjunction | KN-A-4 (chunk-14 + chunk-15 own) |

The pilot's per-language finding D-1 (verify-green.py pytest-only)
is captured separately in `KNOWN-ISSUES.md` Backlog E and `phase-4.5/
EXTERNAL-DOGFOOD-HANDOFF.md` P1.
