# Phase 4 Demo — Adversarial Sprint

Three acts. Each one earns the next.

**Core principle:** demo claims bind to verified capabilities. If a probe
didn't verify it, it doesn't go in the demo (OPERATING-RULES §16). No Mission
cosplay. "Close the laptop" requires a durable runner — either build one or
drop the claim.

---

## Narrative arc

### Act 1 — By hand. It works, and that's the problem.

The manual baseline harness (Phase 0.5) runs the full adversarial sprint
method with two CLIs and shell glue. It genuinely works: headless real runs,
blind cross-family validators, machine-verifiable gates, cost/latency/
intervention logging, a regression-guarded fake-pass fixture. The headline
numbers: 185k input tokens, 40k output tokens, 594k ms wall-clock, 1 operator
intervention (down from ~16+ in the prior hand-relay method).

Then show the cost of it working: you are the orchestrator, the laptop stays
open, nothing is enforced, no attribution, nothing to show a CISO. An
audience of engineers recognises this immediately — it is what their teams
are doing right now.

**Script:** [`act-1-script.md`](act-1-script.md)

### Act 2 — Push a button, go enjoy life.

The same sprint, but the orchestration is a script. `tools/orchestrate-
review.py` runs the complete pipeline mechanically: produce evidence bundle,
run cross-family validators, check stray writes, parse verdicts, append
telemetry, report gate decision. One command instead of 16+ manual handoffs.
The guarantees — cross-family validation, evidence-bundle consumption,
stray-write checks, telemetry — are enforced by the script, not by operator
discipline.

The KI-2 preventive fix is demonstrated live: in bundle-consuming mode,
validators' `--enabled-tools` drops `Execute`, closing the write vector
preventatively.

**Script:** [`act-2-script.md`](act-2-script.md)

### Act 3 — Now make it safe for a bank.

Autonomy is the easy half; every vendor demos that. The reason a regulated
buyer signs is the layer on top — the platform controls that the method
depends on. Four controls were verified by Phase 0 probes:

1. **Model pinning** (Probe 2): `--model` pins resolve exactly, invalid IDs
   fail closed at exit 1, a family gate hook denies before any tool acts.
2. **Hook enforcement** (Probe 4 re-verified): a `PreToolUse` hook blocks
   the executor's edit to a locked test, the agent receives
   `SPEC_OR_TEST_BLOCKED`, the run continues.
3. **Context isolation** (Probe 3): a custom Droid's tool restrictions are
   enforced by schema omission — a tool absent from the schema cannot be
   talked into existing. The filesystem-reach gap is honestly disclosed.
4. **Plugin scaffold** (Probe 6): droid, skill, and hook ship as a single
   installable plugin, all activating on install.

Three capabilities from the v1 roadmap review are listed as roadmap narrative,
NOT demo claims: Droid Shield, OpenTelemetry export, and air-gapped
deployment. None were verified by Phase 0 probes.

**Script:** [`act-3-script.md`](act-3-script.md)

### Act 4 — Eat our own dog food. (FUTURE — depends on Phase 4.5)

The framework runs on itself. The pilot target is this repo — the
adversarial sprint framework's own code. A real change to the framework
(e.g., a bug fix in `orchestrate-review.py`, a new feature in the evidence
provider, a refactor of `valid-red.py`) goes through the full adversarial
sprint: plan → test → execute → validate → gate decision.

This is the ultimate test. The method's entire thesis is that cross-family
independence catches what single-family review misses. Running it on its
own codebase answers: does the method catch bugs in the method? The
roadmap review already showed one case of this (v1 REJECT by cross-family
panel caught factual errors in a single-family document). Act 4 makes it
routine, not a one-off.

**What Act 4 demonstrates:**
- The framework is not a special case. It runs on its own code the same
  way it runs on QuantumBank. The evidence provider produces a bundle for
  the framework's own tests. Cross-family validators review the framework's
  own diffs. The gate blocks the framework's own PRs on REJECT.
- The calibration data feeds back. Every dogfooding run adds rows to
  `findings.jsonl`, accumulating the `first_seen_in_panel_position` signal
  that Phase 6 calibration needs. The framework's own bugs become
  calibration data for the framework's own panel optimization.
- The telemetry is real. The framework's own `runs.jsonl` and
  `findings.jsonl` are the §13 system of record, not a demo fixture.

