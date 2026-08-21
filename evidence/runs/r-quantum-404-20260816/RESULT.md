# Sprint run result — QuantumBank `/api/*` 404 response format

**Run id:** `r-phase45-20260815-230258` · **Date:** 2026-08-16 · **Wall time:** ~28 min
**Pilot commit:** `quantum-bank` @ `ab139640` · **Result:** ACCEPTED

---

> **Scope note — read this first.** This run changed **response formatting** for
> unrecognised `/api/*` routes: they returned an HTML error body, so API clients could
> not parse the 404. It is **not** a security finding. No authorization, access-control,
> or data-exposure issue was involved, none was claimed, and no customer data was in
> scope. The change is a content-negotiated error body; browser behaviour elsewhere is
> unchanged.

---

## 1. Executive summary

A defect in a regulated codebase was routed through an automated multi-model review
loop and came out the other side **accepted, tested, and fully evidenced** — without
relaxing the existing quality bar.

| | |
|---|---|
| **Outcome** | Accepted. Fix committed to the pilot repository |
| **Locked target tests** | **21 passed** |
| **Full pilot suite** | **90 passed** |
| **Independent review** | 6 model calls across **5 distinct model families** |
| **Validator verdict** | Both fresh-context validators: **ACCEPT-WITH-NITS** |
| **Unauthorised writes** | None detected |

The loop separates the seat that plans, the seats that review the plan, the seat that
writes the code, and the seats that validate the result — each pinned to a named model,
with family separation enforced so no single vendor grades its own work.

**The most useful output of this run was not the fix.** The run also surfaced a defect
in the review system itself. That finding, its handling, and its regression test are in
§6, and it is the part worth the most scrutiny.

---

## 2. Requirement

| | |
|---|---|
| **Observed** | Unrecognised routes under `/api/*` returned an HTML error body |
| **Impact** | API clients could not parse the 404 response |
| **Required** | `/api/*` returns a parseable JSON error body at status 404 |
| **Constraint** | Non-API paths keep existing HTML behaviour, unchanged |

Stated as observable behaviour. Whether a given request is served JSON or HTML is
verifiable from the response alone.

---

## 3. Outcome

Fix committed as `quantum-bank` `01292042` → `ab139640`, in `api/four_o_four.py`:

```python
from flask import request, jsonify


def handle_404():
    # Content-negotiated 404: API paths get a parseable JSON error body,
    # non-API paths keep the existing HTML 404 response.
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return "404 Not Found", 404
```

Both halves of the requirement are covered: API clients receive parseable JSON; every
other path is untouched.

---

## 4. Evidence at a glance

| Seat | Model | Family | Verdict |
|---|---|---|---|
| Planner | `claude-opus-5` | claude | plan issued, hash-bound |
| Plan reviewer 1 | `grok-4.5` | grok | **REJECT** — 5 findings |
| Plan reviewer 2 | `gemini-3.1-pro-preview` | gemini | **APPROVE** — 2 findings |
| Executor | `glm-5.2` | glm (zhipu) | GREEN — 21 locked + 90 suite |
| Validator 1 | `grok-4.5` | grok | **ACCEPT-WITH-NITS** |
| Validator 2 | `kimi-k3` | kimi (moonshot) | **ACCEPT-WITH-NITS** |

Six live model calls, five distinct families. Seat attribution is taken from the
invocation and the `provider`/`family` fields the runner recorded — **not** from any
model's self-report about itself.

Validators run with **fresh context**: they receive the diff and the evidence bundle,
not the planning conversation, so they cannot inherit the planner's assumptions.

**Token usage — real, metered, non-zero.** Dry-run rows are tagged as simulated and
carry all-zero usage; these are live rows.

| Role | Model | Input | Output | Cache-read | Sec |
|---|---|---:|---:|---:|---:|
| planner | claude-opus-5 | 34 | 26,525 | 720,817 | 330 |
| plan-rev1 | grok-4.5 | 71,208 | 31,688 | 1,176,704 | 550 |
| plan-rev2 | gemini-3.1-pro | 812,209 | 13,387 | 634,152 | 168 |
| executor | glm-5.2 | 9,843 | 2,284 | 99,104 | 42 |
| validator1 | grok-4.5 | 91,906 | 15,471 | 969,856 | 267 |
| validator2 | kimi-k3 | 76,152 | 23,685 | 1,318,424 | 344 |
| **total** | | **1,061,352** | **113,040** | **4,919,057** | **1,701** |

The executor row is read from `evidence/c1/c1-ex-envelope.json` rather than
`telemetry/runs.jsonl` — see §8.

---

## 5. Validation result

| Check | Result |
|---|---|
| Locked target tests | **21 passed** |
| Full pilot suite | **90 passed** |
| Validator 1 (`grok-4.5`, fresh context) | ACCEPT-WITH-NITS |
| Validator 2 (`kimi-k3`, fresh context) | ACCEPT-WITH-NITS |
| Gate decision | **ACCEPT** |
| Stray writes outside declared scope | none detected |

