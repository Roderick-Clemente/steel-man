# tools/ — RUN LEDGER (committed; durable)

Real droid exec / validator invocations across the
`factory/build-gate-tools` ladder and the phase-4.5 sprint loop.

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

---

# Phase-4.5 sprint loop — live attempt progression

Ten attempts to drive a single chunk (multi-home data model with
backward-compatible optional parameters) through the full pipeline:
planner → dual plan review → gate → test-designer → RED → executor →
verify-green → validators. Pilot: a private device-dashboard app.
Framework branch: `factory/schema-v3-and-subagent-executor`.

## Attempt progression

| Attempt | Exit | What it proved | What it found |
|---------|------|----------------|---------------|
| 1–5 | various | Pipeline could not reach the executor seat. Planner timeouts, §5.3 gate refusals, F-4 crash, F-5 0-byte envelopes. Each blocker fixed before re-running. | F-1 through F-7 (see four-arm experiment below) |
| 6 | partial | **First run to traverse every seat.** kimi-k3 executor produced working code: 19 turns, ~6 min, 477 lines across 7 files, 8/8 locked tests, 37/37 full suite. Solved the hardest constraint (optional `home_id` with defaults) unprompted. | KI-10: validator prompt never rendered (6 placeholders passed through verbatim). KI-11: `--full-suite` never passed by runner. |
| 7–8 | refusal | Plan-review loop iterated for the first time (KI-8 fix). Contract tightened from 10 to 15 criteria on reviewer evidence. | KI-7: planner accepted a chat summary as the plan. KI-8: planner planned against a guess, not the authored contract. KI-9: RED classifier rejected a valid RED for explaining itself. |
| 9 | REJECT_IMPL | **KI-10 proven fixed live.** Both validators reviewed the same rendered prompt (9,514 bytes, zero surviving placeholders) for the first time. They immediately caught a real defect: regression evidence missing from the bundle. | KI-15: bundle produced twice (second overwrites first), wrong command runs (bare pytest, zero tests collected), exit 5 counts as pass. |
| 10 | REJECT_IMPL | **KI-11/KI-15 proven fixed live.** Bundle shows `full_suite: 35 passed, exit 0` with the declared command recorded. grok caught a real bug the test suite endorsed: implementation silently weakened criterion 9 (reported as "substituted fallback" instead of "reported as such"). gemini accepted the same code. | KI-16: executor retried blind after rejection — no feedback rendered into retry prompt. KI-13 reproduced: rejected commit `7f9d467` on pilot branch before gate. KI-14 filed: invalid RED retries executor instead of test-designer. |
| 11 | pending | Will test KI-16 fix live: executor should fix criterion 9 on first retry because grok's finding is now rendered into its prompt. | Awaiting model availability window. |

**Summary: 16 known issues found, 12 fixed, 2 open (KI-13, KI-14), 2 closed as documented limitations (KI-5, KI-12). Every refusal so far has been a genuine defect caught before it did damage.**

## Per-seat cost breakdown — attempt 6 (kimi-k3 executor)

**Caveat: this data is inflated by KI-10.** grok recovered its inputs by reading the entire repo (161K input tokens, 28 turns). gemini processed unrendered placeholder text (607K input tokens). The fixed framework should show much lower validator costs. Re-measurement on the fixed framework is required before drawing cost conclusions.

| Seat | Model | Family | Turns | Input tok | Output tok | Credits | Duration |
|------|-------|--------|-------|-----------|------------|---------|----------|
| Planner | claude-opus-5 | claude | 2 | 26,497 | 5,530 | 48,688 | 42s |
| Plan reviewer 1 | grok-4.5 | xai | 8 | 43,210 | 12,936 | 88,520 | 4m 7s |
| Plan reviewer 2 | gemini-3.1-pro-preview | google | 23 | 82,123 | 8,472 | 104,239 | 2m 18s |
| Test designer | gpt-5.2 | openai | 14 | 44,679 | 23,010 | 194,481 | 4m 50s |
| Executor | kimi-k3 | moonshot | 19 | 45,764 | 18,956 | 235,758 | 6m 0s |
| Validator 1 | grok-4.5 | xai | 28 | 161,433 | 19,389 | 417,046 | 6m 4s |
| Validator 2 | gemini-3.1-pro-preview | google | 20 | 606,611 | 6,948 | 556,744 | 2m 9s |
| **TOTAL** | | | **114** | **1,010,317** | **94,241** | **1,745,476** | ~27m |

