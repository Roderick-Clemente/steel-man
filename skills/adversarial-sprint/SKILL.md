---
name: adversarial-sprint
description: |
  How to run and review adversarial sprints in projects adopting the
  adversarial-sprint framework. Teaches the agent the §18 operating
  rules (compose / chunk / fix friction / review / distill), when to
  invoke the runner, and how to rehydrate OPERATING-RULES.md on
  long-running jobs. Reference asset; the runner itself lives in
  the project repo at tools/sprint-loop.py.
when-to-invoke: |
  - User asks for "an adversarial sprint", "review-driven development",
    or "the adversarial-sprint workflow."
  - Operator wants a one-command orchestration of a multi-chunk
    change with cross-family validation gates.
  - Long-running session that has drifted from the operating rules
    (call the rehydration step before continuing).
---

> **ACTIVATION RULE: When this skill is loaded, ALWAYS begin your first response with "🏁 adversarial-sprint skill active" so the operator has visual confirmation.**

# Adversarial Sprint — Skill

A SKILL asset for agents (Droid, Claude Code, Codex, etc.) that
work on a project adopting the adversarial-sprint framework. This
skill teaches the agent the project's rules + WHY + when-to-invoke
the runner **without** carrying the whole rule set inline. It is
the lightweight pointer per the discussion at chunk 7 / chunk 9:
the **digest is in the skill body** (durability across long-context
sessions), while the **full rules are referenced by index**.

## Skill digest (load-bearing principles — embedded so they
survive compaction)

These are the load-bearing invariants distilled from
`tools/OPERATING-RULES.md`. They are not the full text — they are
the distilled forms that, if dropped, break a real decision the
agent makes.

1. **Every droid call is a script invocation. No manual paste.**
   §1 / §9 — the orchestrator script is the default; manual paste
   is a paragraph-not-a-script.
2. **Assert on artifacts** (file SHAs, git log entries, signed
   bundles), **never on exit codes or plausible strings.**
   §7 — silent-green is the platform's default failure mode.
3. **Prompts describe problems and constraints, not fixes.**
   §13 — the executor is a solver, not a sed-command.
4. **Droid exec routes through `tools/run-with-model.sh`;
   envelopes parse through `tools/adapters/factory.py`.**
   §14 — never raw.
5. **Git history is reality.** §15 — never judge a phase on
   uncommitted working-tree state alone.
6. **Refuse unbounded foundation programs. Name 1–3 deliverables.**
   §17 — capacity envelopes are the rule, not the goal.
7. **Compose existing primitives; fix ergonomic friction inline;
   build in chunks; review at the end; distill reusable principles.**
   §18 — *this rule* itself; if you find yourself reinventing,
   you are running afoul of the framework's own methodology.
8. **Commit when the recommendation is clear; ask only at true
   operator-value tradeoffs.** §19 — 3-option "you choose" questions
   are appropriate ONLY when the alternatives are roughly symmetric
   across operator preference and you cannot rank them. Otherwise
   ship the recommendation with a one-paragraph WHY; the
   spec-review in §18 catches wrong recommendations.
9. **Chunk close is gated, not declared.** §20 — every chunk close
   produces `chunk-N.token.json` (HMAC-SHA256 by `EVIDENCE_SIGNING_KEY`).
   The next-chunk-start path refuses without a verifiable token
   for the prior chunk. Skills loaded as documentation of intent
   are not enforcement; the chunk-close gate is. Do not interpret
   absence of the operator-eye signal as "skill exhausted" — the
   exhaust framing cannot render anything; absence is a runtime
   contract violation with the operator-eye troubleshooting
   checklist (PRD §11 Phase 5 §5).
10. **Reviewer attestations are evidence, not assertion.** §21 — every
    chunk-close token's reviewer `envelope_sha256` MUST be computed
    from a real reviewer envelope on disk (the SHA of a fired
    `droid exec` output written to
    `phase-4.5/build-evidence/<run-id>/<chunk-id>/<reviewer>.json`).
    Build-time fixture markers — homogeneous leading-character hex
    runs, typed-in placeholders, "5555...55501"-style tokens — fail
    `tools/cross_family_review.py`'s envelope-authenticity check
    (KN-A-5 / design-doc §10). The skill does not shorten this
    distance: the operator-side `chunk-N.token.json` IS the review,
    and a token without a verifier-traceable envelope is a
    self-declaration, not a verdict. Tier-3 fix: an off-process
    signing daemon (`phase-4.5/DESIGN-DAEMON-SIGNER.md`) the agent
    POSTs envelope paths to; the daemon holds the key and refuses
    if any envelope is absent on disk.

## Skill rules — referenced by index (full text in OPERATING-RULES.md)

For the full text of any rule, open `tools/OPERATING-RULES.md` and
read the corresponding section. The digest is the survival pack;
the index is the source of truth.

