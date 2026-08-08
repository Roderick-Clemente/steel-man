# Architecture

Two architectures matter in this repository, and confusing them is the most common way to misread it.

1. **The repository's own structure** — a spec, a method template, and probe evidence. This is what exists today.
2. **The system the spec describes** — the Adversarial Sprint plugin. This does not exist yet; Phase 0 was the gate deciding whether it can.

## Repository structure

```text
adversarial-sprint/
├── README.md                              entry point and one-page pitch
├── AGENTS.md                              conventions for every agent working here
├── PRD.md                                 full spec: problem, invariants, phases, evaluation
├── templates/
│   └── SPRINT-PLANNING-TEMPLATE.md        canonical GROK/CHUNK/EXECUTE method
├── tools/                                 operating discipline, tracked so it travels
│   ├── OPERATING-RULES.md                 multi-agent, multi-machine rules
│   ├── wake-loop.md                       orchestrator/worker async pattern
│   └── pilot-llms-txt-spec.md             spec for the first hand-run pilot
├── phase-0/
│   ├── README.md                          the eight probes and their verdicts
│   ├── GO-NO-GO.md                        Phase 0 decision
│   └── evidence/
│       ├── README.md                      what a probe record must contain
│       ├── probe-1/ … probe-8/            one directory per probe
│       │   ├── README.md                  the finding, with reasoning
│       │   ├── raw/                       captured stdout, exit codes, hook logs
│       │   ├── rig/                       the hook scripts and configs under test
│       │   └── run.sh                     re-runs every measurement
│       └── canary-0.180.0/                the same primitives on an older CLI
└── pilots/
    └── ai-discovery/                      first hand-run pilot, the H1 observation
        ├── README.md                      units, merge commits, what it does not support
        └── validator-outputs/             the reviewers' own text, verbatim where noted
```

There is no build, no dependency manifest, and no test suite in the conventional sense. The executable artifacts are the probe rigs: Python hook scripts and `run.sh` reproduction scripts. See [Getting started](./getting-started.md).

`tools/` is tracked deliberately. Sessions are machine-scoped and `STEER.md` is gitignored, so the git repository is the only channel that reaches a second machine — anything a future agent must know has to be committed or it does not travel. `tools/OPERATING-RULES.md` is the operating discipline that sits on top of `AGENTS.md`.

`pilots/` is separate from `phase-0/` on purpose. Phase 0 evidence answers whether the platform *can* enforce the invariants and is scoped to a CLI version. A pilot is a hand-run of the method against a live target, and it is deliberately **not** filed under `phase-0.5/`, because PRD §11 reserves Phase 0.5 for the manual baseline arm — the same change done a second way for comparison — which has not been run. See [First H1 observation](../findings/first-h1-evidence.md).

### Evidence lives in the repo, not in `.factory/`

PRD §9 nominates `.factory/adversarial-sprints/<run-id>/` as the default artifact path, but `.factory/` is gitignored here as local tool state, so evidence written there would be invisible to git. Phase 0's exit criteria require a *captured* run artifact, and §9 permits "another configured artifact path". `phase-0/evidence/` is that path. The reasoning is recorded in `phase-0/evidence/README.md`.

### One consolidated branch, recorded per probe

Each probe was recorded on its own `factory/<topic>` branch while it was being run, and later probes were chained onto earlier ones so results could accumulate and cite each other. Those branches have since been merged into a single line:

```mermaid
graph LR
    main["main<br/>spec, template, conventions"] --> P1["factory/probe-1-evidence"]
    main --> P3["factory/probe-3-context-isolation"]
    main --> STEER["factory/steer-channel"]
    main --> P4["factory/probe-4-hook-blocking"]
    P4 --> P8["factory/probe-8-self-declared-risk"]
    P8 --> P2["factory/probe-2-fallback-safety"]
    P2 --> P6["factory/probe-6-plugin-boundary"]
    P6 --> GNG["factory/phase-0-go-no-go"]
    P1 -.merged.-> GNG
    P3 -.merged.-> GNG
    STEER -.merged.-> GNG
```

