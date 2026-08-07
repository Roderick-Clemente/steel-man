# Spec: on-merge wiki-refresh trigger (event-driven, not time-based)

**Goal.** Keep the wiki current without an unattended agent editing the shared
working tree on a clock. A wiki update is *event-driven* — it should happen when
a phase/experiment lands, i.e. on merge to `main` — not every N hours. This spec
is the design; wiring the trigger lives in the repo's CI config (GitHub / Harness)
and needs to be done there.

## Why not a time-based cron

- A few-hour cron mostly wakes to nothing changed, burning tokens for no work.
- The real hazard is safety: an unattended *writing* agent in a shared working
  tree can commit half-states or clobber another agent's uncommitted work.
  Three agents already share this tree (AGENTS.md) — "commits are the baton."
- The natural signal is a merge, and a git trigger already exists on the repos.

## Trigger shape

1. **Event:** push/merge to `main` (native git trigger; one already exists on the
   pilot, one is planned for this repo).
2. **Action:** launch a wiki-refresh agent that reads the *committed* diff since
   the last wiki update and proposes wiki edits.
3. **Isolation (non-negotiable):** the agent works on its **own branch**
   (`factory/wiki-refresh-<sha>` via `git worktree`), **never** edits the shared
   tree or `main` directly, and opens a PR. No force-push to wiki pages.
4. **Landing:** the PR goes through the normal human/review gate. CI augments; it
   does not auto-publish narrative.

## Guardrails

- **Read committed state only.** The agent diffs `main` at the merge SHA vs the
  last wiki-update marker; it does not read other agents' uncommitted work.
- **Scope to the wiki.** It may only touch `droid-wiki/**`. A path guard (reuse
  the existing hook-matcher pattern) fails closed on anything else.
- **Idempotent + attributed.** Re-running on the same SHA is a no-op; commits
  carry the agent attribution convention.
- **Sensitive-content check.** Before commit, run the same secret/sensitive
  scan the orchestrator uses pre-push (AGENTS.md "treat this repo as public").

## What's left to wire (repo side)

- Add the git trigger for this repo (pilot already has one).
- Provide an agent runner in CI (this is the same "agent-in-CI" capability the
  Phase 3.2 evidence-provider work needs; share the plumbing).
- Decide the last-wiki-update marker (a tag, a file, or the last commit touching
  `droid-wiki/**`).

## Relationship to Phase 3.2

This is a small, concrete instance of the Phase 3.2 pattern: an event-driven,
branch-isolated, review-gated agent action driven off a git trigger. If the 3.2
evidence-provider abstraction gets an agent-in-CI runner, this rides on the same
rails. Until then it stays a spec, not a live automation.
