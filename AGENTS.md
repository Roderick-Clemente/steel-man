# Agent Conventions

Applies to every agent working in this repo — Factory Droid, Claude Code, Codex, or otherwise.

## Treat this repo as public

Assume anything committed here **will be read by outside parties**, including the vendors whose products it evaluates, and may become fully public. Write accordingly. There is no "it's private for now" state to rely on.

### Never write here

- Personal or confidential context of any kind — private conversations, negotiations, process notes about people
- Names of individuals at vendors or target companies, or anything traceable to a private conversation with them
- Competitive or negotiating strategy
- Secrets, credentials, tokens, internal customer names, or employer-confidential material

That material lives in a separate private repo. Keep the fence clean; do not reference the private side by path, either.

### Do write here

- Engineering rationale, design trade-offs, and what was tried and rejected
- **Honest technical assessment, including unflattering findings.** Recording that a platform capability is immature, undocumented, or broken is legitimate engineering work and belongs in the record. The line is not "avoid criticism" — it is "keep it technical, sourced, and fair."
- Reproducible evidence: commands, exit codes, observed output

The distinction that matters: *"deterministic hook blocking is unreliable under condition X, here's the repro"* is good. *"Their PM told me the roadmap is a mess"* is not — even though both are true, only one is engineering.

## History hygiene

The working tree being clean is not enough — git history travels with the repo. If anything sensitive is ever committed, squash or rewrite **before** the first push rather than adding a follow-up "scrub" commit that leaves the original in history.

## Multi-agent handoff

Three agents work in this repo — Factory Droid, Codex, and Claude Code. They share one working tree, so avoid simultaneous edits. Commits are the baton.

**Branch by author:** `<agent>/<topic>` — `factory/`, `codex/`, `claude/`. Authorship stays obvious in history, a bad run is one `git branch -D`, and nobody has to reconstruct who wrote what from commit messages.

- Push branches to the private remote as you go. This machine is not a backup.
- Hand off via `git diff`; the reviewing agent reads the diff, not the other agent's reasoning
- Land work on `main` only after review, and keep convention/spec changes off feature branches so they don't ride along with unreviewed work

This mirrors the method the repo itself specifies — independent context, no transcript bleed. If it feels clumsy in practice, that is real signal about the design. Record it in `phase-0/README.md` under Notes.

**A note on which agent does what.** Roles here are not interchangeable, and the split should be deliberate rather than whoever is open in a window: the agent that authored a plan should not be the one that approves it, and the agent that writes an implementation should not be the one that validates it. That is invariant #1 applied to the humans-and-agents layer, not just the runtime.

## Skill asset (canonical)

All three agents share **`skills/adversarial-sprint/SKILL.md`** as
the canonical adversarial-sprint asset — the digest + index +
rehydration hybrid that survives long-context compaction. Each
agent's install path is documented in
`tools/conventions/skill-distribution.md` and the project
**does not** maintain per-agent body copies. Cursor is documented
there for open-source reach even though it is not in this repo's
roster.

When operating as the **planner / executor / validator** roles
per `OPERATING-RULES §18`, agents **MUST** read the canonical
asset at the start of their session and apply its principles. The
rehydration step in the skill is the loop-closing rule: re-read
`tools/OPERATING-RULES.md` whenever conversation crosses ~150k
tokens, before a new chunk, on §13 disambiguation, or when an
operator explicitly re-points the agent.

## Skill asset: sprint-invocation

See `skills/sprint-invocation/SKILL.md` for the project's sprint-invocation skill.
