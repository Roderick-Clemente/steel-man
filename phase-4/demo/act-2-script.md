# Act 2 — Push a button, go enjoy life.

**Demo beat:** the full adversarial loop running end-to-end via a scripted
orchestrator — not a Mission, not an interactive session.

**What Act 2 demonstrates:** `tools/orchestrate-review.py` runs the complete
review pipeline mechanically: produce evidence bundle → run N cross-family
validators → check stray writes → parse verdicts → append telemetry → report
gate decision. No asking, no waiting, no "should I merge?" questions. It
runs, it reports, it stops only if something breaks.

**What Act 2 does NOT demonstrate:** autonomy. "Close the laptop" is NOT
claimed. The orchestrator is a foreground script — it runs as long as the
terminal is alive. A durable background runner has not been built or
evidenced. Dropping this claim is the honest choice (Track C prompt: "either
build one or drop the claim").

---

## The command

```sh
python3 tools/orchestrate-review.py \
    --framework-root /Users/factory/work/adversarial-sprint-dev-3.2-build \
    --pilot-root /Users/factory/work/quantum-bank--llms-txt-pilot \
    --pilot-python /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python \
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
```

**What each flag does:**

| Flag | Purpose |
|------|---------|
| `--framework-root` | The adversarial sprint repo (where the orchestrator and prompts live) |
| `--pilot-root` | The QuantumBank pilot repo (the code under review) |
| `--pilot-python` | The pilot repo's venv Python (for running tests in the evidence bundle) |
| `--test-file` | The locked acceptance test |
| `--lock-file` | The lock manifest with accepted assertion phrase and test SHA |
| `--prompt-file` | The blind review prompt (no executor context) |
| `--review-output-dir` | Where envelopes and stderr logs are written |
| `--validators` | Cross-family panel: grok-4.5 (xAI) + gemini-3.1-pro-preview (google) |
| `--evidence-output` | If set, step 1 produces a bundle (treatment arm) |
| `--enabled-tools` | **KI-2 fix: `Execute` is DROPPED** — validators get `Read,Glob,Grep,LS` only |
| `--evidence-source` | Tags telemetry rows as `bundle` (treatment) vs `in-session` (control) |

---

## The expected flow

```
STEP 1: Produce evidence bundle
  → local_backend.py runs the locked test, captures GREEN/RED, writes bundle JSON
  → Bundle contains: test results, locked SHA, diff, spec — no executor reasoning

STEP 2: Run cross-family validators
  → grok-4.5: droid exec --model grok-4.5 --enabled-tools Read,Glob,Grep,LS
  → gemini-3.1-pro-preview: droid exec --model gemini-3.1-pro-preview --enabled-tools Read,Glob,Grep,LS
  → Each validator reads the bundle + blind prompt, emits a verdict

STEP 3: Check stray writes (KI-2 mitigation)
  → git status --porcelain before and after each validator
  → Only newly dirty paths are flagged (not pre-existing ones)
  → Validators have no Execute tool — write vector preventatively closed

STEP 4: Parse verdicts
  → Regex extracts ACCEPT / ACCEPT-WITH-NITS / REJECT / HUMAN_DECISION from result text
  → Last occurrence wins (verdict is on the last line per prompt spec)

STEP 5: Append telemetry rows
  → Each validator → one row in telemetry/runs.jsonl (schema v2)
  → Row includes: model, family, tokens, verdict, evidence_source, duration

STEP 6: Gate decision
  → Any REJECT → gate = REJECT
  → Any ERROR → gate = STOP
  → Any UNKNOWN → gate = STOP
  → Stray writes → gate = STOP (KI-2 violation)
  → All ACCEPT → gate = ACCEPT
```

---

## Preventive KI-2 in the demo

**The Evidence Provider fix, demonstrated live.** In bundle-consuming mode,
validators' `--enabled-tools` excludes `Execute`:

```
--enabled-tools Read,Glob,Grep,LS
```

This is the KI-2 fix from ROADMAP-REVIEW §3.13. Dropping `Execute` from
validators closes the write vector preventatively — a validator that cannot
shell out cannot mutate the working tree, cannot `sed -i` a locked test, and
cannot `droid search` for another agent's transcript (Probe 3 addendum
confirmed `droid search` requires `Execute`).

The orchestrator supports both arms via a flag:
- **Treatment (bundle):** `--enabled-tools Read,Glob,Grep,LS` — no Execute
- **Control (in-session):** `--enabled-tools Read,Glob,Grep,LS,Execute` — with Execute

This is a parameterization, not a redesign. The same script runs both arms.

---

## Expected output

A clean run (both validators ACCEPT):

```
STEP 1: Produce evidence bundle
  Bundle: 8432 bytes
  Tests: 4 passed, 0 failed
  Locked SHA: a1b2c3...
  Green: True

STEP 2: Run cross-family validators
  [grok-4.5] Running grok-4.5 (grok-family)...
    turns=7 tokens_in=59128 tokens_out=14022 error=False
  [gemini-3.1-pro-preview] Running gemini-3.1-pro-preview (gemini-family)...
    turns=17 tokens_in=421023 tokens_out=5008 error=False

STEP 3: Check stray writes (KI-2 mitigation)
  grok-4.5: CLEAN
  gemini-3.1-pro-preview: CLEAN

STEP 4: Parse verdicts
  grok-4.5: ACCEPT-WITH-NITS
  gemini-3.1-pro-preview: ACCEPT

STEP 5: Append telemetry rows
  Appended: grok-4.5 -> ACCEPT-WITH-NITS
  Appended: gemini-3.1-pro-preview -> ACCEPT
  Total rows appended: 2

STEP 6: Gate decision
  Validators: 2
  ACCEPT: 2 | REJECT: 0 | HUMAN_DECISION: 0 | ERROR: 0 | UNKNOWN: 0
  GATE: ACCEPT
  REASON: All 2 validator(s) ACCEPT (1 with nits)
```

