# Sprint run result — QuantumBank /api/* 404 JSON

- **Run id:** `r-phase45-20260815-230258`
- **Date:** 2026-08-16 (started 23:02:58, ended 23:32:27 local; ~28 min wall)
- **Payload:** content-negotiated 404 handler for QuantumBank
- **Outcome:** full adversarial loop passed on real model calls; the pilot
  fix is committed and dual cross-family validation approved. The runner then
  crashed on the final *framework-side audit commit* (a split-repo topology
  issue, not a modeling failure). Finalized by hand per operator decision.

## Roster (config C)
| Seat | Model | Family |
|------|-------|--------|
| Planner | claude-opus-5 | claude |
| Plan reviewer 1 | grok-4.5 | grok |
| Plan reviewer 2 | gemini-3.1-pro-preview | gemini |
| Executor | glm-5.2 | glm (zhipu) |
| Validator 1 | grok-4.5 | grok |
| Validator 2 | kimi-k3 | kimi (moonshot) |

## Stage outcomes
1. Planner wrote `evidence/plan.md` (hash-bound, sha256 `2c2edbcc…`).
2. Plan reviewer 1 (grok-4.5): **REJECT**, 5 findings.
3. Plan reviewer 2 (gemini-3.1-pro-preview): **APPROVE**, 2 findings.
4. Reconcile gate: 1/2 APPROVE bound + no open blocker/high -> **auto-accept** (unattended).
5. Executor (glm-5.2): implemented fix, **21 locked + 90 full-suite tests pass -> GREEN**,
   committed pilot `ab139640`.
6. Validators (grok-4.5, kimi-k3): both **ACCEPT-WITH-NITS**; gate **ACCEPT**; no stray writes.
7. Framework audit commit: **FAILED** — see Known issue.

## The fix (pilot `01292042` -> `ab139640`, `api/four_o_four.py`)
```python
from flask import request, jsonify


def handle_404():
    # Content-negotiated 404: API paths get a parseable JSON error body,
    # non-API paths keep the existing HTML 404 response.
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return "404 Not Found", 404
```

## Token cost by role (completing run)
| Role | Model | Input | Output | Cache-read | Thinking | Sec |
|------|-------|------:|-------:|-----------:|---------:|----:|
| planner | claude-opus-5 | 34 | 26,525 | 720,817 | 2,057 | 330 |
| plan-rev1 | grok-4.5 | 71,208 | 31,688 | 1,176,704 | 23,226 | 550 |
| plan-rev2 | gemini-3.1-pro | 812,209 | 13,387 | 634,152 | 3,308 | 168 |
| executor | glm-5.2 | 9,843 | 2,284 | 99,104 | 0 | 42 |
| validator1 | grok-4.5 | 91,906 | 15,471 | 969,856 | 8,220 | 267 |
| validator2 | kimi-k3 | 76,152 | 23,685 | 1,318,424 | 0 | 344 |
| **total** | | **1,061,352** | **113,040** | **4,919,057** | **36,811** | **1,701** |

Note: the executor row is not in `telemetry/runs.jsonl` (the crash happened before its
row flushed); its usage above is read from `evidence/c1/c1-ex-envelope.json`.

## Fixes applied to the framework clone (branch `factory/readiness-fixes`)
- `34b3272` — drop non-existent `ApplyPatch`/`MultiEdit` tool ids; droid 0.180's
  registry only has `Read,Glob,Grep,LS,Edit,Create,Execute`. Passing the missing
  ids made `droid exec` reject the list (`Unknown tool identifier(s)`) and emit a
  0-byte envelope.
- `3554cdc` — commit the generated lock manifest so the §7/§15 clean-tree preflight
  passes on re-run.

## Known issue (not fixed — deferred)
`commit_chunk_change` commits only into the framework repo (`_REPO_ROOT`) and stages
the evidence tree. With `evidence_output_dir` pointed *outside* the framework clone
(our split-repo lab; the `[H-9]` path), nothing is staged, so `git commit` fails with
the empty "nothing to commit" error. **One-line fix for a clean exit:** set
`evidence_output_dir` to a path *inside* `framework_root` (e.g.
`framework/pilot-evidence`), which lets the audit commit stage+commit the bundle.
The substantive loop is unaffected.

## Evidence locations
- `sprint/evidence/plan.md`, `plan-reviewer-{1,2}-envelope.json`, `reconcile-packet.txt`
- `sprint/evidence/c1/` — executor prompt/envelope, `c1-bundle.json` (signed),
  `reviews/` (validator envelopes + `review-summary.json`),
  `executor-stray-test_syntax.py` (executor side-probe, preserved)