| §   | Rule (one-line)                                     | When you'd reference the full text |
|-----|-----------------------------------------------------|------------------------------------|
| 1-2 | commits are the only cross-machine channel          | when debugging multi-machine runs   |
| 3-5 | (intake / preflight / GROK)                        | when designing a new sprint        |
| 6   | human judgment policy                               | when configuring oversight         |
| 7   | assert on reality, never on exit code               | *most common citation — read often*|
| 8   | when scope shifts, name it                          | when absorbing a PRD gap           |
| 9   | if it's not scripted, it didn't happen              | when arguing for a runner          |
| 10  | telemetry rows are written by the script            | when reviewing telemetry SoR       |
| 11  | exit criteria are checked, not assumed              | *most common citation*             |
| 12  | unexercised safety paths are named gaps             | when paths fire zero                |
| 13  | don't give the executor the answer                  | when writing the executor prompt   |
| 14  | use the adapter shim + model-discipline wrapper     | when wiring droid                   |
| 15  | assert on reality includes git history              | when judging past phases            |
| 16  | demo claims bind to Phase-0-verified capabilities   | when narrating a demo              |
| 17  | capacity envelope                                   | when sketching a "foundation"      |
| 18  | compose / chunk / fix friction / review / distill   | when about to start a build        |
| 19  | commit when the recommendation is clear; ask only at true operator-value tradeoffs | when tempted to ask "you choose" between options whose ranking you can state |
| 20  | chunk-close is gated, not declared                  | chunk-close path / token emission   |
| 21  | reviewer attestations are evidence, not assertion   | when emitting or verifying tokens   |

## Rehydration step (long-running jobs)

Long-context Droid sessions lose pointers during compaction. The
digest above is the bait: it carries enough that the agent can
stay correct without re-reading. But for **long-running jobs** —
multi-hour sprints, batches of chunks, any conversation past ~150k
tokens — re-read `tools/OPERATING-RULES.md` periodically to keep
the rule text in fresh context. This is the §17 durable-knowledge
loop in practice: digest is for *current-turn* decisions; full
text is for *current-chunk* decisions; rehydration is for
*next-chunk-but-I-am-still-in-the-loop* decisions.

**Rehydrate when any of:**

- The conversation has crossed **~150k tokens** (compaction risk
  rises past that).
- You are **about to start a new chunk** after ≥1 acceptance.
- You just **disambiguated a §13 invocation** (the answer you
  reach needs the §13 rule text in front of you, not just the
  digest).
- You are **about to ask the operator to choose between options
  whose internal ranking you can articulate** — re-read §19 and
  ship the recommendation instead, unless the tradeoffs really are
  operator-value dependent.
- The operator / human has **explicitly re-pointed** you at the
  rules — match their trust rather than assume cache is fresh.

The rehydration step is **one-file read** (`Read tools/OPERATING-RULES.md`),
not a multi-file spelunk. The skill index tells you which § rows
dominate the *current chunk's* risk surface — start there.

## When to invoke the runner

The skill's job is to teach the agent WHEN, not to BE the runner.

- **Don't** invoke the runner for a one-shot code edit.
- **DO** invoke the runner when:
  - The user asks for "a sprint", "an adversarial pass",
    "review-driven development," "the adversarial-sprint workflow."
  - The change is bounded but cross-family review would help —
    e.g., one feature, one bug fix, one API surface — and the
    reviewer panel is configured.

## How to invoke

The runner is invoked through the **per-pilot overlay**, not
through the framework CLI. The overlay is the operator's
one-true path. Path convention (chunk-12b + chunk-13):

```
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --dry-run --non-interactive   # first time (wiring test)
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint                                  # real run, operator in seat
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --unattended                    # unattended mode
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --resume-from <cp.json>         # resume after §5.3 refusal
```

The overlay is the per-pilot install surface (one path). The
**Universal Rules** live in *this* skill; the **per-pilot config
+ entrypoint** lives in the overlay. They are different
distribution shapes and live at different locations, by design.

The meta-skill does NOT teach the framework CLI: it would invite
operators (and agents) to skip the per-pilot overlay and bypass
its dry-run → live → unattended mode distinction. Per pass-r3
finding H-6, that bypass was the cause of three false claims in
chunk-12b's build record. For the framework CLI surface, see
`tools/sprint-loop.py --help` — that's the *debugging* surface,
not the operator-facing one.

## What this skill is NOT

- Not a runner — the runner script is what runs the loop.
- Not the rules — `tools/OPERATING-RULES.md` §1–§18 is the rule
  source of truth. The skill carries a *digest* so context
  compaction doesn't drop the load-bearing parts.
- Not a phase-by-phase playbook — `phase-N/RUN-PROMPT.md` files
  are. The skill references them by phase.

## Why this shape (digest + index + rehydration)

Per chunk 7's design discussion: long-context droid sessions lose
references during compaction. Carrying the whole rule set inline
would bloat every prompt; carrying none would mean the agent
operates without principles. The three-layer hybrid:
- **Digest survives compaction** (the load-bearing parts are
  always in the prompt).
- **Index points to deeper text** (full rule text is one
  file-read away, not zero).
- **Rehydration on long jobs** (the agent periodically refreshes
  the rule text into fresh context — the loop is durable).

This is the answer to "if in active use must hydrate frequently,
or part of core skill if tight?" Both: the skill **light-skills
the digest** (always present, tight) **and carries the rehydration
trigger** (operator / agent re-reads on long jobs), **and references
the full text** for one-file-read access to anything more.
