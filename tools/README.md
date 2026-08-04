# tools/ — validation primitive + ladder

This is the validation gating scaffold used by `factory/build-gate-
tools` for a validator-pipeline test. It builds the primitive,
exercises it, and refuses silent-green. One rung = one commit.

## What this primitive is

A two-seat configuration in which one seat (the **validator**)
inspects a git diff and emits a structured verdict, and another
seat (the **executor**, this CLI) orchestrates the inputs and
applies a fixed stack of gates around the validator's output.
The gates intentionally refuse to mint `exit-0-green` from:
- empty tool-call traces
- tool calls with paired `is_error=True`
- missing required-source coverage
- ACCEPT verdicts (without an ACCEPT-WITH-NITS or REJECT shape)
- ACCEPT without a normalized "doubled-charset" finding
- same-family validator and executor (a key for self-orchestration)

The primitive is general; the fixtures here are wired to a
specific defect (Content-Type charset-doubling on
`pilot/llms-txt`) only to make the gates' verdicts inspectable.

## Where the fixtures live

```
tools/
├── README.md                    ← this file
├── KNOWN-ISSUES.md              ← known issues / runway
├── render-blind-prompt.py       ← rung-2 renderer (pin + spec → blinder)
├── validator-spec/
│   └── llms-doubled-charset.md  ← the spec handed to the validator
└── fixtures/
    ├── doubled-charset-pin.json       ← the bug-present pin (BASE / HEAD)
    ├── blind-prompt.txt               ← committed only if you re-run the renderer
    ├── rung1-grep-gate.py             ← defect-literal pin checker
    ├── rung2-canary-check.py          ← 14-marker transcript-leak canary
    ├── rung3-extract-tool-calls.py    ← parse inner-session jsonl → digest
    ├── rung3-tool-call-digest.json    ← committed run-time evidence
    ├── rung3-gate.py                  ← shape: num_turns, tokens, tool calls
    ├── rung4-family-decisions.json    ← validator/executor family verdicts
    ├── rung4-family-gate.py           ← family-collision gate
    ├── rung5-gate.py                  ← tool-use events + required coverage
    ├── rung6-gate.py                  ← decision ≠ ACCEPT + finding shape
    ├── rung7-empty-diff-blind-prompt.txt
    ├── rung7-blocked-tools-blind-prompt.txt
    ├── rung7-configA-digest.json      ← fabricates-from-source REJECT
    ├── rung7-configB-digest.json      ← blocked-tools ACCEPT (gates RED)
    ├── rung7-reflection.md            ← what rung 7 found (positive + negative)
    └── rung7-reconciliation.md       ← rung-6 vs human verdict (SUPERSEDED +
                                         corrected severity-divergence analysis)
```