The summary JSON is written to `phase-3.2/reviews/orchestrated/review-summary.json`.

---

## Honesty bounds

### No Mission cosplay

The GO-NO-GO decision was command-orchestrated, not Mission-native
(`droid exec --mission` is a no-op that reports success — Probe 1). The
demo command is a Python script, not a Mission. PRD §15 Act 2 describes
"same sprint as a Mission" — the honest version is "push a scripted button."
The command is `python3 tools/orchestrate-review.py ...`, not `droid exec
--mission`.

### "Close the laptop" — DROPPED

PRD §15 Act 2: "Kick it off, close the laptop, come back to a completed
sprint." This claim is NOT demonstrated. The orchestrator is a foreground
script that runs in a terminal. Closing the laptop kills the process. A
durable runner (background process, systemd, CI) has not been built or
evidenced. Building one is out of scope for Track C. The claim is dropped.

What IS demonstrated: the orchestration stopped being a human relay. The
operator runs one command instead of 16+ manual handoffs (Act 1's §13
comparison). The guarantees — cross-family validation, evidence-bundle
consumption, stray-write checks, telemetry — are enforced by the script,
not by operator discipline.

### Orchestrator flakiness — shown honestly

Track B step B1 (orchestration hardening) has NOT been completed. The
orchestrator works end-to-end (12 telemetry rows in `telemetry/runs.jsonl`
from 6 orchestrated runs prove it), but it has residual flakiness:

**Observed telemetry (from committed `telemetry/runs.jsonl`):**

| Run | Grok verdict | Gemini verdict | Gate | Notes |
|-----|-------------|----------------|------|-------|
| 1 | ACCEPT-WITH-NITS | ACCEPT | ACCEPT | clean |
| 2 | ACCEPT | **ERROR** (0 tokens) | STOP | gemini provider API hiccup |
| 3 | ACCEPT | ACCEPT | ACCEPT | clean |
| 4 | **REJECT** | ACCEPT | REJECT | split verdict — grok found issues |
| 5 | **REJECT** | **UNKNOWN** (is_error) | STOP | both validators problematic |
| 6 | ACCEPT-WITH-NITS | ACCEPT | ACCEPT | clean |

2 of 6 runs had ERROR/UNKNOWN for gemini (provider API returning 0 tokens).
1 of 6 had a split verdict (grok REJECT, gemini ACCEPT — a genuine
cross-family disagreement, not a flake). The B1 hardening would add:
- retry logic for transient API failures (up to 2 retries with delay)
- stray-write baseline (set difference, not set equality — avoids false
  positives from pre-existing dirty-tree paths)
- adapter shim + `run-with-model.sh` usage (OPERATING-RULES §14)

Until B1 is done, the flakiness is shown honestly. A failed run is shown as
a failure, not hidden.

### What the orchestrator does NOT do yet

- **No retry logic.** A validator returning 0 tokens or an ERROR verdict
  is recorded as-is. B1 adds retry (up to 2 times with delay).
- **No stray-write baseline.** The current check compares `git status
  --porcelain` before and after, and STOPs if anything changed — including
  pre-existing dirty paths (false positive). B1 fixes this with a set
  difference.
- **No adapter shim.** The script calls `DROID_BIN` directly instead of
  using `tools/adapters/factory.py` and `tools/run-with-model.sh`
  (OPERATING-RULES §14). B1 fixes this.
- **No durable runner.** The script runs in the foreground. Closing the
  terminal kills it.

---

## Replay instructions

### Prerequisites

- `droid` CLI at 0.186.0 (or re-verify probes after upgrade)
- The pilot repo with its venv: `/Users/factory/work/quantum-bank--llms-txt-pilot`
- The framework repo: `/Users/factory/work/adversarial-sprint-dev-3.2-build`
- Cross-family validator models accessible: `grok-4.5`, `gemini-3.1-pro-preview`

### Run the orchestrator

```sh
cd /Users/factory/work/adversarial-sprint-dev-3.2-build

python3 tools/orchestrate-review.py \
    --framework-root . \
    --pilot-root /Users/factory/work/quantum-bank--llms-txt-pilot \
    --pilot-python /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python \
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
```

### Review the output

```sh
# Telemetry rows appended
tail -2 telemetry/runs.jsonl

# Summary
cat phase-3.2/reviews/orchestrated/review-summary.json
```

### Run it N times (single runs lie)

The orchestrator is designed to be run N times with identical parameters.
Each run appends 2 rows to `telemetry/runs.jsonl`. Compare the rows across
runs to see variance in tokens, turns, and verdicts. The flakiness (if any)
is visible in the telemetry — do not hide it.
