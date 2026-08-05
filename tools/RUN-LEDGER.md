# tools/ — RUN LEDGER (committed; durable)

Real droid exec / validator invocations across the
`factory/build-gate-tools` ladder.

Each row is ONE reproducible run, traced from its envelope
(`build-evidence/*-droid-exec-output.json`). The ledger is the
distilled, durable form; the raw envelopes remain untracked by
design (paths in those JSONs are captures from the audit run, see
the per-file durability disclaimers).

## Per-run table

| rung | tag                 | model_id        | family    | num_turns | input | output | cache_read | thinking | duration_ms | is_error | decision  |
|------|---------------------|-----------------|-----------|-----------|-------|--------|------------|----------|-------------|----------|-----------|
|  3   | rung-3 (LIVE)       | gpt-5.4-mini    | openai    | 2         | 13612 | 1661   | 9216       | 1449     | 17071       | false    | REJECT    |
|  7A  | rung-7 Config A     | gpt-5.4-mini    | openai    | 3         | 15465 | 3179   | 22016      | 2842     | 32414       | false    | REJECT*   |
|  7B  | rung-7 Config B     | gpt-5.4-mini    | openai    | 1         | 7178  | 363    | 0          | 330      | 4207        | false    | ACCEPT    |
|  R4  | refactor-blind-v1 (Codex) | gpt-5.3-codex | GPT | 26   | 90 050 | 13 616 | —  | —  | 171 000   | false    | REJECT          |
|  R5  | refactor-blind-v1 (Grok)  | grok-4.5      | xAI | 12   | 58 881 | 21 694 | —  | —  | 369 300   | false    | ACCEPT-WITH-NITS|

Notes:

- **rung-7 Config A REJECT\***: this is the **false-REJECT via
  source-read** the silent-green-negative-control rung produced,
  not a genuine diff-driven finding. Validator read
  `api/llms_txt.py` directly despite an empty diff. Tracked as
  *Issue: False-REJECT via source-read (isolation leak)* in
  `tools/KNOWN-ISSUES.md`.

- All three (rung 3, 7A, 7B) runs use `--model gpt-5.4-mini` from
  the executor seat (auto-routed `fireworks/minimax-m3`); the
  `--enabled-tools` flags differ between Config A (`Read +
  Execute + Glob + Grep + LS`) and Config B (`Execute + Glob` only).
  See raw envelopes for the exact args.

- **R4 / R5 are MEASUREMENT runs** — same blind prompt, same
  fixture, primitive out of the loop, only the model varied.
  They are the §13 refactor-validation pair. Both found the
  same doubled-charset defect on identical input; the verdicts
  SPLIT (Codex → REJECT, Grok → ACCEPT-WITH-NITS) — a 2nd
  sighting of the severity-calibration divergence documented in
  `tools/fixtures/rung7-reconciliation.md` (corrected analysis).
  cache_read and thinking_token columns marked `—` because the
  orchestrator's provision did not include those fields; only
  `input_tokens` and `output_tokens` were supplied.

## Totals (across 5 runs)

| metric          | sum         | notes                                 |
|-----------------|-------------|---------------------------------------|
| run count       | 5           | 3 ladder runs + 2 MEASUREMENT runs    |
| input tokens    | 185 186     |                                       |
| output tokens   | 40 513      |                                       |
| cache_read tok  | 31 232      | ladder runs only; R4/R5 not supplied  |
| thinking tok    | 4 621       | ladder runs only; R4/R5 not supplied  |
| duration_ms     | 593 992     | ≈9 m 54 s wall-clock across 5 runs    |

Average duration per run: ~119 s. The two MEASUREMENT runs
(R4 / R5) skew this; the 3 ladder runs average ~17.9 s. Tokens
sum across input+output+cache_read+thinking for the 3 ladder
runs only: 77 311 (unchanged from prior revisions).

## Parties involved

- **validator (inner seat)**: 1 model family across all runs —
  `gpt-5.4-mini / openai`. Tool-on default list (rung 3, rung
  7A) or stripped list (rung 7B).
