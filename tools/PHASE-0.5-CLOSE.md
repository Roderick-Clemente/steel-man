# tools/PHASE-0.5-CLOSE.md — Phase 0.5 closure checklist

This page marks the close of Phase 0.5 of the validation
primitive. The primitive now survives a battery of independent
checks — headless real runs, blind cross-family verdicts,
machine-verifiable gates, known-ground-truth reproduction, full
cost/latency/intervention logging, and a regression-guarded
fake-pass fixture (Units A–C of `factory/rung5.5-fakepass-close`,
backstop-verified on a clean clone at tip `6bc03e7`).

## Phase 0.5 exit criteria

- [x] **Headless real run** — `num_turns` and `tokens` are
      observed across the 3 ladder runs (rung 3 LIVE, rung 7A,
      rung 7B) AND across the 2 MEASUREMENT runs (R4 Codex
      refactor-blind-v1, R5 Grok refactor-blind-v1). Both axes
      (`num_turns > 0`, `(input_tokens > 0) OR (output_tokens > 0)`)
      pass on real-input runs. The `--mission-style` no-op shape
      is rejected by the rung-3-shape-gate's `num_turns > 0` /
      `tokens > 0` / `tool_calls_total ≥ 1` checks.

- [x] **Validator provably blind** — the validator sees only the
      rendered blind spec + diff prompt. A 14-marker forbidden-
      token canary (`tools/fixtures/rung2-canary-check.py`) ships
      with the ladder and refuses any of `BUILD-LOG.md`,
      `hook-attempts.jsonl`, `num_turns=`, `is_error=`,
      `factory_credits`, executor reasoning, etc. The
      reproduction bundle commit (`74df967`) verifies the same on
      a fresh-clone review.

- [x] **Gate asserts on reality + fails loud** — every gate
      emits an exit code; pre-fix Code's rung-5 gate minted exit 0
      on `is_error=None` (the fake-pass hole). Units A–C of
      `factory/rung5.5-fakepass-close` close that hole:
      `rung5-gate.py` rejects `is_error is not False`; each gate
      threads `envelope.is_error`. Backstop verified on tip
      `6bc03e7` from a clean laptop clone (exit codes checked
      with NO pipes). LIVE=`GGG`, Config A=`GGR`, Config B=`RRR`
      — clean run still passes; the forged fixture from Unit B is
      CAUGHT at rung 5 with the literal message
      `rung 5 RED — tool_call is_error must be False (got None).

- [x] **Reproduces known ground truth** — same defect input
      handed to multiple validator models gives verdicts that
      COVER the rubric: Codex → REJECT, Grok → ACCEPT-WITH-NITS,
      `(gpt-5.4-mini + four-family panel)` → REJECT vs
      ACCEPT-WITH-NITS (severity calibration divergence, 2nd
      sighting of the ladder's first divergence). The verdicts
      agree on FACTS (both found the defect) and differ on
      severity. This is the ladder's agreed ground truth.

- [x] **Cost/latency/intervention logged in RUN-LEDGER.md** —
      `tools/RUN-LEDGER.md` carries rows for all 5 validator
      runs (3 ladder + 2 MEASUREMENT), a TOTALS table, and the
      §13 One-vs-N operator-intervention proof. Total cost =
      185 186 input tokens / 40 513 output tokens / 593 992 ms
      wall-clock across 5 runs. Operator-intervention count
      **= 1** (Rod hand-relayed the BACKSTOP steer note once).
      Per brief "§13 reference" — the count drops from N to 1
      against the prior hand-relay method (~16+ actions per
      validation loop).

- [x] **Fake-pass hole closed + regression-guarded by rung7b
      fixture** — `tools/fixtures/rung7b-fakepass/` carries
      `fake-envelope.json` + `fake-session.jsonl` (one tool_use
      Read on `api/llms_txt.py`, no tool_result,
      `is_error=None`) plus a forged verdict text containing the
      exact double-charset phrasing the project hunts. The
      contract gate `tools/fixtures/rung7b-fakepass-gate.py`
      asserts the fixture MUST be REJECTED; pre-fix the contract
      gate REDs (exit 1, contract violated); post-fix the gate
      flips to GREEN (exit 0, contract satisfied). Backstop
      verified the flip on a clean clone at tip `6bc03e7`. The
      `KNOWN-ISSUES.md` entry "Fake-pass via unmatched tool_use"
      (filed in Unit A of this branch) documents the closed hole.

## Phase 0.5 status

Phase 0.5 DONE; Phase 1 (reference guard) is next.
