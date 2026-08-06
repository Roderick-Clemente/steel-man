# PRD — Adversarial Sprint for Factory

*A Factory-native workflow for independent planning, test design, execution, and validation, built on the GROK → CHUNK → EXECUTE sprint method.*

**Owner:** Roderick Clemente
**Date:** 2026-08-02
**Status:** Draft — ready for Phase 0 feasibility spike
**Primary artifact:** Factory plugin + reference Mission configuration
**Pilot repository:** `~/Work/QuantumBank`
**Baseline instrument:** Manual two-CLI harness (Phase 0.5) — the §13 comparison arm and Act 1 of the demo

*Revision note: §§4, 5.3, 5.6, 8, 9, 11, 13, 15, 16 revised 2026-08-02 following a structured cross-family review by Factory Droid. Its findings on H3 measurability, single-blind labelling, v1 surface area, the post-GREEN test-lock gap, and the implicit Probe 5 contingency were accepted; the proposed `max_review_rounds` change was rejected with reason recorded in §5.3, and the proposed consolidation of Droid definitions was rejected in §8 as collapsing the invariants it would have packaged away.*

---

## 1. Executive Summary

Rod currently runs an effective but manual loop: one model plans, a model from another family attacks the plan, both examine the test strategy, a cheap agent implements small chunks, and an independent agent validates each result. The quality comes less from any single prompt than from separating roles, limiting what each role can see and change, and forcing claims of completion through executable evidence.

**Adversarial Sprint** packages that method for Factory. It does not replace Missions, Spec Mode, custom Droids, hooks, or CI. It composes those primitives around the missing workflow:

1. independent cross-family plan review;
2. a structured queue of material disagreements;
3. tests authored separately from implementation;
4. machine-verifiable RED → GREEN evidence; and
5. risk-based human gates.

The first build is a Factory plugin demonstrated on `QuantumBank`. The demo must show both the mechanism and its limits: different model families are a useful independence control, not proof of correctness; tests are executable evidence, not an infallible referee; and agreement between reviewers is not a guarantee.

---

## 2. Problem

Single-agent coding workflows fail in predictable ways:

| Failure | Why it happens | Required countermeasure |
|---|---|---|
| Confidently wrong plans | The author also grades the plan | Independent reviewer with a different model family |
| Tests encode the implementation bug | The same agent writes tests and code | Test designer is separate from the executor |
| Self-review theater | The reviewer inherits the author's reasoning and framing | Fresh validator context; no executor transcript |
| Fake RED evidence | Syntax, import, fixture, or environment failure is called “RED” | Verify the intended behavioral assertion ran and failed |
| Rubber-stamp validation | Review is advisory or has no blocking contract | Validator rejection blocks advancement |
| Token and credit waste | Frontier models perform mechanical execution | Pin role-appropriate models and measure actual spend |
| Lost decisions | Findings, dispositions, commands, and outputs live only in chat | Versioned run artifacts with model and evidence metadata |
| Correlated blind spots | Repeated passes reuse the same priors and framing | Cross-family review plus independently authored checks |

The most important product problem is not “use two models.” It is **making independence and evidence structural properties of the run instead of prompt suggestions**.

---

## 3. Goal, User, and Non-goals

### Goal

Build a reusable Factory plugin that can take an approved engineering objective through planning, adversarial review, test design, chunked execution, independent validation, and a human-reviewable PR with a complete audit trail.

### Primary user

An engineer or technical lead delegating a bounded change to agents while retaining judgment at ambiguity, risk, and course-change points.

### v1 non-goals

- Rebuilding Factory Missions, Spec Mode, model selection, hooks, Droid Shield, or CI.
- Proving that adversarial review works for every model, repository, or task class.
- Automatic adaptation to every stack. `QuantumBank` is the single v1 adapter.
- A general-purpose repo-ingestion engine. Auto-detecting test and CI conventions is a later slice.
- Deployment, CD, auto-merge, or autonomous production changes.
- Multi-repository or cross-service changes.
- A custom UI. Factory output plus files on disk are the interface.
- Requiring Harness MCP integration for the first end-to-end run. Local validation is the v1 gate; CI handoff is a follow-on.
- The portable two-CLI implementation. v1 is Factory-native.

---

## 4. Hypotheses and Invariants

The hypotheses must be measured; the invariants must be enforced.

### Product hypotheses

**H1 — Independent review finds material, non-overlapping issues.** A reviewer from a different model family will surface accepted correctness, scope, or test-strategy findings that the planner misses.

**H2 — Evidence gates reduce false completion.** Separating test design from implementation and validating RED → GREEN mechanically will catch false or weak completion claims that self-reporting misses.