**`factory/phase-0-go-no-go` now carries the complete record**: all six probe evidence directories, the go/no-go, the spec, and this wiki. Every other branch is fully contained in it. They were kept rather than deleted, so the per-commit history of each probe stays readable on the branch that produced it.

Consolidation was done as merges rather than a squash, deliberately. The commit-by-commit baton between agents is itself evidence that the handoff method described in [Development workflow](../how-to-contribute/development-workflow.md) worked, and squashing would have destroyed it.

Nothing has landed on `main` beyond the initial commits, because `AGENTS.md` requires review before merge. So `main` is still the spec and the conventions only, and the Phase 0 branch is where the evidence is.

## The system the spec describes

The plugin composes existing Factory surfaces around a workflow gap. It does not replace Missions, Spec Mode, custom Droids, hooks, or CI.

```mermaid
graph TD
    INTAKE[Intake / preflight] --> GROK[GROK: planner drafts<br/>analysis, criteria, risks, test strategy]
    GROK --> REVIEW[Blind review:<br/>different-family reviewer]
    REVIEW --> RECONCILE{Converged?}
    RECONCILE -->|unresolved risk| GROK
    RECONCILE -->|approved against plan hash| TESTS[Test design:<br/>independent behavioral tests]
    TESTS --> LOCK[Chunk and lock:<br/>dependency graph, test hashes]
    LOCK --> EXEC[Execute per chunk:<br/>verify RED, implement GREEN, refactor]
    EXEC --> VALIDATE[Validate:<br/>different-family validator]
    VALIDATE -->|reject| RETRY{Bounded retry}
    RETRY --> EXEC
    RETRY -->|exhausted| GROK
    VALIDATE -->|accept| REPORT[Report and PR:<br/>audit bundle, human merge]
```

Each stage is detailed in [Workflow](../method/workflow.md); the role and model policy is in [Roles and models](../method/roles-and-models.md).

### Enforcement, not suggestion

The distinguishing claim is that independence and evidence are **structural properties of the run**, not prompt instructions. Phase 0 tested whether the platform can actually deliver that, and the answer shaped the architecture significantly.

```mermaid
graph TD
    subgraph guard["One reference guard (PreToolUse hook)"]
        READ[Read transcript_path<br/>inspect what actually happened]
        FAILCLOSED[Fail closed on any<br/>payload it cannot interpret]
        EMIT[Emit contract on stderr,<br/>exit 2 → agent receives it, run continues]
    end
    READ --> FAILCLOSED --> EMIT
    EMIT --> POL1[Locked-test guard<br/>invariant 3]
    EMIT --> POL2[Isolation guard<br/>invariant 2]
    EMIT --> POL3[Family gate<br/>invariants 1 and 7]
```

One primitive, three policies. This is the central architectural conclusion of Phase 0 and is documented in [The reference guard](../findings/reference-guard.md).

### What changed because of Phase 0

| Spec assumption | Phase 0 result | Architectural consequence |
|---|---|---|
| Missions orchestrate worker and validator stages | `droid exec --mission` performs no work ([Probe 1](../probes/probe-1-model-pinning.md)) | Command-orchestrated state machine instead; the §8 contingency |
| Mission flags pin per-role models | Flags exist but are `--mission`-only | One `droid exec --model <id>` per role ([Probe 2](../probes/probe-2-fallback-safety.md)) |
| Hooks block locked-test edits | True, but only via specific registration channels ([Probe 4](../probes/probe-4-hook-blocking.md)) | Guard must live in `settings.json` or a plugin, match `Execute`, and fail closed |
| Custom Droids give isolated context | True at the agent channel, false at the storage layer ([Probe 3](../probes/probe-3-context-isolation.md)) | Isolation needs an active guard, not just a Droid definition |
| Per-role cost attribution needs Missions | `usage.factory_credits` is per run | One invocation per role attributes cost directly |