**Cost distribution (inflated):** Executor 13.5%, Validators 55.7%, Plan reviewers 11.0%, Test designer 11.1%, Planner 2.8%.

Source: per-seat `*-envelope.json` files in the pilot's `.adversarial-sprint/build-evidence-homes-c1-kimi/` directory. Each envelope contains `num_turns`, `duration_ms`, and `usage` (`input_tokens`, `output_tokens`, `factory_credits`, `cache_read_input_tokens`).

## Four-arm experiment (pre-sprint, framework enhancement validation)

Ran before the sprint loop to validate `--force-accept`, `--verify-mode`, and `per_call_timeout_seconds` enhancements.

| Arm | Flags | Exit | What happened |
|-----|-------|------|---------------|
| control | `--unattended` | 4 | §5.3 refusal (7 open blocker/high findings). Correct behavior. |
| probe | `--force-accept-reason "..."` | 2 | Flag doesn't exist as CLI arg; only `force_accept_reason` config key works. Ergonomics gap (F-3). |
| test B | `--force-accept` | 1 | Override fired correctly, then F-4 crash (`AttributeError: NoneType.value`). |
| test C | `--force-accept --verify-mode` | 2 | Both overrides worked, but executor produced 0-byte envelopes (F-5: `MultiEdit` invalid tool id). |

Findings: F-1 (`--force-accept` works), F-2 (`--verify-mode` works), F-3 (`--force-accept-reason` ergonomics gap), F-4 (None crash, fixed), F-5 (`MultiEdit` invalid, fixed), F-6 (family-guard message misleading but map correct), F-7 (plan-reviewer verdict binding to `plan_sha256`).

## The KI-7 shape — recurring architectural pattern

Four of the sixteen issues share the same structural defect:

| Instance | Seat | What was missing | What happened |
|----------|------|------------------|---------------|
| KI-7 | Planner | Write tool (prompt named an output path) | Seat improvised a shell write, failed silently, reported success |
| KI-10 | Validator | Rendered prompt (6 placeholders passed verbatim) | One validator read the repo to recover inputs; the other refused |
| KI-15 | Evidence bundle | Correct producer (second overwrote first) | Validators read a bundle missing the regression evidence |
| KI-16 | Executor (retry) | Rejection feedback (finding text not rendered) | Retry was the same dice roll at full cost — no knowledge of why it was refused |

**The pattern:** a seat is invoked without an input it needs, produces a plausible artifact anyway, and every success signal the framework owns reports normal. `seat_outcome="ok"` means the seat returned a parseable envelope, not that it did its job. The framework's own success signals cannot distinguish "the seat did its work" from "the seat produced something that looks like work."

**What catches it:** only an adversarial reviewer comparing the artifact against the contract can see that the stronger claim was never honored. This is the architectural argument for cross-family validation — it is not redundancy, it is the only layer that can detect this class of defect.

**The pattern to grep for:** any retry or re-invocation path that does not carry forward the reason it was triggered. If the retry prompt is identical to the first-attempt prompt, the retry is not a retry.

## Upcoming: two-arm executor experiment

The next phase measures whether a cheap executor (kimi-k3, moonshot-family) produces cheaper full-cycle results than an expensive executor (gpt-5.2, openai-family), or whether executor quality shifts cost to the validators.

Same plan, same locked tests, same validators, different executor. Two arms. The fixed framework (KI-10, KI-15, KI-16, verdict-aware routing) is the prerequisite — without it, the validator data is unsound and the comparison is meaningless. Attempt 11 (pending) is the last gate: if the executor fixes criterion 9 on its first retry via KI-16's feedback loop and both validators ACCEPT, the experiment can run.

