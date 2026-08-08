# Adversarial Sprint

**A framework for getting better code out of coding agents, because quality comes from structural independence rather than a smarter model.**

Two or more agents from **different model families** plan the work, attack each other's plan, cut it into chunks, and independently validate every chunk before the next one starts. No agent grades its own work, and no agent reviewing a piece of work is allowed to see the reasoning of the agent that produced it.

That is the primary claim and it is a claim about correctness. The measure for it is the hidden acceptance-test pass rate, which `PRD.md` §13 names as the primary external correctness measure. Spend is a separate question, handled further down as an allocatable lever rather than a second headline promise.

## Why you should care

Coding agents fail quietly. They report success for work they did not do, and the report looks exactly like a report of work they did.

That is not a hypothesis here. Four separate probes against a shipping product at a pinned version hit the same shape:

- a mission that performs no work and exits 0 ([Probe 1](../probes/probe-1-model-pinning.md))
- a hook registered in the documented location that is never loaded ([Probe 4](../probes/probe-4-hook-blocking.md))
- a model silently downgraded from maximum reasoning to none ([Probe 2](../probes/probe-2-fallback-safety.md))
- a run whose every tool call was denied, still exiting 0 with a plausible-looking answer ([Probe 2](../probes/probe-2-fallback-safety.md))

Each one is reproducible from a command recorded in this repository. The pattern is written up in [Silent green](../findings/silent-green.md).

If you run agents unattended, that is the real exposure. Not a bad diff you can see in review, but a green check you believe. Adversarial Sprint starts from the assumption that **a run's own account of itself is not evidence**, and builds the loop so that something other than the executor decides whether the work is done.

## How it works

One frontier model plans. A model from a different family attacks that plan. The disagreements are reconciled, the work is cut into chunks, and then each chunk runs a small test-first cycle whose result is checked by a model that did not write it.

### The method, run by hand today

```mermaid
graph TD
    P["Plan<br/>frontier, family A"] --> R["Attack the plan<br/>frontier, family B"]
    R -->|disagreements| C["Reconcile<br/>bounded; a human breaks ties"]
    C --> K["Cut into chunks"]
    K --> T["Write the test<br/>author is not the executor"]
    T --> RED{"Valid RED?<br/>fails for the expected reason"}
    RED -->|no| T
    RED -->|yes| X["Execute the chunk<br/>cheap tier"]
    X --> F["Refactor<br/>tests stay green"]
    F --> V["Validate<br/>family is not the executor's<br/>sees spec, diff and evidence, not reasoning"]
    V -->|reject| X
    V -->|accept| N{"More chunks?"}
    N -->|yes| T
    N -->|no| D["Done"]
```

This is the GROK, CHUNK and EXECUTE method in `templates/SPRINT-PLANNING-TEMPLATE.md`, the canonical copy this project packages. It has been run by hand for months and it works. Chunking is a defined stage there rather than a box invented for this page, and it carries a dependency graph in which independent chunks may run in parallel while dependent ones stay sequential. The diagram keeps one chunk in view for legibility; the full graph is in [Workflow](../method/workflow.md).

Nothing on this diagram is speculative. Every separation in it is something a person currently holds in their head and remembers to do.

Four properties carry the method, and all four are meant to be enforced rather than suggested:

1. **Family separation.** The plan reviewer is not the planner's family; the validator is not the executor's family. Two passes from one model family are one opinion twice.
2. **Fresh review context.** The validator sees the approved spec, the diff, read-only repository state, and test evidence. It never sees the executor's reasoning.
3. **Independent test authorship.** The executor cannot write or modify the tests that judge it. Locked by content hash, enforced by a hook.
4. **Valid RED before GREEN.** Behavior-changing work cannot start until the intended assertion has run and failed *for the expected reason*. A syntax error is not a RED.

Validation happens **per chunk, not at the end**. A rejected chunk is a cheap retry against a small diff, and the next chunk does not start on top of unvalidated work. The full set of eight runtime invariants is in [Invariants](../method/invariants.md), and the stage-by-stage walkthrough is in [Workflow](../method/workflow.md).

### The enforcement, and what the phases build