**What Act 4 does NOT demonstrate (honesty bounds):**
- Act 4 cannot be demoed today. It depends on Phase 4.5's full loop
  runner (only the review step is scripted; planning, test design, and
  execution are still manual `droid exec` calls). Once the loop runner
  exists, Act 4 is "point it at this repo instead of QuantumBank."
- Family separation still applies. The planner/executor that built the
  framework was Claude-family. Validators must be cross-family (Grok,
  Gemini, or others). The framework reviewing its own code with the same
  family that wrote it would violate invariant #1.
- Dogfooding is not proof of generality. It proves the method works on
  its own codebase, not on any arbitrary codebase. That's Phase 5
  (generalize to a second stack).

**Script:** `act-4-script.md` (to be created in Phase 4.5)

**Replay (future):**
```sh
cd /path/to/adversarial-sprint-dev

# Point the loop runner at this repo instead of QuantumBank
python3 sprint-loop.py \
    --framework-root . \
    --pilot-root . \
    --pilot-python $(which python3) \
    --test-file test/test_framework_own_tests.py \
    --lock-file locks/test_framework_own_tests.py.lock.json \
    --change-description "Fix ANSI regex in valid-red.py to handle CSI codes"
```

The loop runner plans the change, writes a test, executes, produces
evidence, runs cross-family validators, and creates a PR with a gate
decision. The framework has reviewed its own code.

---

## Honesty summary

### What the demo proves

- **The loop runs end-to-end.** Act 2's orchestrator produced 12 telemetry
  rows from 6 orchestrated runs. The pipeline is mechanical, not ad hoc.
- **Cross-family validation works.** Grok (xAI) and Gemini (Google) produce
  independent verdicts on the same evidence. Split verdicts are visible
  (grok REJECT, gemini ACCEPT in run 4) — genuine disagreement, not theater.
- **The evidence provider saves tokens.** In bundle-consuming mode,
  validators read a pre-built bundle instead of running tests themselves.
  The KI-2 fix (dropping `Execute`) closes the write vector preventatively.
  H-CI experiment (B2) confirmed: 27.8% mean token saving (bundle vs
  in-session), quality holds (6/6 ACCEPT both arms), fairness rule holds.
  See `phase-4/h-ci/analysis.md`.
- **The platform enforces the core invariants.** Model pinning, hook
  enforcement, context isolation (tool schema), and plugin distribution are
  all probe-verified and reproducible from committed evidence.
- **The fake-pass hole is closed.** The rung7b fixture proves the gate
  rejects forged evidence. Backstop-verified on a clean clone.
- **The operator cost dropped from N to 1.** Phase 0.5's §13 proof: 1
  operator intervention across 5 runs, down from ~16+ in the prior method.
- **Cheap executors can implement from spec.** H3 validation (B3) proved
  gpt-5.4-mini implemented from an un-hinted prompt (no solution in the
  prompt), GREEN on first attempt, cross-family ACCEPT.
  See `phase-4/h3/analysis.md`.
- **The framework can review its own code (future).** Act 4 (dogfooding)
  will prove the method works on its own codebase. The roadmap review
  already showed one case (v1 REJECT caught single-family errors). Act 4
  makes it routine — pending the full loop runner from Phase 4.5.

### What the demo does NOT prove

- **Autonomy ("close the laptop").** The orchestrator is a foreground
  script. A durable runner has not been built or evidenced. The claim is
  dropped, not demoed.
- **Droid Shield.** Not verified by any Phase 0 probe. Roadmap narrative.
- **OpenTelemetry export.** Not verified by any Phase 0 probe. Roadmap
  narrative.
- **Air-gapped deployment.** Not verified by any Phase 0 probe. Roadmap
  narrative.
- **Mission-native orchestration.** `droid exec --mission` is a no-op
  (Probe 1). The demo is command-orchestrated, not Mission cosplay.
- **H-CI with high confidence.** The H-CI experiment ran N=3 (minimum
  viable). Variance is high (run 1 treatment +16.9%, run 2 -50.9%). The
  27.8% mean saving is directional, not a tight CI. See
  `phase-4/h-ci/analysis.md` for the full variance analysis.
- **Dogfooding (yet).** Act 4 is planned but depends on Phase 4.5's full
  loop runner. The framework has not yet reviewed its own code through the
  full loop — only the review step is scripted today.

### The honest version of PRD §15

PRD §15 Act 2 says "close the laptop, come back to a completed sprint." The
honest version: "push a scripted button, get a gate decision with a full
audit trail." The autonomy delta from Act 1 is real — the orchestration
stopped being your job — but it is not unattended autonomy. The delta from
Act 1 is the demo. Not "AI wrote code" — the orchestration stopped being
your job, and the guarantees stopped being your discipline.