**H3 — Role-tiered models reduce cost without reducing task success.** Frontier planning/review plus cheaper execution will cost less than an all-frontier run while preserving hidden acceptance-test results.

**H3 is conditional on Probe 7.** If Phase 0 cannot produce per-role credit or token attribution at usable granularity, H3 is **excluded from the §13 evaluation** and v1 makes no cost claim at all. An unmeasured cost claim is worse than a missing one, particularly in a demo — it invites a question that cannot be answered with evidence. Decide this at the Phase 0 gate, not while writing the results.

These are not assumed true because one demo looks good. A single demo illustrates the mechanism; the evaluation design in §13 tests the claims.

### Runtime invariants

1. **Family separation:** planner ≠ plan reviewer family; test designer ≠ executor family; executor ≠ validator family.
2. **Fresh review context:** the validator receives the approved spec, resulting diff, read-only repository state, and test evidence. It never receives the executor's transcript, reasoning, or self-assessment.
3. **Independent test authorship:** the executor may not create or modify locked acceptance tests. A required test change returns to the test-design stage.
4. **Valid RED before GREEN:** behavior-changing work cannot begin until the intended assertion has run and failed for the expected reason.
5. **Immutable evidence:** the RED test content hash must match the GREEN test content hash. Any mutation invalidates the gate and requires review.
6. **Blocking validation:** a rejected chunk cannot be marked complete.
7. **Explicit degradation:** if family identity, context isolation, test locking, or artifact capture cannot be guaranteed, the run stops rather than silently weakening the method.
8. **Human merge:** the system may create a branch, local commits, and a PR; a human approves the merge.

### What “model family” means

Family is declared model provenance, not a marketing label or cost tier: Anthropic/Claude, OpenAI/GPT, Google/Gemini, DeepSeek, and so on. Open-weight derivatives must declare their upstream base family. Unknown provenance is treated as unknown and cannot satisfy a hard separation constraint.

The plugin owns a versioned `model-families.json` map. Every run records resolved model ID, provider, family, role, and whether a fallback occurred. A fallback that violates a role constraint stops the run.

**Provenance is maintained by hand, not detected.** Many hosted providers will not declare an upstream base family, and nothing in the runtime can verify a claim of provenance. So `model-families.json` is a curated file with an owner and a review date, not an inference. Any model absent from the map resolves to `unknown`, and `unknown` cannot satisfy a hard separation constraint — it stops the run rather than being optimistically admitted. This is a known maintenance cost and it is accepted deliberately.

---

## 5. End-to-End Workflow

```text
INTAKE / PREFLIGHT
  ↓
GROK — planner drafts problem analysis, acceptance criteria, risks, test strategy
  ↓
BLIND REVIEW — different-family reviewer emits structured findings
  ↓
RECONCILE ◄──────────────┐
  │                      │ revise, re-review (bounded)
  └─ unresolved risk? ───┘
  ↓
TEST DESIGN — independent behavioral tests and expected RED signatures
  ↓
CHUNK / LOCK — final dependency graph, test hashes, commands, rollback
  ↓
EXECUTE — per chunk: verify RED → implement GREEN → refactor
  ↓
VALIDATE — different-family validator; approved spec + diff + repo + evidence
  │
  ├─ reject → bounded retry → re-plan or human gate
  └─ accept
  ↓
REPORT / PR — audit bundle, comparison metrics, human merge decision
```

### 5.1 Intake and preflight

The input may begin as a short goal, but execution cannot begin from an unreviewed one-line prompt. Preflight produces or verifies:

- source commit and isolated sprint branch/worktree;
- clean handling of any pre-existing user changes;
- baseline build, lint, and test commands plus current results;
- explicit acceptance criteria and out-of-scope boundaries;
- allowed files, tools, credentials, network access, and autonomy level;
- budget, timeout, retry limit, and human-gate policy;
- resolvable model IDs and valid family separation;
- artifact directory writable and excluded from product behavior where appropriate.

If baseline tests already fail or are flaky, the run records that state and either narrows the gate to an approved test subset or stops for human disposition. It never attributes pre-existing failures to the new change.

### 5.2 GROK

The planner creates:

- current state and root cause or opportunity;
- affected public behaviors, systems, dependencies, and likely files;
- assumptions and open questions;
- risk table with severity, probability, impact, mitigation, and review trigger;
- acceptance criteria written as observable outcomes;
- test strategy across unit, integration, contract, and end-to-end boundaries as applicable;
- rollback and recovery strategy.

### 5.3 Single-blind plan review and reconciliation

The first reviewer pass is **single-blind**: the reviewer sees the plan document and repository evidence, but not the planner's private reasoning and not a competing review. This reduces anchoring and performative disagreement.