The same loop. What changes is that each handoff becomes a contract that something checks, rather than a discipline someone maintains.

```mermaid
graph TD
    P["Plan<br/>frontier, family A"] --> R["Attack the plan<br/>frontier, family B"]
    R -->|disagreements| C["Reconcile<br/>bounded; a human breaks ties"]
    C --> K["Cut into chunks"]
    K --> T["Write the test<br/>author is not the executor"]
    T --> RED{"Valid RED?<br/>fails for the expected reason"}
    RED -->|no| T
    RED -->|yes| X["Execute the chunk<br/>cheap tier"]
    X --> F["Refactor<br/>tests stay green"]
    F --> V["Validate<br/>family is not the executor's<br/>sees spec, diff and evidence, not reasoning"]
    V -->|reject| X
    V -->|accept| N{"More chunks?"}
    N -->|yes| T
    N -->|no| D["Done"]

    GUARD["Reference guard<br/>one PreToolUse hook, ~30 lines"]
    GUARD -.->|"family separation"| R
    GUARD -.->|"independent test authorship"| X
    GUARD -.->|"fresh review context"| V

    OURS["Our code, outside the guard<br/>valid-RED classifier<br/>per-role pinned invocation"]
    OURS -.-> RED

    style GUARD fill:#eaeaff,stroke:#445588,stroke-width:2px
    style OURS fill:#eaffea,stroke:#446644,stroke-width:2px
```

One guard, three policies. That shape is the finding rather than a simplification of it: Phase 0's most useful constructive result is that independent test authorship, fresh review context and family separation collapse into a single `PreToolUse` hook of roughly thirty lines, differing only in what it inspects and what it refuses ([The reference guard](../findings/reference-guard.md)).

Two things sit outside the guard. One is the valid-RED classification. The other is per-role pinned invocation, and the diagram under-draws it deliberately: **pinning applies at every role invocation in the loop, not only at the RED gate.** Each role is a separate `droid exec` with its model named explicitly, so the property attaches to all five seats; the dotted line lands on one node purely to keep the picture readable.

**Where each contract actually stands.** These are not uniformly unbuilt, and the differences matter:

| Contract | State |
|---|---|
| Family separation | Platform primitive **verified** in Phase 0. Explicit `--model` pins resolve exactly and an invalid ID fails closed at exit 1 ([Probe 2](../probes/probe-2-fallback-safety.md)). |
| Locked tests | Platform primitive **verified**, conditionally. A hook blocks the executor's own edit and the run continues on the refusal, provided it is registered correctly and fails closed ([Probe 4](../probes/probe-4-hook-blocking.md)). |
| Fresh review context | **Enforceable, not default, and holed.** The executor's session is readable off disk with `Grep` alone, and independently via `droid search`. Isolation holds only if the guard blocks those paths ([Probe 3](../probes/probe-3-context-isolation.md)). |
| Valid RED, and the guard itself | **Our code, not yet written.** The platform will not classify a RED or detect its own silent degradation; that detection is ours to build. |

So the enforcement layer is part verified primitive and part unwritten code, and one of its contracts has a known hole with a known fix. What does not exist in any form is a measured result: no arm of the `PRD.md` §13 comparison has been run, under any configuration.

## Where the tokens go

**The claim in this section is not that the method costs less.** It is that spend stops being a single dial on one model and becomes something the design places deliberately.

The method spends *more* than a single-model run on planning, adversarial plan review, test design, and per-chunk validation. That is intentional. Those are the points where being wrong is expensive, because an error in the plan propagates into every chunk built on top of it, and an error the validator misses ships.

That front-loaded spend is what makes the cheapest seat safe. By the time any implementation code is written, the work has been planned, attacked by a model from a different family, cut into a bounded chunk with a declared complexity ceiling, and given a test that has already failed for the expected reason. The executor is not being asked to decide what to do. It fills a specified hole with a test watching. That is why the cheapest model in the loop is the one holding the only seat with implementation write access.

This argument is not back-fitted to justify the design. The canonical template states it as a standing principle, in those words: **"Low-token execution: plan once, execute in small chunks with minimal context"** (`templates/SPRINT-PLANNING-TEMPLATE.md`). The allocation came first and the method was built around it, well before this page existed to argue for it.