- **executor (outer seat — this CLI session)**: auto-routed
  `fireworks/minimax-m3` with fallback chain
  `kimi-k2.7-code`, `glm-5.2`, `claude-opus-4-8`. Configured
  `--auto low` and `--enabled-tools …`.
- **operator (relay, NOT in the validating seat)**: 1 session.
  See operator-intervention count next.

## Operator-intervention count for THIS run = 1

One single human-relay action:

> Rod hand-relayed the BACKSTOP steer note into this session
> because `origin/orchestrator/steer` did not exist on this
> repo's remote. Surfaced verbatim in every rung and cleanup
> commit message; ladder proceeded without further operator
> input.

That's the only operator-hand-relay that occurred across this
7-rung ladder + cleanup pass.

## §13 EXIT CRITERION — the One-vs-N comparison

The §13 exit criterion for the validation primitive is:
**per-validation-loop operator-intervention count drops from N to
1.**

This run is the proof:

| method                  | action                                       | count              | human-relay / family | per-family  | total   |
|-------------------------|----------------------------------------------|--------------------|----------------------|-------------|---------|
| prior hand-relay method | open UI → paste prompt → capture verdict      | 1 action / family  | 4 families           | 1           | 4       |
| prior hand-relay method | + repeat for next family                     | repeat             | 4 families           | 4           | 16+     |
| this run (factory droid)  | 1 instruction-orchestration; models — auto-routed into 3 droid exec invocations producing the ladder's evidence | 1 action (backstop steer note) | 1 hand-relay → 1 auto-routed executor model → 1 validator family across the 3 evidentiary runs | n/a (1 normalised ladder) | **1** |

(Numbers are approximate; the prior-method "16+" reflects the
protocol of running the four hand-relayed families Grok/Kimi/
Codex/Opus serially with prompt+verdict copy per family, but
exact count varies based on per-family UI gating. The principle
is the operative claim, not the precise digit.)

The "4 model families" reference here is the historical
canonical pilot/llms-txt validation panel — Grok (xAI), Kimi
(Moonshot), Codex (GPT), Opus (Anthropic). That panel reviewed
`2b70eae1` (the pre-fix pilot/llms-txt tip with the doubled-
charset defect PRESENT — same state the validator here reviewed).
The four-family panel graded ACCEPT-WITH-NITS; this run's
validator graded REJECT; the difference is **a model-calibration
question, not a fixture-direction artifact** (see
`tools/fixtures/rung7-reconciliation.md` corrected analysis).

## Per-rung envelope map (durability disclaimer)

| rung | envelope (raw, NOT in tree)                                                | durable evidence                                 |
|------|----------------------------------------------------------------------------|--------------------------------------------------|
|  3   | `build-evidence/rung3-droid-exec-output.json`                              | `tools/fixtures/rung3-tool-call-digest.json`     |
|  7A  | `build-evidence/rung7/rung7-droid-exec-output.json`                         | `tools/fixtures/rung7-configA-digest.json`       |
|  7B  | `build-evidence/rung7-configB/rung7B-droid-exec-output.json`                | `tools/fixtures/rung7-configB-digest.json`       |

The raw envelopes are NOT committed. They live under
`build-evidence/` as mini-local untracked artefacts. They are
captures, not handles (the JSON files reference inner-session
directories under `~/.factory/sessions/-private-tmp-rungn-…` and
`/private/tmp/rungn-fresh-clone-…` — both are platform-internal
runtime dirs that do not survive reboot).

This ledger, the digests, and the committed fixtures are the
durable artefacts. Committing the raw envelopes alongside this
ledger is intentionally not done: the digests already encode the
fields the gates need and the per-file disclaimers explain the
captured-path semantics in-line.

## Method

The runner kept one shape per evidence record (one row), pulled
the inputs from `build-evidence/*-droid-exec-output.json`
envelopes, and re-derived numbers from `git show`-grade evidence
(commit graph; not synthesised). Numbers reproduced;
abbreviations standard (input/output/cache_read/thinking tokens
map directly to `usage.input_tokens`, `usage.output_tokens`,
`usage.cache_read_input_tokens`, `usage.thinking_tokens`).