It is deliberately *not* double-blind, and the distinction matters. The reviewer reads the plan itself, so it inherits the plan's framing, vocabulary, and choice of what to make salient. Calling this "blind review" would encourage exactly the over-trust in independence that the method exists to avoid.

Findings use this schema:

```json
{
  "id": "F-001",
  "severity": "blocker|high|medium|low",
  "category": "semantic|factual|test-gap|scope|operability|style",
  "plan_section": "string",
  "claim": "string",
  "evidence": ["path:line or command/result"],
  "recommended_change": "string",
  "risk_if_ignored": "string",
  "status": "open|accepted|rejected|superseded",
  "disposition_rationale": "string"
}
```

Reconciliation may expose both positions, but agreement is only the absence of a known dispute—not evidence of correctness. A plan converges when:

- no blocker or high-severity finding remains open;
- every factual, semantic, scope, and test-gap finding has a recorded disposition;
- acceptance criteria, rollback, and test strategy are internally consistent; and
- the reviewer returns `APPROVE` against that exact plan hash.

The loop is capped at `max_review_rounds` (default: 2 revisions). If it does not converge, the run pauses with a concise decision packet for a human.

The default stays at 2 for v1. It was challenged during review as too tight for legitimate scope disagreement, which is plausible — but it is a tuning parameter with a human escape hatch already attached, and it is the cheapest value in the document to change. Set it from observed non-convergence rates, not from intuition before the first run.

### 5.4 Test design and valid RED

The planner and reviewer independently audit the test strategy using `review-tests`; their outputs are merged only after both passes complete. A designated test designer then authors the final behavioral tests through public interfaces.

Each required RED record contains:

```json
{
  "behavior": "observable outcome under test",
  "test_id": "path::test_name",
  "test_sha256": "hash of locked test content",
  "command": "exact test command",
  "expected_failure": "assertion and mismatch expected before implementation",
  "exit_code": 1,
  "observed_failure": "captured assertion output",
  "classification": "behavioral-red"
}
```

A valid RED means the test collected, executed the intended path, reached its assertion, and failed because the required behavior is absent or wrong. Syntax errors, import errors, missing fixtures, unavailable services, empty test selection, timeouts, and unrelated assertion failures are **invalid RED**.

Refactors, docs-only changes, test-only cleanup, and fixes with an already-failing test may receive a documented exception. The validator approves the exception before execution.

### 5.5 Chunk and lock

Test findings may change scope and dependencies, so final chunking occurs after test design. Each chunk includes:

- one bounded outcome and observable success criteria;
- dependencies and semantic interfaces, not merely overlapping file paths;
- allowed implementation files and locked test files;
- exact RED, focused GREEN, full-suite, lint, and build commands;
- expected outputs or pass conditions;
- risk level and human-review trigger;
- rollback method;
- retry and escalation behavior;
- standardized result block.

Chunks are sequential by default. Parallel execution requires clean file boundaries **and** no shared schema, configuration, generated artifact, migration order, API contract, or behavioral dependency.

Chunk prompts include enough repository context and public examples to execute safely, but do not prescribe a full implementation. Over-specifying implementation would anchor the executor and make black-box tests more likely to mirror the code.

### 5.6 Execute

The executor receives the approved chunk, repository worktree, and focused commands—not the review debate.

For each behavior-changing chunk:

1. Re-run the locked RED command.
2. Confirm the test hash and expected behavioral failure.
3. Implement only within the allowed scope.
4. Run the focused test to GREEN.
5. Refactor while keeping the focused test green.
6. Run the approved regression commands.
7. Emit the chunk artifact and diff.

A hook blocks writes to locked test files. If the spec or test is wrong, the executor reports `SPEC_OR_TEST_BLOCKED`; it does not “fix” the test.

#### Post-GREEN test changes

The hash lock in invariant #5 covers RED → GREEN. It does not cover what happens after, and REFACTOR is the third beat of the cycle — so a legitimate test cleanup following a passing implementation is not an edge case, it is the first thing a real chunk will hit.

Post-GREEN test changes are a **separate reviewed transition**, not an exception to the lock:

1. The executor never makes them. It reports `TEST_REFACTOR_REQUESTED` with a rationale.
2. The test designer authors the change.
3. The validator approves it and re-runs the **original locked assertion set** against the current implementation. If a previously-locked behavioral assertion no longer holds, the change is a scope change and routes back to GROK.
4. The run records both hashes and the approving role.

There is deliberately no "cosmetic test change" fast path. Cosmetic is a judgment call, and removing the executor's judgment from test content is the entire point of the lock.

### 5.7 Validate and retry

The validator runs in a fresh context with:

- approved chunk spec and hashes;
- base and result commits/diff;
- read-only access to the relevant repository, not only the diff;
- RED/GREEN records and command output;
- no executor transcript or self-assessment.

It verifies observable behavior, scope, regression results, error paths, rollback impact, and test quality. Test review rejects private/internal coupling, weak truthiness, tautologies, conditional assertions, timing sleeps, subject-under-test mocks, and assertions that merely replay implementation details.

Outcomes are `ACCEPT`, `REJECT_IMPLEMENTATION`, `REJECT_TEST`, `REPLAN`, or `HUMAN_DECISION`.

- Implementation rejection returns to a fresh executor attempt, capped at 2.
- Test rejection returns to test design and invalidates downstream locks.
- Scope or architectural invalidation returns to GROK/CHUNK.
- Repeated rejection or ambiguous ownership pauses for a human.

### 5.8 Report and PR

The orchestrator creates local commits on the sprint branch and may open a PR. The final report distinguishes evidence from inference and includes unresolved risks. No auto-merge.

---

## 6. Human Judgment Policy

The `oversight` setting controls review frequency without weakening hard safety gates.

| Setting | Human gates |
|---|---|
| `high` | Plan approval; all semantic/factual/test disagreements; every high-risk chunk; every rejection; final PR |
| `medium` (default) | Plan approval; unresolved high/unknown findings; course-changing chunks; re-plan events; repeated rejection; final PR |
| `low` | Plan approval; blockers/unknown classifications; budget or scope breach; repeated rejection; final PR |

Unknown disagreement classifications fail toward review, not auto-dismissal. Stylistic findings never block by themselves. Hard invariants in §4 apply at every oversight level.

Queued human decisions are batched. Each item explains what changed, why the run paused, the competing positions, evidence, cost of delay, and available actions.

---

## 7. Roles and Model Policy

| Role | Default tier | Required separation | Tool policy |
|---|---|---|---|
| Planner/orchestrator | Frontier | — | Read-only during planning; orchestration tools |
| Plan reviewer | Frontier | ≠ planner family | Read-only |
| Test designer | Frontier or mid | ≠ executor family | Test-file edit + focused test execution |
| Executor | Cheap/fast | — | Approved implementation files + test/build commands |
| Validator | Mid/frontier | ≠ executor family | Read-only repo + test/build execution |

Models are explicitly pinned for the first version. Factory's automatic router may recommend candidates, but it may not choose or fall back across a hard family constraint without a new preflight check.

Cost tier is a default, not dogma. An executor may be escalated after one failed attempt if the chunk exceeds the declared complexity ceiling; the run records the reason, incremental cost, and model change.

---

## 8. Factory-Native Design

Adversarial Sprint fills a workflow gap while reusing Factory's existing surfaces.

| Need | Factory surface | v1 use |
|---|---|---|
| Long-running orchestration and milestone validation | Missions | Execute chunks with worker and validator stages |
| Separate worker and validator models | Mission model settings / `droid exec --mission` flags | Pin model IDs and validate family mapping before launch |
| Fresh role contexts and least-privilege tools | Custom Droids | Plan reviewer, test designer, and validator definitions |
| Reusable TDD and review behavior | Skills | `review-tests`, plan review, reporting |
| Deterministic enforcement | Hooks | Block locked-test edits; run/capture validation commands |
| Shareable packaging | Plugins | Bundle manifest, commands, Droids, skills, schemas, and scripts |
| Repo conventions | `AGENTS.md` | Reuse the pilot repo's commands and rules; do not regenerate in v1 |
| Security guardrails | Droid Shield + autonomy/tool policy | Keep enabled; restrict role tools and run in an isolated worktree |
| Platform telemetry | OpenTelemetry | Correlate sessions, tools, usage, and errors with plugin artifacts |
| Existing CI | Harness pipeline in `QuantumBank` | Optional post-local-validation handoff; not a v1 blocker |

Factory documentation confirms that Missions expose separate worker and validator model settings, custom Droids can pin models and read-only tools in fresh contexts, hooks can deterministically block actions, and plugins can bundle these components. It does **not** establish a declarative “role X must differ from role Y by family” rule. The plugin therefore enforces that relationship itself before execution.

### Plugin shape

```text
adversarial-sprint/
├── .factory-plugin/
│   └── plugin.json
├── commands/
│   └── adversarial-sprint.md
├── droids/
│   ├── plan-reviewer.md
│   ├── test-designer.md
│   └── independent-validator.md
├── skills/
│   └── review-tests/
│       └── SKILL.md
├── schemas/
│   ├── finding.schema.json
│   └── red-green.schema.json
├── scripts/
│   └── verify-red-green.sh
├── templates/
│   └── SPRINT-PLANNING-TEMPLATE.md
└── README.md
```