| Role | Default tier | Write access |
|---|---|---|
| Planner / orchestrator | Frontier | Read-only while planning |
| Plan reviewer | Frontier | Read-only |
| Test designer | Frontier or mid | Test files only |
| **Executor** | **Cheap / fast** | **Implementation files** |
| Validator | Mid / frontier | Read-only, plus test execution |

The escalation rule follows the same reasoning. An executor may be escalated one tier after a single failed attempt, but repeated escalation is treated as evidence that the *chunking* was wrong, so the chunk is re-cut rather than handed to a larger model ([Roles and models](../method/roles-and-models.md)). A bigger model is not the first lever reached for when something fails.

### The harness as a tuning instrument

Every seat in the loop takes a model family and a cost tier as parameters. Nothing in the design pins a particular assignment, so the same harness can run one task repeatedly across different seat configurations and read off what each configuration produced on both axes independently: correctness, via the hidden acceptance-test pass rate, and spend, attributed per role.

Framed that way, the three comparison runs in `PRD.md` §13 (a single frontier model that plans and reviews its own work; all-frontier separated roles; the role-tiered adversarial workflow) stop being a one-off A/B/C and become three sampled points on a surface the rig could sample more densely.

**None of this has been run.** There is no tradeoff curve, no sampled surface, and no result of any kind to report. A quality-versus-spend plot is an *output the instrument is designed to produce*, not a claim this project is making, and the two axes are deliberately kept separate rather than collapsed into a ratio: a ratio that improves tells you nothing about which of the two terms moved. This subsection describes what becomes measurable next, on the same terms as everything else on this page.

**What is claimed, and what is not.** The target in `PRD.md` §13 is at least 25% lower credit and token cost than an all-frontier run at no loss in hidden acceptance-test pass rate, and the PRD states it as a goal rather than a guaranteed outcome. That number has **not been measured**, because the pilot that would measure it has not been run. Nor has any other arm of the §13 comparison: no pilot task has been run end to end under any of the three configurations, so there is no baseline to compare against and no figure to quote in either direction.

What Phase 0 did establish is that it will be measurable. Per-role cost attribution was assumed to depend on Missions, which turned out to be broken; instead, `usage.factory_credits` is reported per run, so invoking once per role attributes cost cleanly (`phase-0/GO-NO-GO.md`). `PRD.md` §4 commits to making no cost claim at all if attribution proves unavailable, on the grounds that an unmeasured cost claim invites a question that cannot be answered. That commitment still stands, and it is why this section describes a mechanism and an instrument instead of a headline figure.

## Why this is not already solved

The primitives exist. Phase 0 confirmed that tool restrictions on a custom agent are genuinely enforced rather than merely requested ([Probe 3](../probes/probe-3-context-isolation.md)), that hooks can deterministically block a tool call ([Probe 4](../probes/probe-4-hook-blocking.md)), that an agent, a skill and a hook ship as a single install ([Probe 6](../probes/probe-6-plugin-boundary.md)), and that a model family gate can be enforced at invocation time ([Probe 2](../probes/probe-2-fallback-safety.md)).

What does not exist is the layer above them: anything that **sequences the roles and constrains what crosses the boundary between them**. The obvious candidate was Missions, and `droid exec --mission` performs no work while reporting success, which removed that path and forced the design to be command-orchestrated. The go/no-go puts it plainly: the wrapper owns the state machine, so this is our code, not a platform feature.

So the gap this project fills is not intelligence and not tooling. It is the **handoff** — a formal, enforced contract for what one agent hands the next, and what the next one is allowed to see. Today that handoff is a convention someone remembers to follow. The working version of it is already running by hand in this repository, where commits are the only baton between agents (`tools/wake-loop.md`).

*Scope note: Probe 1 tested `droid exec --mission`, the scriptable path. The interactive Missions flow was not tested, and no claim is made about it.*

## Roadmap

The north star is a **replayable demo of the method on one bounded pilot change**, with the manual harness at Phase 0.5 as the honest comparison arm. **Phases 0–4 are the MVP**, the point at which the core loop runs end-to-end, the foundation is hardened, and the §13 comparison produces a measured result. Everything past 4 is earned by using that MVP, not required to have proven it.

