# Rung 7 — RECONCILIATION NOTE — SUPERSEDED 2026-08-04

> **Superseded: the earlier diff-direction explanation was incorrect;
> see backstop refutation below. The corrected analysis treats this as
> a SEVERITY divergence on IDENTICAL input — the validator was stricter
> than the four hand-relayed model families (Grok/Kimi/Codex/Opus) —
> NOT a fixture direction mismatch.**

This document captures the ORIGINAL (incorrect) reasoning and the
CORRECTED (severity-divergence) reasoning. Both are kept on purpose:
honesty about wrong turns is the record. The validator-builder
rationalised its own anomaly rather than flagging it; that rationalising
is itself a rung-7 finding.

---

## (Earlier, SUPERSEDED — diff-direction explanation)

### What was claimed

The first version of this note claimed the machine REJECT vs the
four hand-relayed model families' ACCEPT-WITH-NITS gap was a
"diff-direction mismatch": the machine had reviewed the bug-
introducing diff (BASE → HEAD with defect PRESENT), while the
four hand-relayed model families had reviewed the fix-direction
diff (pilot/llms-txt 308aaa70 with defect ABSENT). Both verdicts
were reported as correct for their respective diffs.

(That first version was already wrong on the attribution: it
referred to "humans" where it should have said "the four hand-
relayed model families" — Grok (xAI), Kimi (Moonshot), Codex
(GPT), Opus (Anthropic). Rod was the operator/relay, not a
validating seat. The fix-direction framing itself was the second
error; the attribution was the first.)

### Why that was wrong

The orchestrator's BACKSTOP refutation caught a structural error:

1. The fix commit `308aaa70` (parent = `2b70eae1`, the fixture HEAD)
   is **a single-line mimetype removal** (see `git show 308aaa70`):
   ```
   - mimetype="text/plain; charset=utf-8"
   + mimetype="text/plain"
   ```
   So the fix is purely on top of the same state the validator
   reviewed.

2. The canonical four-family verdict says the doubled-charset
   was "caught BLIND". A blind catch on a defect that is already
   absent at HEAD is impossible. The catch had to happen on the
   defect-PRESENT state — that is, on commit `2b70eae1`, exactly
   what the validator reviewed.

3. Therefore the four hand-relayed model families (Grok/Kimi/
   Codex/Opus) reviewed the SAME `2b70eae1` defect-present state
   the validator did, and graded differently:
   four-families: ACCEPT-WITH-NITS (nit; ship).  validator: REJECT
   (blocking).

The "diff-direction mismatch" framing was a rationalisation: it
explained away the discrepancy by claiming the four families
reviewed something the validator hadn't, when in fact they
reviewed the same input.

### Why this matters for the build

Rationalised anomalies hide real issues. We should treat this as
a rung-track finding in its own right: the validator-builder
clinging to a story that absolved the validator instead of
sur-facing a strictness divergence.

---

## Corrected analysis (CURRENT — supersedes above)

### The discrepancy

`tools/fixtures/rung6-gate.py` (commit `5e927bc`) ran against the
LIVE rung-3 verifier envelope (`build-evidence/rung3-droid-exec-
output.json`). Verifier verdict: `Verdict: REJECT`. Gate verdict:
GREEN — REJECT satisfies `decision ≠ ACCEPT`, and the doubled-
charset finding keyword is present.

The canonical four-family verdict on the same defect-present
state (`pilot/llms-txt@2b70eae1`) is ACCEPT-WITH-NITS. The doubled-
charset was a "nit" to the four hand-relayed model families
(Grok/Kimi/Codex/Opus).

### Severity rubric divergence on identical input

| reviewer                              | input commit | defect-state | verdict          | severity rubric        |
|---------------------------------------|--------------|--------------|------------------|------------------------|
| validator (gpt-5.4-mini, this run)   | 2b70eae1     | PRESENT      | REJECT (block)   | defect ⇔ block         |
| four hand-relayed model families      | 2b70eae1     | PRESENT      | ACCEPT-WITH-NITS | defect ⇔ nit (fixable) |
|   — Grok (xAI)                        |              |              |                  |                        |
|   — Kimi (Moonshot)                   |              |              |                  |                        |
|   — Codex (GPT)                       |              |              |                  |                        |
|   — Opus (Anthropic)                  |              |              |                  |                        |