Mission configuration and repo-local hooks may live outside the plugin if Factory's plugin lifecycle cannot install them safely. Phase 0 determines the supported boundary rather than assuming it.

**The v1 surface was cut deliberately.** An earlier draft shipped three skills, three schemas, and two scripts for a two-to-four chunk pilot. `sprint-report` and `adversarial-plan-review` start as prompts inside the command and graduate to skills only when reuse is demonstrated; `run.schema.json` waits until the state machine has stabilised; `preflight.sh` starts inline.

**The three Droid definitions stay.** They were also proposed for consolidation into "prompt variations," and that would be a mistake: the roles carry different tool policies (plan reviewer read-only, test designer with test-file write, validator read-only plus execution) and different hard family constraints. Collapsing them collapses the invariants they exist to enforce. Cut packaging, never role separation.

**Probe 5 contingency.** If Missions cannot route a validator rejection back to retry or re-plan, Phase 3 is redesigned around a command-orchestrated state machine with Factory as the execution substrate. **That redesign happens before any Phase 2 work begins**, not mid-Phase 3 — which is why Probe 5 runs first in Phase 0.

---

## 9. Run Artifacts and State

Every run writes to `.factory/adversarial-sprints/<run-id>/` or another configured artifact path:

```text
run.json                   # state, source commit, budgets, role/model map
goal.md                    # approved objective and boundaries
plan-v1.md ... plan-vN.md  # hashed plan history
findings.jsonl             # findings and dispositions
tests.json                 # locked test IDs, hashes, expected RED signatures
chunks/                    # independently executable chunk specs
evidence/                  # commands, exit codes, stdout/stderr, timestamps
validation/                # per-chunk verdicts and reasons
RESULTS.md                 # human-readable rollup and retrospective
```

`run.json` is the resumable state machine. A resumed run rechecks source commit, working-tree state, plan/test hashes, resolved model assignments, and completed gates before continuing. Stale or mismatched state pauses rather than replaying mutations.

Secrets and raw chain-of-thought are never written to artifacts. Command output is filtered for secrets before persistence.

### Auditability is asymmetric — design for it

The artifact classes are not equally verifiable, and treating them as if they were will misplace the engineering effort:

| Artifact | Verifiability | Implication |
|---|---|---|
| RED/GREEN records | **Machine-verifiable.** Hash, exit code, captured assertion output | Automate fully. A human should never need to adjudicate one |
| Validation verdicts | Semi-verifiable. The verdict is a judgment; the commands and results behind it are not | Record the evidence, not just the verdict |
| Finding dispositions | **Not machine-verifiable.** "Accepted" or "rejected" is irreducibly a judgment call | The recording burden is human. Keep the schema light or dispositions will be skipped, and a skipped ledger is worse than none |

Put the automation where the evidence is mechanical, and put the ergonomics where the judgment is.

---

## 10. Pilot: `QuantumBank`

`QuantumBank` is a credible pilot because it is a real, tested Python application rather than a greenfield toy:

- Python 3.10 / Flask with pytest, Ruff, and Black configuration;
- public, banking, API, and model test markers;
- Harness pipeline assets under `.harness/`;
- Split feature-flag integration;
- Semgrep history and an existing RED → GREEN security-gate drill;
- prior chunked delivery history; and
- an existing `review-tests` skill with a repository adapter.

The v1 demo change should be behaviorally meaningful but bounded to one service and completable in 2–4 chunks. It should include at least one error or boundary path, not only a happy-path UI change. The exact goal is approved after Phase 0 baseline checks.

---

## 11. Delivery Plan

### Phase 0 — Feasibility spike (build gate)

Answer with working probes, not product assumptions:

- Can the installed Factory version pin planner/reviewer/worker/validator models as required?
- Can the plugin resolve effective model IDs and abort before a family-violating fallback?
- Do custom Droids provide the required fresh context and tool restrictions?
- Can hooks block edits to locked tests and persist command evidence reliably?
- Can Mission rejection route to retry/re-plan, or must the command wrapper own that loop?
- Which settings, hooks, and Mission artifacts are safely distributable inside a plugin?
- Can usage/credit data be associated with a run at the required granularity?

**Exit:** a minimal plugin scaffold, two cross-family read-only Droids, one blocking hook, a captured run artifact, and a written go/no-go on Factory-native orchestration.

Also required at exit, because Phase 1 will otherwise discover them stale:

- **The actual per-role model-pinning surface, documented** — the concrete Mission settings and `droid exec` flags, not a pointer to the docs. This is Probe 1's real output.
- **A go/no-go on H3** — if Probe 7 cannot attribute usage per role, H3 leaves the §13 evaluation and v1 makes no cost claim.
- **The Probe 5 branch, decided in writing** — Mission-native or command-orchestrated. If command-orchestrated, that redesign lands before Phase 2 starts.

