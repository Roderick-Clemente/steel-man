# Backlog D — Capabilities Framework (forward design)

Status: **designed, not implemented.** Forward-of-chunk-11 design
note. The runner-as-skill-orchestrator extension is the project's
next-tier of capability, captured here so it survives compaction
between commits.

## Operator's vision (recorded)

> "I should be able to fire my adversarial scale and it should
> take the rest — whether [the runner is] broken into multiple
> skills, capability, [or one] — and I want to be able to evoke
> skills, for example example-and-use on this sprint for that
> 5-plan, or use this priority, or use it to help ask me
> questions about my new feature that I want to add."

Translated: the sprint-loop runner is **a router over skills** in
addition to a router over roles. The operator names a skill at any
of several hook points and the runner invokes it there, captures
its output, and feeds the next step.

## Hook points (capability invocation surface)

A capability (= active skill an operator names mid-sprint) can
fire at one or more of these hook points in the runner:

| Hook                  | When                                | Example capability         |
|-----------------------|-------------------------------------|---------------------------|
| `pre-sprint`          | before plan stage fires              | `feature-clarifier`       |
| `during-plan`         | after planner's plan document lands  | `priority-ranker`         |
| `during-review`       | per-reviewer verdict or finding row  | `acceptance-pattern-miner`|
| `pre-chunk`           | before each chunk's inner loop       | `chunk-coverage-checker`  |
| `during-executor`     | after executor write but pre-gate    | `silent-green-sniffer`    |
| `post-chunk`          | per-chunk evidence bundle produced   | `evidence-coverage-audit` |
| `post-sprint`         | after all chunks committed           | `acceptance-digest-writer`|

Each capability is a single markdown file under
`skills/capabilities/<name>.md` with YAML frontmatter declaring
*which* hook points it runs at, plus the input schema (what
runner state it reads) and output schema (what it writes back).

## Capability registration

Capabilities are registered in
`skills/capabilities/MANIFEST.yaml`:

```yaml
capabilities:
  - name: priority-ranker
    hooks: [during-plan, post-chunk]
    input: plan_doc_path
    output: ranked_findings (list of Finding with rank)
    runner-state-read: plan_sha256, plan_findings

  - name: feature-clarifier
    hooks: [pre-sprint]
    input: pilot_spec_file
    output: clarifying_questions (list of strings)
    runner-state-read: pilot_spec_file, planner_model

  - name: silent-green-sniffer
    hooks: [during-executor]
    input: chunk_diff
    output: silent_green_findings (list of Finding)
    runner-state-read: chunk_id, diff_after_executor
```

The runner reads the manifest at sprint-launch time and registers
a dispatcher that fires each capability at the right hook.

## Operator invocation surface

Two patterns:

1. **Per-run flag**: `sprint-loop.py --capability priority-ranker --capability silent-green-sniffer ...`
2. **Per-skill file** (operator-authored) at
   `skills/invocations/<sprint-id>.yaml` declaring which
   capabilities fire at which hooks for this run.

Pattern 1 is for short ad-hoc invocations. Pattern 2 is for a
reusable sprint shape — e.g., "feature-add sprint" pre-registers
the `feature-clarifier` (pre-sprint) and `priority-ranker`
(during-plan); "refactor sprint" pre-registers the
`silent-green-sniffer` and `evidence-coverage-audit`.

## What this changes about chunk 11

Chunk 11 ships the file-format / install surface (the "skills as
installed assets" shape). Backlog D extends the runner with the
"skills as invoked capabilities" shape. They compose:

- The chunk-11 install paths (`skills/<name>/SKILL.md`,
  `.factory/...`, `.claude/...`, `.cursor/...`) become the **asset
  layer** that capabilities reference.
- The chunk-11 rehydration step becomes the **recovery shape** for
  compaction-long sessions running capabilities.

## Why this isn't in chunk 11

Two reasons anchored in OPERATING-RULES:

1. **§17 capacity envelope**: chunk 11's budget was the file
   distribution surface. Bundling the dispatcher into the same
   chunk would expand chunk 11's surface to runner architecture -
   a different deliverable.
2. **§18 review at the end**: the dispatcher needs adversarial
   review against the PRD §11 acceptance criteria themselves when
   implemented - it's the same shape that surfaced F-1/F-2/F-7/F-8
   in chunk 10.

## Phasing

| Phase | Deliverable                                         |
|-------|-----------------------------------------------------|
| 4.5 (now) | Foundation: skill distribution shape + convention doc + install paths |
| **Future — Backlog D, post-Phase-5** | Capability registry: `skills/capabilities/MANIFEST.yaml` + dispatcher in runner |
| **Future — Backlog D, post-Phase-5** | Pre-built capabilities: priority-ranker, feature-clarifier, silent-green-sniffer |

The runner-as-router shape with hook points is the unifying
abstraction across both — but each ship is a verifiable deliverable,
not a half-built version of both.

**Renumbered from "Phase 6 / Phase 7" per pass-r2 finding G-11:**
the PRD defines Phase 6 as "no new feature work" and Phase 7 as
outside the measured 0–6 arc. Backlog D is unimplemented design
captured here so it survives compaction; the actual phase numbering
lands when the PRD moves its gates.

## See also

- `tools/conventions/skill-distribution.md` (chunk 11 convention)
- `skills/adversarial-sprint/SKILL.md` (meta-skill — durable principles)
- `skills/sprint-invocation/SKILL.md` (invocation skill - how to fire the
  runner)
- OPERATING-RULES §18 / §19