The runtime output of the validator runs lives under
`build-evidence/` and is **NOT** committed (it is ephemeral;
paths like `/tmp/rung3-fresh-clone-…` or `~/.factory/sessions/
-private-tmp-rung{n}-…` referenced in the digest JSONs are
captures from this audit run and will not survive a reboot —
they're not durable handles).

## The 7-rung ladder

| rung | what                                                       | gate (commit)                              |
|------|------------------------------------------------------------|--------------------------------------------|
|  1   | pin the bug-present state (BASE, HEAD, diff_sha256)        | `rung1-grep-gate.py` (commit `d27b720`)    |
|  2   | render the blind spec+diff prompt; canary transcript-leaks | `rung2-canary-check.py` (commit `e14aa30`) |
|  3   | invoke the validator via `droid exec`; capture envelope    | `rung3-gate.py` + digest (commit `ce2513e`)|
|  4   | family-collide gate (validator≠executor family)            | `rung4-family-gate.py` (commit `11121b0`) |
|  5   | tool-call event gate (paired tool_use ↔ tool_result, required-source coverage) | `rung5-gate.py` (commit `629dec7`) |
|  6   | decision invariant (decision ≠ ACCEPT + finding shape)     | `rung6-gate.py` (commit `5e927bc`)         |
|  7   | silent-green negative control (no-op run fires FAIL LOUD)  | `rung7-*-digest.json` (commit `2098859`)   |

Each rung is its own commit. No PRs opened against `main`. The
branch lives at `factory/build-gate-tools`.

## How each gate asserts

### rung-3

`rung3-gate.py` requires:
- `num_turns > 0`
- `(input_tokens > 0) OR (output_tokens > 0)`
- `tool_calls_total ≥ 1`
- at least one tool name in `{Read, Execute, Glob, Grep, LS}` — the
  validator's expected tool surface

This catches silent-green shapes where the verifier responded
without exercising any tools. It does NOT inspect transcript
prose (that's rung 5 and rung 6).

### rung-4

`rung4-family-gate.py` reads `rung4-family-decisions.json` and:
- REFUSES when validator's family and executor's family collide
- REFUSES when either family is unknown
- REFUSES when the executor uses a silent-fallback proxy
- ALLOWS only when the families are clearly distinct

The decision is a deterministic function call; the live state and
eight negative controls all run through it.

### rung-5

`rung5-gate.py` parses the inner droid session jsonl directly and:
- requires `tool_use` and `tool_result` events to be paired by
  `tool_use_id`
- requires every paired `tool_result.is_error` to be `False`
- requires at least one `Read` against `api/llms_txt.py` (the
  defect source file)

This is the rung that owns "the validator actually inspected the
code, not narrated from KB". It is intentionally transcript-
prose-free — it will not pass on a verdict string alone.

### rung-6

`rung6-gate.py` parses the verifier's verdict text and:
- recognises `Verdict/Decision: ACCEPT | ACCEPT-WITH-NITS | REJECT`
- REFUSES `ACCEPT` (only ACCEPT-WITH-NITS or REJECT pass)
- REFUSES any verdict missing a normalized doubled-charset
  mention (regex matches 8 phrasings)

Both halves must pass. Two fabricated verdicts and seven
canonical-shape negative controls are committed in the gate.

### rung-7

`rung7-{configA,configB}-digest.json` plus `rung7-reflection.md`.

- Config A: empty diff + default tools → validator fabricates
  REJECT from source inspection. rung-3 GREEN, rung-5 GREEN,
  rung-6 may pass or fail depending on verdict template. **False-
  REJECT via source-read hole exposed** (see KNOWN-ISSUES.md).
- Config B: empty diff + `--enabled-tools Execute,Glob` → validator
  emits ACCEPT; rung-3 RED, rung-5 RED, rung-6 RED. The
  designed "fail loud" intent met.

## Seat → model config knob (`plan/validate/execute/validate`)

The four-stage harness pattern (typical seat layout):
- **plan** (orchestrator-side; not in this primitive): decide what
  shape of evidence is required from the next seat.
- **validate** (validator seat; default for rung 3 onward): read
  the rendered spec+diff prompt and emit a structured verdict.
- **execute** (executor seat; this CLI): orchestrate safe
  invocations, parse envelopes, run gates, commit.
- **validate** (validator seat; for rung-4 cross-validation): when
  the same prompt is run on multiple validator seats, the rung-4
  family rule decides whether validators are de-facto equivalent.

The contract:
- Validator seat's `providerLock` and `apiProviderLock` are stable
  for the run. They are read out of the inner-session settings.json.
- Executor seat's seat-id (here: `effectiveFactoryRouterModel`) is
  routed by auto-mode and may cascade through a `fallbackChain`.
  The cascade is captured in `rung4-family-decisions.json`.

### Config-contract TODO: "family" must mean model lineage, not serving-provider

**Currently rung-4 keys on `apiProviderLock` (provider-of-record)
and falls back to `providerLock` if absent.** This is wrong for
the brief's intent. Two distinct models on the same provider
should NOT collapse to the same family:

- Example: MiniMax-3 (`fireworks`) and Kimi-K2.7 (`fireworks`)
  would currently be classified as the same family even though
  they are different model lineages.
- The brief's intent is "model lineage" — i.e., the model
  itself, not the vendor serving it. A correct family gate should
  key on the resolved model-id (`modelId`) and corroborate against
  the validator's `providerLock`.

A future rung-8 rework of `rung4-family-gate.py` should:
1. Read the resolved `modelId` for each seat (validator + executor).
2. Treat two seats as the same family iff the model lineage matches.
3. Provider-lock equality becomes a secondary corroboration (NOT the
   primary key). Two seats on the same provider with DIFFERENT model
   IDs are NOT the same family.

In the meantime, the LIVE factory/build-gate-tools state has
`validator=openai/gpt-5.4-mini` and `executor=fireworks/minimax-m3`,
which is genuinely a different lineage on different provider; the
gate is correct for current state but is structurally wrong for the
configuration-contract intent. Flagged, not fixed.

## How to re-run

A canonical re-execution flow:

```
cd /Users/factory/work/adversarial-sprint-dev
# rung 1
python3 tools/fixtures/rung1-grep-gate.py --exit-loud

# rung 2 (regenerate the blind prompt if the pin/spec changed)
python3 tools/render-blind-prompt.py
python3 tools/fixtures/rung2-canary-check.py --exit-loud

# rung 3 (use a fresh clone identical to the original audit)
FRESH="/tmp/rung3-fresh-clone-$(date +%s)"
cp -r ~/work/quantum-bank--llms-txt-pilot "$FRESH"
cd "$FRESH"; git checkout 2b70eae11969a5eabece97a81a80cf42853d7514
cd <repo>
droid exec --model gpt-5.4-mini --output-format json \
    -f tools/fixtures/blind-prompt.txt \
    --auto low --cwd "$FRESH" \
    --enabled-tools Read,Execute,Glob,Grep,LS \
    > build-evidence/rung3-droid-exec-output.json
# regenerate digest
python3 tools/fixtures/rung3-extract-tool-calls.py
# shape-gate
python3 tools/fixtures/rung3-gate.py --exit-loud

# rung 4
python3 tools/fixtures/rung4-family-gate.py --exit-loud

# rung 5
python3 tools/fixtures/rung5-gate.py --exit-loud \
    --envelope build-evidence/rung3-droid-exec-output.json

# rung 6
python3 tools/fixtures/rung6-gate.py --exit-loud \
    --envelope build-evidence/rung3-droid-exec-output.json

# rung 7 (fail-loud negative control)
# see tools/fixtures/rung7-reflection.md for Config A / B details.
```

A `make-rungN.sh` wrapper is intentionally NOT provided; rung
runs are short, and inline commands keep prose-level intent
visible in the audit trail.

## Where the brief's intention shifts as we climb the rungs

| axis | rung that owns it                                    |
|------|-------------------------------------------------------|
| "Did the run actually happen?"                     | rung 3 |
| "Are the seats really different?"                  | rung 4 |
| "Did the validator actually inspect, not narrate?" | rung 5 |
| "Did the verdict LITERALLY report what it claims?" | rung 6 |
| "Does the pipeline fail loud on a no-op?"          | rung 7 |

A ladder with each rung owning one orthogonal axis keeps a
failure from sounding as if it were the gate's silent-green
when the validator is the actual culprit, or vice versa.

## Routing knobs you may want to tweak

- `--model gpt-5.4-mini` — the validator's model in rung 3.
  Swap to test family-overlap. (Keep `--auto low`; do not pass
  `--skip-permissions-unsafe` — they conflict.)
- `--enabled-tools …` — the surface the validator may exercise.
  rung 7 config B deliberately strips Read + Grep; rung 7 config
  A uses the default surface; both are recorded.
- `--cwd <fresh-clone>` — the absolute path the validator reads.
  This path is captured into the validator's `file_path` strings,
  which is why the digests reference `/private/tmp/rungn-fresh-
  clone-…` — those references are captures, not durable handles.

## Files that intentionally remain outside this directory

- `pilot-llms-txt-spec.md` — top-of-bridge on the canonical
  adversarial-sprint-dev main; not part of the validation
  primitive.
- `OPERATING-RULES.md` / `wake-loop.md` / `wiki-link-audit.py` —
  pre-existing scaffolding.

## Closing note

This page is the audit trail. Each rung's verdict is in the
relevant `rungN-{gate,digest}.{py,json}` artifact and the
commits themselves carry the verbatim RED and GREEN output of
the gate run. Reading commit-by-commit in chronological order
is sufficient for replay.

See `KNOWN-ISSUES.md` for the false-REJECT hole exposed by
rung 7 and the family-key TODO flagged above. Both are rung-8+
work and are explicitly OUT OF SCOPE under this rung-7 closure.