"Locked" tests are hash-pinned before execution so the seat writing the fix cannot
alter the tests that judge it.

---

## 6. Quality system finding

**A defect was found in the review gate itself, during this run.**

Plan reviewer 1 (`grok-4.5`) returned a REJECT carrying a HIGH-severity finding,
`F-3a91c2`. The gate's aggregation step **dropped that finding** before it reached
`findings.jsonl` or the reconcile packet. The acceptance precondition — *at least one
APPROVE and no open blocker/high* — therefore evaluated against an incomplete ledger
and passed **vacuously**, auto-accepting the plan on 1 of 2 approvals.

This is the failure mode that matters most in a regulated context: **the gate reported
success while holding an unreviewed objection.** It did not produce a wrong answer
loudly; it produced a clean one quietly.

Handling:

| Step | Detail |
|---|---|
| **Detected** | During post-run evidence review, by reconciling the reviewer's raw response against the gate's ledger |
| **Replayed** | From the **retained reviewer response**, not a reconstruction — the response was kept as evidence, so the defect was reproducible after the fact |
| **Root cause** | The finding parser desynchronised on a brace inside a JSON string literal in the finding's evidence text |
| **Fixed** | Parser rewritten to consume findings with a JSON decoder rather than brace counting |
| **Regression test** | grok's **actual envelope** from this run is committed as a permanent fixture at `tools/fixtures/ki4-dropped-high/plan-reviewer-1-envelope.json`; the suite asserts all six findings parse and that `F-3a91c2` arrives at `severity=high` |
| **Cross-reviewed** | Fix independently reviewed by two model families before merge; both approved |

Retaining reviewer responses as evidence is what made this recoverable. Without the
original artifact there would have been nothing to replay, and a silently-passing gate
would have stayed silent.

---

## 7. Artifact links

| Artifact | Path |
|---|---|
| Plan (hash-bound, sha256 `2c2edbcc…`) | `evidence/plan.md` |
| Plan reviewer envelopes | `evidence/plan-reviewer-{1,2}-envelope.json` |
| Reconcile packet | `evidence/reconcile-packet.txt` |
| Executor prompt + envelope | `evidence/c1/` |
| Signed evidence bundle | `evidence/c1/c1-bundle.json` |
| Validator envelopes + summary | `evidence/c1/reviews/` |
| Executor side-probe (preserved) | `evidence/c1/executor-stray-test_syntax.py` |
| Telemetry | `telemetry/runs.jsonl`, `telemetry/findings.jsonl` |
| Regression fixture (§6) | `tools/fixtures/ki4-dropped-high/plan-reviewer-1-envelope.json` |
| Pilot fix commit | `quantum-bank` @ `ab139640` |

Invocation, for reproduction:

```
python3 framework/tools/sprint-loop.py \
  --config sprint/config.json \
  --chunks-file sprint/chunks.json \
  --unattended
```

The runner drove the full loop and issued all six model calls itself. This was not a
hand-orchestrated sequence of individual calls.

---

## 8. Scope note — limits of what this run demonstrates

Recorded so the evidence is not read as proving more than it does.

**The plan named implementation, not just behaviour.** `plan.md` specified the `jsonify`
helper, and a review-round finding introduced the `startswith('/api/')` discriminator.
Both are *how*, not *what*. **No claim of independent implementation may be drawn from
this run** — the executor implemented a solution it had largely been handed. The
boundary is that a plan states what must be true, not how to achieve it. This is the
third recorded instance; it is filed against the planning stage, not the executor, with
a lint rule proposed to flag implementation-prescriptive language in behavioural
criteria. The executor did what it was told. The plan told it too much.

**The run did not complete unattended.** After validation passed, the runner crashed on
a framework-side bookkeeping commit — a repository-topology issue where the evidence
directory sat outside the framework clone, so nothing was staged and the commit failed
empty. The substantive loop was unaffected and the pilot fix was already committed, but
the run was finalised by hand. Both this and the §6 gate defect have since been fixed
and merged.

**One telemetry row is sourced from the envelope, not the ledger.** The executor's usage
row had not flushed to `telemetry/runs.jsonl` when the crash occurred; the figures in §4
are read from `evidence/c1/c1-ex-envelope.json`. The numbers are real; their provenance
differs from the other five rows and is stated rather than smoothed over.

**Single chunk.** `chunks.json` defines one chunk, so this run does not exercise
multi-chunk boundary enforcement. One pilot commit, no framework audit commit.

**Executor seat attribution rests on the invocation.** The executor's raw envelope does
not echo a model field, so its seat is corroborated by the invocation flag and the
commit body's `Model: glm-5.2 (providerLock: zhipu)` line rather than an envelope
self-report. Every other seat's family is corroborated by its telemetry row. No silent
model substitution was observed.