The validator is **strictly stricter than the four-family rubric**:
it treats the doubled-charset as a merge-blocking defect, while the
four hand-relayed model families treat it as a fixable nit. This
is NOT a gate over-firing (the gate accepts ACCEPT-WITH-NITS via
the `ACCEPT(?:-WITH-NITS)?` regex). The validator itself emitted
REJECT, not the gate.

The actor over all four families is the historically-validated
panel that reviewed pilot/llms-txt. Rod is *not* in the validating
seat — Rod was the operator/relay who hand-pasted the prompt and
hand-copied each family's verdict. The validating seat was held
by four models, sequentially.

### Why the validator is stricter (probable reasons)

- The validator reads the source file (`api/llms_txt.py`) directly
  with the Run/Live tool access list (`Read, Execute, Glob, Grep,
  LS`). It sees the literal `mimetype="text/plain; charset=utf-8"`
  on line 56 and likely grades "RFC compliance" of Content-Type
  blocking.
- The four hand-relayed model families read in a richer context:
  they were prompted in the post-build review of pilot/llms-txt
  scaffolding (multi-commit pilot), with the defect fix queued,
  and any human-visible Werkzeug behavior in real browsers (which
  dedups the duplicated charset client-side) keeps the production
  effect minimal.
- The validator has no "trust the follow-up" affordance — it grades
  the diff in isolation as a headless automated reviewer.

The divergence is a **model-calibration question**, not a
machine-vs-human one. The right framing is gpt-5.4-mini grade vs
the four families' grades.

### Causal fact of record

The fix commit itself (verbatim from `git show 308aaa70`):
```
-    return Response(LLMS_TXT_BODY, mimetype="text/plain; charset=utf-8")
+    return Response(LLMS_TXT_BODY, mimetype="text/plain")
```
The fix simply removes the defect. The diff that introduces the
defect (BASE → HEAD in our fixture) is happening earlier and is
the same state the four families first caught in their post-build
review.

So both the machine validator and the four families reviewed the
defect — they just graded it with different severity logic. The
validator (gpt-5.4-mini) is the stricter one.

---

## Record-keeping summary

| item                                                  | now-stated verdict              |
|-------------------------------------------------------|---------------------------------|
| divergence cause                                      | severity rubric divergence on identical input (NOT direction mismatch); model-calibration question, NOT machine-vs-? |
| machine verdict (gpt-5.4-mini) on `2b70eae1`           | REJECT                          |
| four-family verdict on `2b70eae1`                     | ACCEPT-WITH-NITS                |
| actors in the validating seat (this conflict)         | (validator) gpt-5.4-mini; (canonical panel) Grok/Kimi/Codex/Opus |
| rung-6 gate behavior                                  | accepts ACCEPT-WITH-NITS via regex; the validator itself is the source of REJECT (gate is symmetric) |
| rung-6 gate outcome on REJECT + finding               | GREEN                           |
| rung-6 gate outcome on ACCEPT-WITH-NITS + finding     | GREEN (would also have been GREEN) |
| rung-8 implication                                    | knob: validator severity rubric MUST be aligned with the four-family rubric — currently the validator's own rubric runs REJECT on a defect the four families let pass. Out of scope now. |

---

## Reference

- Pin: `tools/fixtures/doubled-charset-pin.json` (BASE `bfc8a3b6` → HEAD `2b70eae1`)
- Rung 6 gate: `tools/fixtures/rung6-gate.py` (commit `5e927bc`)
- The original fix-commit (single line mimetype removal): `pilot/llms-txt 308aaa70`
- Live rung-3 verifier envelope: `build-evidence/rung3-droid-exec-output.json`
- Related cleanups in this revision: `tools/KNOWN-ISSUES.md`, `tools/README.md`, `tools/RUN-LEDGER.md`