| Phase | What it delivers | Status |
|---|---|---|
| **0 — Feasibility spike** | Eight probes and a go/no-go on platform capabilities | **Done, GO** |
| **0.5 — Manual baseline harness** | The smallest honest two-CLI harness; the §13 comparison arm and Act 1 of the demo | **Done** — `tools/PHASE-0.5-CLOSE.md`, all exit criteria checked |
| **1 — Test-evidence slice** | Valid-RED classification, test locking, RED → GREEN on the pilot | **Partial** — lock + GREEN works; `valid-red.py` never run, invalid-RED never demonstrated |
| **2 — Adversarial planning slice** | Blind plan review, bounded reconciliation, human decision packets | **Complete (clean null)** — hash-bound APPROVE, zero blocking findings (valid per §13) |
| **3 — Factory end-to-end** | The full loop on one pilot change, plus a replayable demo and the baseline comparison | **Core done, exits missed** — 3 chunks built, all cross-family ACCEPT, 99 tests passing; no demo, no baseline comparison, no local PR |
| **3.1 — Degraded loop spike** | Same-family test-author + executor to measure bias | **Complete** — deterministic gate caught bias every time; panel split ([story](phase-3.1-degraded-spike.md)) |
| **3.2 — Evidence provider** | Local EvidenceBundle, zero-CI default, orchestration script | **Complete (milestone)** — 55.2% token saving (directional); orchestration partially working ([story](phase-3.2-evidence-provider.md)) |
| **4 — Hardening + roadmap review** | Orchestration stabilization, H-CI/H3 experiments, demo packaging, new operating rules | **Current** — roadmap review done (v3), three parallel tracks defined ([story](roadmap-review.md)) |
| **5 — Generalize** | A second stack and a portable Claude/Codex runtime | Not started (post-MVP) |
| **6 — Hardening (settling pass)** | Consolidation of parked low-priority items; hardens the loop's own invariants at no new behaviour | Not started (post-MVP) |
| **7 — Human-in-the-loop compression** | Review panel, hats-across-families, escalation-on-disagreement knob, calibration telemetry, to compress the operator seat | Not started ([post-MVP, pain-point-driven](../human-in-the-loop.md)) |

Each phase carries written exit criteria in `PRD.md` §11. A phase is finished when those are met, not when it looks finished, which is the same standard the probe records hold themselves to. The §13 efficacy metrics are computed over the measured **0–6 arc**; [Phase 7](../human-in-the-loop.md) is deliberately outside it, because it targets the operator's cost rather than the loop's correctness or spend.

Phase 0.5 is the one most easily misread as optional. It is the baseline arm the §13 evaluation already requires, and the PRD is explicit that it must not be strawmanned: if a two-CLI shell harness turns out to be nearly as good as the plugin, that is a finding worth having before a demo rather than during one.

## Where we are against it

**Phases 0–3.2 have landed work; Phase 4 (hardening + roadmap review) is
current.** Phase 0 is complete (GO, command-orchestrated). Phase 0.5 is
closed with all exit criteria checked. Phase 1 shipped its test-evidence
slice with partial completion (lock + GREEN works, valid-red.py never run).
Phase 2 produced a hash-bound, panel-APPROVED plan — a clean null (zero
blocking findings, valid per §13). Phase 3 built 3 chunks through the full
loop with all cross-family ACCEPT and 99 tests passing, but missed 3 of 4
exit criteria (no demo, no baseline comparison, no local PR). Phase 3.1 ran
the degraded loop spike and found panel-dependent bias detection. Phase 3.2
built the evidence provider with a 55.2% directional token saving and a
partially working orchestration script. Phase 4 is the hardening phase that
arrived ahead of schedule — the roadmap review audited everything, went
through two rounds of cross-family panel review (v1 REJECT → v2
APPROVE-WITH-NITS → v3 final), and produced three parallel execution
tracks plus new operating rules.

What still does not exist under any configuration is the thing the whole
gate is there to produce: a measured §13 result. The H-CI and H3
experiments in Phase 4 Track B are the next steps toward that.