### Phase 0.5 — Manual baseline harness

Build the smallest honest two-CLI harness that runs the method by hand: cross-family invocation, test hash locking, RED/GREEN capture, evidence to disk.

This is not a throwaway and not a second product. It is the **baseline arm §13 already requires**, and it doubles as Act 1 of the demo. It also removes the project's single biggest risk — every other deliverable is gated on Factory capabilities that Phase 0 has not yet confirmed, and this one is not.

**It must not be strawmanned.** The comparison only holds if this is genuinely the best achievable with two CLIs and shell. Deliberately hobbling it to flatter the platform is both dishonest and transparently obvious to an engineering audience. If the manual harness turns out to be nearly as good, that is a finding, and it is one worth having before a demo rather than during one.

**Exit:** one pilot task completed end to end by hand, with captured evidence and a recorded cost, latency, and operator-intervention count to compare against.

### Phase 1 — Test-evidence vertical slice

Port the existing `review-tests` skill, add valid-RED classification and structured findings, then demonstrate test locking and RED → GREEN verification on one controlled `QuantumBank` behavior.

**Exit:** invalid RED cases are rejected; the same hashed test is observed failing for the intended assertion and later passing.

### Phase 2 — Adversarial planning slice

Build blind plan review, structured findings, bounded reconciliation, oversight policy, and human decision packets.

**Exit:** one real plan reaches a hash-bound approval or a correctly escalated non-convergence state.

### Phase 3 — Factory end-to-end

Connect planning, test design, Mission execution, validator blocking, retry/re-plan, artifact rollup, and local PR creation on the selected pilot change.

**Exit:** one complete run plus a replayable demo and baseline comparison.

### Phase 4 — Generalize after evidence

Only after the pilot: repo ingest/adapter generation, Harness feedback ingestion, a second stack, and the portable Claude/Codex CLI runtime.

### Phase 5 — Hardening (settling pass)

A deliberately-low-velocity consolidation phase that parks low-priority items noted during active phases so they do not slow the active-phase work. The "settling pass" language is deliberate: items are *noted* at the moment they arise but held until the framework catches up. The phase promotes, re-classifies, or drops them on the framework's own terms.

Distinct from Phase 4: Phase 4 generalises the framework across multiple stacks; Phase 5 hardens the framework's own invariants. Things in scope:
- cross-family calibration artifacts (where the two reviewers diverge, why, and what `first_seen_in_panel_position` says);
- case-sensitivity alignments between red/green checks;
- regex tightening (any signature broad enough to false-reject);
- ledger provenance promotions (every cited artefact as a committed file, where feasible);
- any reviewer rubric finding that was deferred from earlier phases with `wontfix` or `deferred`.

Things explicitly out of scope: new feature work, new behaviour, any change that creates a dependency on Phase-5 work for downstream feature completion. Phase 5 is the canonical home for "*we found this, we noted it, we did not fix it because fixing now would have slowed today's velocity*".

**Exit:** every `wontfix` / `deferred` finding from prior phases is either promoted (fix lands in main) or re-classified (the framework genuinely does not need it, and the re-classification is recorded in the wiki). The §13 efficacy metrics are computed over the whole 6-phase arc at the end of Phase 5.

---

## 12. v1 Acceptance Criteria

- [ ] Phase 0 proves or disproves every Factory capability on which v1 depends.
- [ ] A run starts from a recorded source commit in an isolated branch/worktree and preserves unrelated user changes.
- [ ] Effective model ID/provider/family is recorded for every role, and invalid separation stops before code execution.
- [ ] The plan cannot advance with an unresolved blocker/high finding or without an exact plan-hash approval.
- [ ] Behavior-changing code cannot begin until a valid behavioral RED is captured.
- [ ] Test content is locked from RED through GREEN; executor test edits are blocked.
- [ ] Every chunk has explicit scope, observable criteria, commands, rollback, and evidence.
- [ ] Validator context excludes the executor transcript but includes read-only repository state sufficient to find integration issues.
- [ ] A validator rejection blocks completion and exercises at least one retry, re-plan, or human-decision path in a controlled drill.
- [ ] The run can resume safely after interruption without duplicating completed mutations.
- [ ] The final report includes findings/dispositions, model assignments, test evidence, retries, elapsed time, and credit/token usage when available.
- [ ] The system creates a human-reviewable PR or local branch/commit bundle and never auto-merges.

---

## 13. Evaluation Design

Product acceptance and thesis validation are separate. The plugin may work even if a hypothesis underperforms.

