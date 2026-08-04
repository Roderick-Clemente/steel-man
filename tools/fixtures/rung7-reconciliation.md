# Rung 7 — RECONCILIATION NOTE — SUPERSEDED 2026-08-04

> **Superseded: the earlier diff-direction explanation was incorrect;
> see backstop refutation below. The corrected analysis treats this as
> a SEVERITY divergence on IDENTICAL input — the validator was stricter
> than the human panel — NOT a fixture direction mismatch.**

This document captures the ORIGINAL (incorrect) reasoning and the
CORRECTED (severity-divergence) reasoning. Both are kept on purpose:
honesty about wrong turns is the record. The validator-builder
rationalised its own anomaly rather than flagging it; that rationalising
is itself a rung-7 finding.

---

## (Earlier, SUPERSEDED — diff-direction explanation)

### What was claimed

The first version of this note claimed the machine REJECT vs the
human ACCEPT-WITH-NITS gap was a "diff-direction mismatch":
the machine had reviewed the bug-introducing diff (BASE → HEAD with
defect PRESENT), while humans had reviewed the fix-direction diff
(pilot/llms-txt 308aaa70 with defect ABSENT). Both verdicts were
reported as correct for their respective diffs.

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

2. The canonical human 4-family verdict says the doubled-charset
   was "caught BLIND". A blind catch on a defect that is already
   absent at HEAD is impossible. The catch had to happen on the
   defect-PRESENT state — that is, on commit `2b70eae1`, exactly
   what the validator reviewed.

3. Therefore the human panel reviewed the SAME `2b70eae1` defect-
   present state the validator did, and graded differently:
   humans: ACCEPT-WITH-NITS (nit; ship).  validator: REJECT
   (blocking).

The "diff-direction mismatch" framing was a rationalisation: it
explained away the discrepancy by claiming humans reviewed
something the validator hadn't, when in fact they reviewed the
same input.

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

The 4-family canonical human verdict on the same defect-present
state (`pilot/llms-txt@2b70eae1`) is ACCEPT-WITH-NITS. The doubled-
charset was a "nit" to the human panel.

### Severity rubric divergence on identical input

| reviewer   | input commit | defect-state | verdict          | severity rubric        |
|------------|--------------|--------------|------------------|------------------------|
| validator  | 2b70eae1     | PRESENT      | REJECT (block)   | defect ⇔ block         |
| humans X 4 | 2b70eae1     | PRESENT      | ACCEPT-WITH-NITS | defect ⇔ nit (fixable) |

The validator is **strictly stricter than the human rubric**: it
treats the doubled-charset as a merge-blocking defect, while humans
treat it as a fixable nit. This is NOT a gate over-firing (the gate
accepts ACCEPT-WITH-NITS via the `ACCEPT(?:-WITH-NITS)?` regex). The
validator itself emitted REJECT, not the gate.

### Why the validator is stricter (probable reasons)

- The validator reads the source file (`api/llms_txt.py`) directly
  with the Run/Live tool access list (`Read, Execute, Glob, Grep,
  LS`). It sees the literal `mimetype="text/plain; charset=utf-8"`
  on line 56 and likely grades "RFC compliance" of Content-Type
  blocking.
- The 4-family human panel reads in a richer context: it knows the
  branch is pilot/llms-txt scaffolding (a multi-commit pilot), the
  defect fix is queued, and any human-visible Werkzeug behavior in
  real browsers (which dedups the duplicated charset client-side)
  keeps the production effect minimal.
- The validator has no "trust the follow-up" affordance — it grades
  the diff in isolation.

### Causal fact of record

The fix commit itself (verbatim from `git show 308aaa70`):
```
-    return Response(LLMS_TXT_BODY, mimetype="text/plain; charset=utf-8")
+    return Response(LLMS_TXT_BODY, mimetype="text/plain")
```
The fix simply removes the defect. The diff that introduces the
defect (BASE → HEAD in our fixture) is happening earlier and is
the same state humans caught in their post-build review.

So both the machine validator and the human panel reviewed the
defect — they just graded it with different severity logic. The
machine is stricter.

---

## Record-keeping summary

| item                                                 | now-stated verdict              |
|------------------------------------------------------|---------------------------------|
| divergence cause                                     | severity rubric divergence on identical input (NOT direction mismatch) |
| machine verdict on `2b70eae1` (defect-present)       | REJECT                          |
| human verdict on `2b70eae1` (defect-present)         | ACCEPT-WITH-NITS                |
| rung-6 gate behavior                                 | accepts ACCEPT-WITH-NITS via regex; the validator itself is the source of REJECT (gate is symmetric) |
| rung-6 gate outcome on REJECT + finding              | GREEN                           |
| rung-6 gate outcome on ACCEPT-WITH-NITS + finding    | GREEN (would also have been GREEN) |
| rung-8 implication                                   | knob: validator severity rubric MUST be aligned with the human panel — currently the validator's own rubric runs REJECT on a defect humans let pass.  Out of scope now. |

---

## Reference

- Pin: `tools/fixtures/doubled-charset-pin.json` (BASE `bfc8a3b6` → HEAD `2b70eae1`)
- Rung 6 gate: `tools/fixtures/rung6-gate.py` (commit `5e927bc`)
- The original fix-commit (single line mimetype removal): `pilot/llms-txt 308aaa70`
- Live rung-3 verifier envelope: `build-evidence/rung3-droid-exec-output.json`
- Related cleanups in this revision: `tools/KNOWN-ISSUES.md`, `tools/README.md`
