# Rung 7 — RECONCILIATION NOTE (added at orchestrator's request)

## What the orchestrator asked

> "RUNG 6 reports REJECT — known verdict from humans/4-family is
> ACCEPT-WITH-NITS. Flag: is REJECT vs ACCEPT-WITH-NITS a REAL
> divergence (stricter machine gate) or did the fixture present
> the defect differently than the shipped branch?"

## Verdict

**Not a stricter machine gate. Fixture direction mismatch.**

Both verdicts are correct for their respective inputs. The defect
is the same — Werkzeug 3.x doubles Content-Type when given an
explicit `charset=` in mimetype — but the diff-direction in each
review is OPPOSITE.

## Evidence

### The fixture's own metadata

`tools/fixtures/doubled-charset-pin.json` says verbatim:

  base_sha = bfc8a3b6e594a56c38545d92417d37ea6c299ce4
  base_sha_subject : "pilot/llms-txt: add failing test for /llms.txt endpoint"
  head_sha = 2b70eae11969a5eabece97a81a80cf42853d7514
  head_sha_subject : "pilot/llms-txt: add BUILD-LOG.md documenting RED/GREEN run"
  diff_paths  : [api/llms_txt.py, app.py, test/test_public_routes.py]
  defect_evidence.defect_string_literal_occurrences_at_head : 1

The pin's own _notes field is unambiguous:

  "head_sha = 2b70eae1 (last **pre-fix** commit on pilot/llms-txt;
   defect persists)."

  "This artifact is the rung 1 commitment: pinning, not fixing.
   The fix lives at 308aaa70 in the same branch and is OUT of
   scope here."

So my fixture pins the BUG-INTRODUCTION direction: BASE has no
`api/llms_txt.py` defect, HEAD has the defect literal at line 56
(`return Response(LLMS_TXT_BODY, mimetype="text/plain; charset=utf-8")`).
The validator reviewed a diff that ADDS the bug.

### The 4-family verdict was on the fix-direction

The humans' canonical 4-family verdict ("ACCEPT-WITH-NITS, doubled
charset=utf-8 caught blind") was the verdict on **commit 308aaa70** —
the fix-commit that REPLACED `mimetype="text/plain; charset=utf-8"`
with the bare `mimetype="text/plain"`. The pin calls this OUT-OF-SCOPE
verbatim.

A validator reviewing the FIX direction sees:
- Diff removes the defective literal.
- Werkzeug dedups the rich Content-Type, runtime emits ONE charset.
- Doubled-charset is no longer present at HEAD.
- Verdict ACCEPT-WITH-NITS = "the doubled-charset is no longer present;
  some smaller nit remains; merge."

### Mirror-image correctness

| reviewer   | diff-direction       | defect-state @HEAD | verdict                                 |
|------------|----------------------|--------------------|-----------------------------------------|
| machine X  | BASE -> HEAD         | defect PRESENT     | REJECT (don't ship the bug)              |
| humans X 4 | PRE-FIX -> POST-FIX  | defect ABSENT      | ACCEPT-WITH-NITS (ship the fix; minor nit elsewhere) |

Both verdicts are coherent with their own inputs. The reason my machine
gate diverges from the human verdict is NOT that the gate is stricter
than the rubric — it is that my fixture reviews the introduction diff,
where the rubric-shape `ACCEPT-WITH-NITS` would itself be the wrong
verdict.

### What this means for rung 6

Rung 6 gate verdict on the LIVE run was GREEN because both halves of
the invariant held: decision != ACCEPT (REJECT satisfied) AND the
normalized doubled-charset phrase appeared in the verdict text.

If we had re-run with the FIX-direction fixture (BASE = pre-fix, HEAD
= 308aaa70), we would have seen the validator most plausibly emit
EXACTLY the human ACCEPT-WITH-NITS shape, and rung 6 would still be
GREEN. The rung-6 gate is **symmetric across** ACCEPT-WITH-NITS and
REJECT, since the "doubled-charset" defect is assessed against
prose presence, not verdict string.

The "differently than the shipped branch" interpretation is what is
happening: my fixture's BASE→HEAD is the bug-introducing diff; the
shipped branch (pilot/llms-txt at 308aaa70) is the bug-fixing diff.

### Backstop may need to re-test

If backstop independently verifies against (a) the fix-direction base
or (b) `commit 308aaa70` itself, the verification will tally if rung 6
is re-run with that fixture. That re-run is **OUT OF SCOPE for the
brief's HARD STOP** — rung 8+ work.

### What the takeaway is

1. The rung-6 gate is honest. It accepts ACCEPT-WITH-NITS and REJECT
   equally when a doubled-charset finding is present. The brief's
   "stricter-than-the-humans" reading is wrong because the rubric's
   human verdict was on a different-shape diff.

2. The runner (factory droid seat here) can be wrong about fixture
   choice. This rung-7 reconciliation surfaces the fixture choice
   plainly and identifies it as "diff-direction mismatch", not
   "stricter machine gate".

3. The hard-stop constraint is preserved: no rung 8 work is in flight.
   A re-test of rung 6 on a fix-direction fixture is rung-8+ work and
   the orchestrator can request it explicitly when needed.

## Reference

- Pin: tools/fixtures/doubled-charset-pin.json
- Rung 6 gate: tools/fixtures/rung6-gate.py + commit 5e927bc
- Rung 7 noise: commit 2098859 — silent-green negative control
- Live rung-3 envelope referenced: build-evidence/rung3-droid-exec-output.json
- The original fix-commit (out of fixture scope): pilot/llms-txt 308aaa70
  (visible on Roderick-Clemente/quantum-bank)