### Comparison

Run at least three bounded pilot tasks from identical repository snapshots:

1. single frontier model, self-planned and self-reviewed;
2. all-frontier separated roles; and
3. role-tiered adversarial workflow.

Use the same goals, acceptance criteria, tool permissions, maximum elapsed time, and hidden tests. Counterbalance task/order where possible. Do not tell executors the hidden tests.

### Metrics

| Metric | Why it matters |
|---|---|
| Hidden acceptance-test pass rate | Primary external correctness measure — see note below |
| Human-confirmed material findings unique to each reviewer | Tests independent-review value without rewarding noise |
| Finding precision (`accepted material findings / total findings`) | Penalizes nitpicking and disagreement theater |
| Invalid RED attempts caught | Measures evidence-gate value |
| Validator rejections and escaped defects | Measures gate effectiveness |
| Credits/tokens, wall time, and model escalations | Measures cost and latency trade-offs |
| Human decisions and decision time | Measures oversight burden |

Targets for the pilot:

- no decrease in hidden acceptance-test pass rate versus the all-frontier separated-role run;
- at least 25% lower credit/token cost than the all-frontier run, reported as a goal rather than guaranteed outcome;
- zero accepted invalid-RED records;
- zero silent family-constraint or validator-gate bypasses; and
- qualitative reviewer findings are counted only after human confirmation as material.

“TDD preflight finds at least one gap” and “models disagree at least once” are **not** success gates; both would incentivize manufactured findings. A clean null result is valid data.

### What hidden tests actually buy

Not insulation from human bias — humans author the locked tests and the hidden tests, so the same blind spots ride along in both. Claiming otherwise would overstate the design.

What they buy is **Goodhart protection**. The executor can see the locked tests, so it can satisfy their letter without the behavior generalising: special-casing the asserted input, implementing to the example rather than the rule. Hidden tests are the held-out set that detects exactly that gap. They measure whether the behavior was built or the test was beaten.

This is why hidden tests stay out of every agent's context, including the validator's — a validator that can see them can coach toward them.

---

## 14. Risks

| Risk | Sev | Mitigation / falsification |
|---|---:|---|
| Family separation is unavailable or changes during fallback | H | Preflight and per-stage checks; stop on unknown or violating resolution |
| Cross-family review produces different noise, not better findings | H | Blind passes; evidence-required findings; human-confirmed precision metric |
| Tests are wrong or encode implementation | H | Separate test designer; black-box review; public boundaries; hidden tests |
| RED fails for infrastructure rather than behavior | H | Required assertion signature and explicit invalid-RED classes |
| Validator lacks context to catch integration failures | H | Read-only repo access plus diff/spec; exclude transcript, not codebase reality |
| Validator is anchored by executor-authored tests | H | Independent locked tests and hidden evaluation tests |
| Disagreement classifier hides a material issue | H | Unknown/factual/semantic/test-gap findings fail toward review |
| Review or rejection loop never converges | M | Bounded rounds/retries, then human decision packet |
| Cheap executor cannot complete a chunk | M | Complexity ceiling; one logged tier escalation; re-chunk if repeated |
| Parallel chunks conflict semantically without touching the same file | H | Dependency check includes contracts, schemas, config, migrations, and generated artifacts |
| Baseline tests are flaky or already failing | M | Capture baseline, approved subset or stop; never relabel failures |
| Prompt injection or malicious repo instructions alter policy | H | Least-privilege tools, isolated worktree, Droid Shield, immutable system constraints |
| Hooks execute unsafe code with ambient credentials | H | Review scripts, minimal credentials, isolated environment, no unsafe permission bypass |
| Retry loops erase cost savings | M | Per-role budgets, hard retry caps, measured escalations |
| Audit artifacts leak secrets or private reasoning | H | Secret filtering; store evidence and dispositions, never chain-of-thought |
| Demo proves mechanics but overstates generality | M | Label one run a demo; use the controlled multi-task evaluation for claims |

---

## 15. Demo Narrative

Three acts. Each one earns the next.

### Act 1 — By hand. It works, and that's the problem.

Run the method with the manual harness: two CLIs, shell glue, hash locking, evidence capture. It genuinely works — that is the point, and the reason the baseline must not be strawmanned.

Then show the cost of it working:

- **You are the orchestrator.** Every handoff is a human decision, so the process runs at the speed of your attention.
- **The laptop stays open.** Close it and the run dies.
- **Nothing is enforced.** Family separation, test locking, and validator independence are conventions the operator maintains. A tired operator silently degrades every one of them.
- **No attribution.** Nobody can say what the run cost, or which role spent it.
- **Nothing to show a CISO.** Evidence lives in scrollback.