PRD §15 Act 3 says "Droid Shield on the validation path, OpenTelemetry
traces, deployment flexibility." The honest version: four platform controls
that Phase 0 actually verified, plus three roadmap capabilities that need
re-probing before they can be demoed.

---

## Replay instructions

### Prerequisites

- `droid` CLI at 0.186.0 (or re-verify probes after upgrade — a CLI upgrade
  invalidates the go/no-go until probes are re-run, OPERATING-RULES §3)
- The pilot repo: `/Users/factory/work/quantum-bank--llms-txt-pilot`
  (with its `.venv` for running tests)
- The framework repo (this repo — the directory containing `PRD.md`)
- Cross-family validator models accessible: `grok-4.5`, `gemini-3.1-pro-preview`

### Act 1 — from a clean checkout

The gates run against committed fixtures — no live `droid exec` needed:

```sh
cd /path/to/adversarial-sprint-dev

# Reproduce gate verdicts from committed evidence
python3 tools/fixtures/rung3-gate.py --exit-loud \
  --envelope tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
python3 tools/fixtures/rung5-gate.py --exit-loud \
  --envelope tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
python3 tools/fixtures/rung6-gate.py --exit-loud \
  --envelope tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
# All three should print GREEN

# Reproduce the fake-pass regression guard
python3 tools/fixtures/rung7b-fakepass-gate.py
# Expected: GREEN (exit 0) — the gate catches the fake pass

# Review the headline numbers
cat tools/RUN-LEDGER.md
```

Full instructions: [`act-1-script.md`](act-1-script.md)

### Act 2 — from a clean checkout

Requires a live `droid` CLI with access to cross-family models:

```sh
cd /path/to/adversarial-sprint-dev

python3 tools/orchestrate-review.py \
    --framework-root . \
    --pilot-root /path/to/quantum-bank--llms-txt-pilot \
    --pilot-python /path/to/quantum-bank--llms-txt-pilot/.venv/bin/python \
    --test-file test/test_profile_model.py \
    --lock-file phase-1/locks/test/test_profile_model.py.lock.json \
    --prompt-file phase-3.2/reviews/review-prompt.md \
    --review-output-dir phase-3.2/reviews/orchestrated/ \
    --validators grok-4.5:xai:grok-family,gemini-3.1-pro-preview:google:gemini-family \
    --evidence-output phase-3.2/build-evidence/chunk1-bundle.json \
    --enabled-tools Read,Glob,Grep,LS \
    --auto-level high \
    --phase phase-3.2 \
    --evidence-source bundle

# Review output
tail -2 telemetry/runs.jsonl
cat phase-3.2/reviews/orchestrated/review-summary.json
```

Run it N times (single runs lie). Each run appends 2 telemetry rows. Compare
across runs to see variance. Flakiness (if any) is visible — do not hide it.

Full instructions: [`act-2-script.md`](act-2-script.md)

### Act 3 — from a clean checkout

The probe reproduction scripts rebuild their scratch repos from committed
artifacts:

```sh
cd /path/to/adversarial-sprint-dev

# Model pinning + family gate (Probe 2)
bash phase-0/evidence/probe-2/run.sh

# Context isolation (Probe 3)
bash phase-0/evidence/probe-3/run.sh

# Hook enforcement (Probe 4 re-verified)
bash phase-0/evidence/probe-4/reverify/run.sh

# Plugin scaffold (Probe 6)
bash phase-0/evidence/probe-6/run.sh
```

Each script prints exit codes and resolved model IDs. A CLI upgrade
invalidates these until re-run.

Full instructions: [`act-3-script.md`](act-3-script.md)

---

## File index

| File | Purpose |
|------|---------|
| `act-1-script.md` | Act 1: manual baseline harness (Phase 0.5) |
| `act-2-script.md` | Act 2: command-orchestrated loop |
| `act-3-script.md` | Act 3: Phase-0-verified controls only |
| `README.md` | This file: narrative arc, honesty summary, replay instructions |

---

## Version scope

All probe evidence is scoped to `droid` 0.186.0 on macOS (darwin 24.6.0)
or `droid-cloud-computer-1st` (Linux). A CLI upgrade invalidates the
go/no-go until probes are re-run (OPERATING-RULES §3). The demo is
version-scoped, not forever.
