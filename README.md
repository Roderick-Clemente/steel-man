# Adversarial Sprint

*Multi-model adversarial planning, execution, and validation for agentic coding — built as a Factory plugin.*

**Status:** Phase 0 (feasibility) GO · Phase 0.5 (validation ladder) closed · Phase 1
(test-evidence slice) shipped **with known enforcement gaps** — see
[`phase-1/KNOWN-ISSUES.md`](./phase-1/KNOWN-ISSUES.md) · Phases 2–5 in progress.
Phase gates to date are self-declared; only Phase 1 has been independently probed.
**Pilot repo:** [`Roderick-Clemente/quantum-bank`](https://github.com/Roderick-Clemente/quantum-bank), pinned at `2b70eae1`
**Full spec:** [`PRD.md`](./PRD.md)
**License:** [Apache-2.0](./LICENSE) — see [`NOTICE`](./NOTICE)

---

## The idea

Quality in agentic coding doesn't come from a smarter model. It comes from **structural separation of roles across different model families**, with the expensive thinking front-loaded into planning and executable evidence — not self-assessment — deciding whether work is done.

Four things make it work, and all four are enforced rather than suggested:

1. **Family separation.** The plan reviewer isn't the planner's family. The validator isn't the executor's family. Two passes from one model family are one opinion twice.
2. **Fresh review context.** The validator sees the approved spec, the diff, read-only repo state, and test evidence. It never sees the executor's reasoning or self-assessment.
3. **Independent test authorship.** The executor is prevented from writing or modifying the tests that judge it — locked by content hash, enforced by a PreToolUse hook. Enforcement is real but not yet complete: see [`phase-1/KNOWN-ISSUES.md`](./phase-1/KNOWN-ISSUES.md) for the gaps found by probing the deployed guard, and the harness that reproduces them.
4. **Valid RED before GREEN.** Behavior-changing work can't start until the intended assertion has run and failed *for the expected reason*. A syntax error is not a RED.

## What it isn't

Not a replacement for Factory Missions, Spec Mode, custom Droids, hooks, or CI — it composes those around the workflow gap.

And it makes no claim to be a correctness oracle. Different model families are an independence control, not proof. Tests are executable evidence, not truth. Two reviewers agreeing means no known dispute, nothing more. The value is a governed process that makes assumptions, disagreements, and evidence **visible**.

## Where it came from

The method has been run manually for months — one model plans, a different family attacks the plan, both audit the test strategy, a cheap agent implements small chunks, an independent agent validates each one. This repo turns that into something repeatable.

The sprint method itself is in [`templates/SPRINT-PLANNING-TEMPLATE.md`](./templates/SPRINT-PLANNING-TEMPLATE.md) — GROK → CHUNK → EXECUTE, TDD Red-Green-Refactor, independently executable chunk files, audit trail. That file is the canonical copy; six-plus repos hold stale duplicates.

## Layout

```
PRD.md                              full spec — problem, invariants, phases, evaluation design
templates/SPRINT-PLANNING-TEMPLATE.md   canonical GROK/CHUNK/EXECUTE method
phase-0/                            feasibility probes — the current gate
```

Plugin structure (`droids/`, `skills/`, `schemas/`, `scripts/`) gets created once Phase 0 says the design is buildable, not before.

## Next

[`phase-0/README.md`](./phase-0/README.md) — seven probes against the installed Factory version. Nothing else starts until those are answered with working code.