An audience of engineers recognises this immediately, because it is what their teams are doing right now.

### Act 2 — Push a button, go enjoy life.

The same sprint as a Mission. Pinned models per role, hooks enforcing the locks, Droid Computer holding the run. Kick it off, close the laptop, come back to a completed sprint with an audit bundle.

Then the beat that separates this from every "autonomous agent" demo: **it comes back to you only when your judgment is actually required.** Not a stream of approval prompts — batched decision packets at the points that matter (§6): an unresolved semantic disagreement, a course-changing chunk, a repeated rejection. Each one arrives with what changed, why the run paused, the competing positions, the evidence, and the cost of delay.

Autonomy that never asks is reckless. Autonomy that asks constantly is just slower manual work. The product is autonomy that knows the difference — and the `oversight` setting lets a buyer dial exactly where that line sits for their risk tolerance.

The delta from Act 1 is the demo. Not "AI wrote code" — *the orchestration stopped being your job, and the guarantees stopped being your discipline.*

### Act 3 — Now make it safe for a bank.

Autonomy is the easy half; every vendor demos that. The reason a regulated buyer signs is the layer on top:

- **Model rules and per-user overrides** — which models touch which work, enforced rather than requested
- **Droid Shield** on the validation path
- **Deployment flexibility** — SaaS, hybrid, on-prem for buyers who cannot send code out
- **OpenTelemetry traces** — the run as auditable evidence, exportable into existing security tooling

"Push a button and go enjoy life" is exactly what an enterprise buyer distrusts. Pairing it with this act is what converts it from a risk into a sale: *go enjoy your life, and here is why your CISO is fine with that.*

> **Build Act 3 only on capabilities Phase 0 verified.** Probes 1–4 cover model pinning, fallback safety, context isolation, and deterministic hook blocking — demo those. Air-gapped deployment and the full software-factory outer loop are known to be immature; referencing them as roadmap is fine, staging a demo beat on them is not.

### Close — honest, and stronger for it

Agreement is not correctness. Tests are executable evidence, not truth. Different model families are an independence control, not proof. What the platform buys is a governed process that makes assumptions, disagreements, and evidence **visible** — and visible is the thing an enterprise can actually act on.

This demonstrates the platform thesis without claiming to have rebuilt the platform.

---

## 16. Open Decisions

- Exact `QuantumBank` pilot behavior after Phase 0 reconnaissance.
- Default model assignments and the initial `model-families.json` source of truth.
- Whether Mission validation can express all retry/re-plan transitions or a command-level state machine is required.
- Whether the test designer is the plan-reviewer model or a third independent model in v1.
- Artifact path and retention policy for repos that should not commit run evidence.
- Whether `oversight` is the right public name; “judgment density” is memorable but less immediately clear.
- Product name. “Adversarial Sprint” is descriptive but may overemphasize conflict over independence.
- **What “replayable” means for the demo (§12).** Models are stochastic, so same input → same tokens is not achievable and should not be implied. Same input → same *verdict* is a defensible claim, and even that needs measuring across repeat runs before it is asserted in front of an audience. Pin the wording before the demo narrative is final, because a reviewer will ask.
- Whether the manual baseline harness (Phase 0.5) ships publicly alongside the plugin, or stays an internal comparison instrument.

---

## References

### Local evidence

- Sprint template: `~/Work/dakota-software/docs/db-migration/SPRINT-PLANNING-TEMPLATE.md`
- Gold reference sprint: `~/Work/dakota-software/docs/db-migration/sprints/2026-07-03-track1-working-data/`
- Existing plan-review prompt: `~/Work/dakota-software/docs/archive/db-migration/sprints/2026-07-03-track1-working-data/s6-plan-review-prompt-codex.md`
- Existing test-review skill: `~/Work/QuantumBank/.claude/skills/review-tests/SKILL.md`
- Factory product and strategy research: private notes (not in this repo)

### Factory documentation (verified 2026-08-02)

- Plugins: <https://docs.factory.ai/cli/configuration/plugins>
- Building plugins: <https://docs.factory.ai/guides/building/building-plugins>
- Custom Droids: <https://docs.factory.ai/cli/configuration/custom-droids>
- Skills: <https://docs.factory.ai/cli/configuration/skills>
- Hooks: <https://docs.factory.ai/cli/configuration/hooks-guide>
- Mixed models: <https://docs.factory.ai/cli/configuration/mixed-models>
- Power-user guide (Missions and mission model settings): <https://docs.factory.ai/cli/user-guides/become-a-power-user>
- Droid Exec: <https://docs.factory.ai/cli/droid-exec/overview>
- Enterprise controls and OpenTelemetry: <https://docs.factory.ai/enterprise>