## Trust boundaries

The system runs untrusted-ish model output against a real repository, so the boundaries matter. They are covered in [Security](../security.md), but in summary:

- **Model output is not trusted** to respect a policy stated in a prompt. [Probe 3](../probes/probe-3-context-isolation.md) and [Probe 4](../probes/probe-4-hook-blocking.md) both show cases where a model complied out of good manners, which is not enforcement.
- **The autonomy tier is not a security boundary** for an untrusted role, because it gates partly on a label the model supplies about its own command ([Probe 8](../probes/probe-8-self-declared-risk.md)).
- **Tool restriction is not path protection.** Disabling the `Edit` tool did not protect a file; the agent used a shell instead.
- **The session store is a shared surface.** Any agent with `Grep` can read a prior agent's transcript from `~/.factory/sessions/`.

## The evidence tier (Phase 3.2)

Phase 3.2 externalized the deterministic evidence layer so validators consume a compact structured bundle instead of re-running pytest in-session. The components:

```mermaid
graph LR
    LB["Local backend<br/>(pytest + verify-green + bandit)"] -->|produces| EB["EvidenceBundle<br/>(919 bytes, signed)"]
    EB -->|consumed by| VC["Validator consumer<br/>(ACCEPT/REJECT, no pytest)"]
    EB -->|consumed by| OG["Orchestrator gate<br/>(locked-sha cross-check)"]
    TA["Token accounting<br/>(fairness rule)"] -->|measures| EB
    TA -->|measures| RO["Raw pytest output<br/>(replaced)"]
```

The local backend runs the deterministic tier once (pytest, verify-green.py for the locked-hash check, Bandit for security) and normalizes the results into a signed JSON bundle. Validators read the bundle instead of re-running tests. The orchestrator cross-checks the bundle's `locked_test_sha_observed` against the lock manifest before trusting it.

The orchestration script (`tools/orchestrate-review.py`) wires the full review cycle: produce evidence, call N validators via `droid exec`, check for stray writes, parse verdicts, append telemetry, and report the gate decision. It stops only on error.

See [Evidence provider](../features/evidence-provider.md) and [Orchestration](../features/orchestration.md) for details.

## Key source files

| File | Purpose |
|---|---|
| `PRD.md` | Full specification: problem, hypotheses, invariants, workflow, phases, evaluation design |
| `README.md` | Project entry point and summary of the four core properties |
| `AGENTS.md` | Conventions binding every agent that works in the repo |
| `templates/SPRINT-PLANNING-TEMPLATE.md` | Canonical GROK → CHUNK → EXECUTE method, 666 lines |
| `phase-0/README.md` | The eight probes, their questions, and recorded verdicts |
| `phase-0/GO-NO-GO.md` | Phase 0 decision, invariant scorecard, build order |
| `phase-0/evidence/README.md` | Standard every probe record must meet |
| `phase-0/evidence/probe-4/reverify/rig/hook-protect2.py` | The fail-closed guard that holds against a shell bypass |
| `phase-0/evidence/probe-2/rig/hook-family-gate.py` | The family gate that aborts a wrong-model run before any tool acts |
| `phase-3.2/evidence/local_backend.py` | Local evidence producer: runs pytest + verify-green + Bandit, emits signed bundle |
| `phase-3.2/evidence/consumer.py` | Validator + orchestrator consumers: read bundle, verify signature, cross-check locked-sha |
| `tools/orchestrate-review.py` | Mechanical review pipeline: produce evidence, call validators, check stray writes, report gate |
| `tools/adapters/factory.py` | Vendor shim: normalizes droid exec output into vendor-neutral envelope shape |
| `telemetry/SCHEMA.md` | Data schema for the evaluation's telemetry (v2: test-designer role, MCP token fields) |
