# Act 1 — By hand. It works, and that's the problem.

**Demo beat:** The manual baseline harness (Phase 0.5) as the honest
comparison arm.

**What Act 1 demonstrates:** the adversarial sprint method running
end-to-end with two CLIs and shell glue — headless real runs, blind
cross-family validators, machine-verifiable gates, cost/latency/intervention
logging, and a regression-guarded fake-pass fixture. It genuinely works. That
is the point, and the reason the baseline must not be strawmanned.

**What Act 1 is NOT:** the plugin. This is the best achievable with two CLIs
and shell. If it turns out to be nearly as good as the plugin, that is a
finding worth having before a demo rather than during one (PRD §11 Phase 0.5).

**CLI under test:** `droid` 0.186.0 · **Host:** macOS (darwin 24.6.0)

---

## Headline numbers

| metric | value | source |
|--------|-------|--------|
| total input tokens | 185 186 | `tools/RUN-LEDGER.md` totals |
| total output tokens | 40 513 | `tools/RUN-LEDGER.md` totals |
| wall-clock duration | 593 992 ms (~9 m 54 s) | `tools/RUN-LEDGER.md` totals |
| run count | 5 (3 ladder + 2 MEASUREMENT) | `tools/RUN-LEDGER.md` totals |
| operator interventions | 1 | `tools/RUN-LEDGER.md` §13 proof |

The single operator intervention: Rod hand-relayed the BACKSTOP steer note
once because `origin/orchestrator/steer` did not exist on the repo's remote.
Every other step ran headless via `droid exec`.

---

## What was verified (Phase 0.5 exit criteria — all checked)

From `tools/PHASE-0.5-CLOSE.md`:

1. **Headless real run** — `num_turns` and `tokens` observed across all 5
   runs. Both axes pass: `num_turns > 0`, `(input_tokens > 0) OR
   (output_tokens > 0)`. The `--mission-style` no-op shape is rejected by
   the rung-3-shape-gate.

2. **Validator provably blind** — a 14-marker forbidden-token canary
   (`tools/fixtures/rung2-canary-check.py`) refuses `BUILD-LOG.md`,
   `hook-attempts.jsonl`, `num_turns=`, `is_error=`, `factory_credits`,
   executor reasoning, etc. Verified on a fresh-clone review (commit
   `74df967`).

3. **Gate asserts on reality + fails loud** — every gate emits an exit code;
   pre-fix Code's rung-5 gate minted exit 0 on `is_error=None` (the fake-pass
   hole). Units A–C of `factory/rung5.5-fakepass-close` close that hole.
   Backstop verified on a clean clone at tip `6bc03e7`: LIVE=`GGG`, Config
   A=`GGR`, Config B=`RRR` — clean run still passes; the forged fixture is
   CAUGHT with the literal message `rung 5 RED — tool_call is_error must be
   False (got None)`.

4. **Reproduces known ground truth** — same defect input handed to multiple
   validator models: Codex → REJECT, Grok → ACCEPT-WITH-NITS,
   `(gpt-5.4-mini + four-family panel)` → REJECT vs ACCEPT-WITH-NITS
   (severity calibration divergence). Verdicts agree on FACTS, differ on
   severity. This is the ladder's agreed ground truth.

5. **Cost/latency/intervention logged** — `tools/RUN-LEDGER.md` carries rows
   for all 5 runs, a TOTALS table, and the §13 One-vs-N operator-intervention
   proof. Intervention count = 1 (down from ~16+ in the prior hand-relay
   method).

6. **Fake-pass hole closed + regression-guarded** —
   `tools/fixtures/rung7b-fakepass/` carries `fake-envelope.json` +
   `fake-session.jsonl` plus a forged verdict. The contract gate
   `tools/fixtures/rung7b-fakepass-gate.py` asserts the fixture MUST be
   REJECTED. Pre-fix: gate REDs (exit 1). Post-fix: gate GREENs (exit 0).
   Backstop verified on clean clone at tip `6bc03e7`.

---

## The cost of it working (the demo beat)

From PRD §15 Act 1:

- **You are the orchestrator.** Every handoff is a human decision, so the
  process runs at the speed of your attention.
- **The laptop stays open.** Close it and the run dies.
- **Nothing is enforced.** Family separation, test locking, and validator
  independence are conventions the operator maintains. A tired operator
  silently degrades every one of them.
- **No attribution.** Nobody can say what the run cost, or which role spent
  it — until the ledger is manually compiled.
- **Nothing to show a CISO.** Evidence lives in scrollback.

The 594k ms wall-clock and the 1 operator intervention are the honest
numbers. The method works. The cost is the operator's sustained attention and
discipline.

---

## Replay instructions

### Prerequisites

- `droid` CLI at the version the probes were scoped to (0.186.0)
- The pilot repo: `/Users/factory/work/quantum-bank--llms-txt-pilot`
- The framework repo: `/Users/factory/work/adversarial-sprint-dev-3.2-build`

### Step 1: Reproduce the gate verdicts from committed evidence

The gates run against committed fixtures — no live `droid exec` needed. From
the framework repo root:

```sh
# Live (rung 3 LIVE) — expect GREEN across all three gates
python3 tools/fixtures/rung3-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
# expected: GREEN — num_turns=2, tool_calls_total=2, tokens input/output = 13612/1661

python3 tools/fixtures/rung5-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
# expected: GREEN — all is_error=False; api/llms_txt.py inspected

python3 tools/fixtures/rung6-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
# expected: GREEN — decision 'REJECT' + doubled-charset finding present
```

All three should print `GREEN`.

### Step 2: Reproduce the fake-pass regression guard

```sh
# The contract gate must REJECT the forged fixture
python3 tools/fixtures/rung7b-fakepass-gate.py
# expected: GREEN (exit 0) — the gate catches the fake pass
```

### Step 3: Review the headline numbers

```sh
cat tools/RUN-LEDGER.md
# Contains per-run table, totals (185k input / 40k output / 594k ms),
# and the §13 operator-intervention proof (count = 1).
```

### Step 4 (optional): Re-run the probes against a live CLI

If a live `droid exec` is available at the pinned version, the probe
reproduction scripts are:

```sh
# Probe 2: model pinning + family gate
bash phase-0/evidence/probe-2/run.sh

# Probe 3: context isolation
bash phase-0/evidence/probe-3/run.sh

# Probe 4: hook enforcement (re-verified)
bash phase-0/evidence/probe-4/reverify/run.sh

# Probe 6: plugin scaffold
bash phase-0/evidence/probe-6/run.sh
```

Each script rebuilds its scratch repo from committed artifacts and prints
exit codes and resolved model IDs. A CLI upgrade invalidates these until
re-run (OPERATING-RULES §3).

---

## Honesty bound

Act 1 is the honest comparison arm. It is NOT the plugin. It is the best
achievable with two CLIs and shell. The numbers are real, the gates are
reproducible from committed evidence, and the fake-pass hole is closed and
regression-guarded. The limitation is not quality — it is that the operator
is the orchestrator, and the laptop stays open.