**Phase 0 is complete and the verdict is GO, with one mandatory design change:** build it command-orchestrated rather than Mission-native. See `phase-0/GO-NO-GO.md`, summarised in [Findings](../findings/index.md).

A probe is a **Phase-0-only device**: one feasibility question aimed at the platform, used solely to decide the build gate. Later phases deliver vertical slices measured against exit criteria, not probes. The project is not made of probes, and the eight below are scaffolding for the decision rather than the product.

| Probe | Question | Verdict |
|---|---|---|
| [1](../probes/probe-1-model-pinning.md) | Per-role model pinning | **BLOCKED** — `droid exec --mission` is a no-op that reports success |
| [2](../probes/probe-2-fallback-safety.md) | Fallback safety | **CONDITIONAL PASS** — family gate works; found a silent reasoning downgrade |
| [3](../probes/probe-3-context-isolation.md) | Custom Droid context isolation | **PASS / GAP** — tools genuinely restricted; transcript readable off disk |
| [4](../probes/probe-4-hook-blocking.md) | Deterministic hook blocking | **PASS** (conditional) — overturned an earlier BLOCKED verdict |
| 5 | Rejection routing | Unreached — blocked by Probe 1 |
| [6](../probes/probe-6-plugin-boundary.md) | Plugin distribution boundary | **PASS** — droid, skill and hook ship as one install |
| 7 | Usage attribution | Partially unblocked by Probe 2 |
| [8](../probes/probe-8-self-declared-risk.md) | Self-declared risk as a policy input | **PASS with caveat** — the tier gates on a self-report |

Every verdict is scoped to `droid` **0.186.0** on macOS. A version-less result cannot be rechecked later, so each probe record carries the CLI version, and a CLI upgrade invalidates the go/no-go until the probes are re-run. The primitives were re-checked six patch versions back and held; see [Cross-version validation](../findings/cross-version-validation.md).

## Early evidence for the core bet

The central claim, that a second model from a different family catches what the first one misses, has one early data point rather than a result. A pilot spec was reviewed by two models from different families. They agreed on the accept decision, overlapped on one defect, and each independently raised one the other did not.

It is a single unblinded sample on a specification rather than code, and all three findings were graded as nits by the reviewers themselves. It is written up honestly, including the reading that cuts against the hypothesis, in [First H1 observation](../findings/first-h1-evidence.md).

The design consequence of Phase 0 is [one reference guard](../findings/reference-guard.md) that inspects reality instead of trusting configuration, which follows directly from the platform's inability to fail loudly.

## A note on scope and honesty

The repository makes no claim to be a correctness oracle. Different model families are an independence control, not proof. Tests are executable evidence, not truth. Two reviewers agreeing means no known dispute and nothing more.

The same standard applies to the probe records. Negative results get the same treatment as positive ones, an overturned verdict is kept alongside its correction rather than quietly edited, and unmeasured things are listed as unmeasured. See [Patterns and conventions](../how-to-contribute/patterns-and-conventions.md) for how that standard is applied in practice, and [Open questions](../background/open-questions.md) for what is still unresolved.

## Where to start

| If you want to | Read |
|---|---|
| Understand the method being packaged | [Method](../method/index.md) → [Workflow](../method/workflow.md) |
| Know what the platform can actually enforce | [Findings](../findings/index.md) |
| See the reasoning behind the design | [Background](../background/index.md) |
| Re-run a probe and check a claim yourself | [Getting started](./getting-started.md) |
| See how the pieces fit together | [Architecture](./architecture.md) |
| Look up a term | [Glossary](./glossary.md) |
| Contribute, as a human or an agent | [How to contribute](../how-to-contribute/index.md) |


## The story — building the loop with itself

This framework's primary claim is about correctness, but it also has a
secondary claim that the meta is just as interesting as the meta-tested
code. When the framework is used to build itself, the bugs it surfaces
fall into two flavours: bugs in the code being shipped, and bugs in the
runtime shipping the code. Both land on the same §13 efficacy surface
and both deserve to be tracked.