- `sprint/telemetry/runs.jsonl`, `sprint/telemetry/findings.jsonl`
- Pilot fix commit: `quantum-bank` @ `ab139640`

## Advisor review — answers (Q1–Q6)

**Q1. Did `tools/sprint-loop.py` execute? Exact command.**
Yes. The runner drove the entire loop; this was **not** the skill plus a
hand-invoked `droid exec`. Command, run from the lab root with
`EVIDENCE_SIGNING_KEY` exported:
```
python3 framework/tools/sprint-loop.py \
  --config sprint/config.json \
  --chunks-file sprint/chunks.json \
  --unattended
```
The runner emitted the STEP 1..4 banners, the reconcile gate, and fired all six
model calls itself (see `run.log`).

**Q2. Are the telemetry token counts REAL?**
Yes — real and non-zero. Dry-run rows carry
`"note": "dry-run: simulated; no droid exec fired"` with all-zero usage; the live
rows carry `"note": "droid exec returned exit=0"` with real usage. Representative
live rows (`telemetry/runs.jsonl`):
- planner claude-opus-5: input 34, output 26,525, cache_read 720,817, thinking 2,057, 329,988 ms
- reviewer gemini-3.1-pro-preview: input 812,209, output 13,387, cache_read 634,152, 167,548 ms
- validator kimi-k3: input 76,152, output 23,685, cache_read 1,318,424, 343,918 ms

Executor glm-5.2 usage (input 9,843, output 2,284, cache_read 99,104, 41,893 ms)
is in `evidence/c1/c1-ex-envelope.json`, **not** `runs.jsonl`: the crash at the
audit-commit step happened before the executor row flushed (that gap is KI-3).

**Q3. What broke?**
The prediction held — the first live run did not complete cleanly. Four breaks,
all filed in `tools/KNOWN-ISSUES.md` with repros:
- KI-1 planner 600s per-call timeout when no `pilot_spec_file` was wired (fixed).
- KI-2 executor `enabled_tools` named `ApplyPatch`/`MultiEdit`, absent from droid
  0.180 → 0-byte envelope → family='unknown' guard (fixed, commit `34b3272`).
- KI-3 `commit_chunk_change` empty-commit crash when `evidence_output_dir` is
  outside `framework_root` (open; one-line config fix documented).
- KI-4 the gate dropped grok's single HIGH plan-review finding (F-3a91c2) from
  `findings.jsonl` and the reconcile packet, so §5.3 "no open blocker/high" passed
  vacuously (open; silent-green-class defect in the gate's own aggregation).

**Q4. Did chunk boundaries hold?**
This run had a single chunk (`chunks.json` defines only `c1`), so the
CHUNK_0/CHUNK_1 merge failure from the prior run cannot occur here.
Commit-per-chunk mapping: `c1` → one pilot commit `ab139640` (the executor's fix).
The framework-side per-chunk audit commit did **not** happen — it is exactly what
crashed (KI-3) — so there are zero framework audit commits for `c1`. Honest state:
one pilot commit, no audit commit.

**Q5. Was the executor handed the answer? Partially, yes.**
`plan.md` named both the discriminator (`startswith('/api/')`) and the response
helper (`jsonify`), which are implementation choices rather than observable
behaviour. The executor's fix therefore does not demonstrate independent
implementation, and no H3 claim may be drawn from this run. The §13 boundary is:
a plan states *what must be true*; it does not state *how*. This is the third
recorded instance — Phase 4 records the same failure for Phases 1 and 3. Filed
against the **planning stage** (not the executor) as KI-5, with a recommendation
that `plan-lint.py` flag implementation-prescriptive language (method names,
library helpers, function calls) appearing in a spec's behavioural criteria. The
executor did what it was told; the plan told it too much.

**Q6. Which model sat in which seat?**
From the invocation (`config.json` roster) and the resolved `provider`/`family`
fields the runner recorded in `runs.jsonl`, not from any model's self-report:

| Seat | model_id | provider | family |
|------|----------|----------|--------|
| planner | claude-opus-5 | anthropic | claude-family |
| plan reviewer 1 | grok-4.5 | xai | grok-family |
| plan reviewer 2 | gemini-3.1-pro-preview | google | gemini-family |
| executor | glm-5.2 | zhipu | glm-family |
| validator 1 | grok-4.5 | xai | grok-family |
| validator 2 | kimi-k3 | moonshot | kimi-family |

Caveat: the executor's raw envelope does not echo a model field, so its seat
attribution rests on the invocation flag plus the commit body's
`Model: glm-5.2 (providerLock: zhipu)` line, not an envelope self-report. No silent
model substitution was observed (contrast the claude-haiku incident); every other
seat's family is corroborated by its `runs.jsonl` row.