**Phase 1 is the first six-reviewer-session case study of that loop used
on itself.** Three rounds of two reviewers (`grok-4.5` and
`gemini-3.1-pro-preview`), ~3.4M input tokens across the panel,
~22 findings of severity variant. Round 2 had a REJECT-from-both-panels
stretch where Grok caught a regression the round-1 fix had introduced
(retrospectively adding `python3` to a read-only allowlist had
inadvertently opened an inline-eval bypass) and Gemini caught three
orthogonal hook-layer defects in the same round. Round 3 was a clean
ACCEPT-WITH-NITS confirmatory pass.

The full round-by-round breakdown — including the catch-by-catch
overlap, the per-session tokens, and the calibration divergence
matrix — is in [The meta-narrative](meta-narrative.md).

## Code-quality signals — beyond the bug

The bug count is not the only signal the panel produces. The round-by-round
trace also surfaces five quality dimensions that are measurable on every
slice that goes through the framework:

1. **Placebiticity.** Would the locked test catch a no-op implementation?
   Real Werkzeug behaviour, no SUT mock, real client GET. Phase 1 locked
   test passes six of the seven items in
   [method/sprint-template.md test-quality rubric](../method/sprint-template.md).
2. **Cross-family calibration divergence.** The two reviewers didn't
   catch the same defects — Gemini caught the hook security family,
   Grok caught the rubric compliance family. The overlap is partial
   and the divergence is the §13 efficacy lever.
3. **Spec-compliance coverage per PRD exit criterion.** Findings cite
   `criterion: spec-compliance | phase-0.5-handoff | test-quality`,
   forced by the reviewer rubric. Phase 1 covered all four PRD §11
   exit criteria (a–d).
4. **Time-to-correctness (RED→GREEN path).** Locked test → RED → lock →
   executor → minimal fix → GREEN verified, all in single-digit minutes.
5. **Cost per finding and marginal cost per extra reviewer.** ~155k
   tokens-in per finding on Phase 1; ~250k–500k for the marginal
   second-reviewer cost on small slices.

The full description of each signal and where the data lives
(`telemetry/runs.jsonl`, `telemetry/findings.jsonl`,
`telemetry/aggregate.py`) is in [Code-quality signals](code-quality-signals.md).

## Where this leaves us at Phase 1 close

Phase 1 ships at `9940d40` on `factory/phase-1-test-evidence`, with
ACCEPT-WITH-NITS from cross-family review and a Phase-2/Phase-3 paused
state while the rest of the system catches up. The cross-family panel
is the structural guarantee that keeps the framework honest as it
grows; the build-review-find loop is itself the work being reviewed.

## Phase 2 — the adversarial planning slice

Phase 1 showed the loop reviewing code it wrote. **Phase 2 pushes it one step
earlier: can the panel review a *plan* before any code exists, and reach an
approval bound to that plan's exact bytes?** On one real slice — a read-only
`GET /profile` page for the pilot bank — the answer is yes.

Two single-blind cross-family stages (brief, then plan) each ran `grok-4.5` +
`gemini-3.1-pro-preview`. The brief came back ACCEPT-WITH-NITS / ACCEPT and was
reconciled; the pinned planner (`claude-opus-5`) then drafted a plan hashed to
`sha256:72eccff5…`, and both families **APPROVED it with zero blocking
findings**, satisfying the PRD §11 Phase 2 exit ("one real plan reaches a
hash-bound approval") — now awaiting the human plan-approval gate.

The sharpest result landed *before* the panel: the planner self-corrected three
wrong file anchors in its own prompt and discovered that "just add an `address`
column" was a hidden scope trap (no `ALTER TABLE`, no migration runner, a
count-gated seed), turning a design coin-flip into a clear least-scope call. The
calibration divergence also inverted Phase 1's: on specification and planning
artifacts, Grok was the finder and Gemini the confirmer — the mirror of Phase 1,
where Gemini was the security finder on hook code. That task-conditioned
divergence is exactly the `first_seen_in_panel_position` signal Phase 6 will
accumulate.

The full round-by-round breakdown — verdicts, per-session tokens, the autonomy
findings from running paid reviewers unattended, and the divergence matrix — is
in [The Phase 2 planning slice](phase-2-planning-slice.md).
