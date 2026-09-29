# Development workflow

This repo is worked by three agents, not one. Factory Droid, Codex, and Claude Code share a single working tree, and the conventions exist to keep that from turning into a merge war. The short version: branch by author, commit is the baton, and never edit the same file at the same time as another agent.

The full conventions live in `~/work/adversarial-sprint-dev/AGENTS.md`. This page is the onramp. Read it before your first commit, then come back here when you need the recipe.

## Branch by author

Every branch carries its author's name as a prefix: `factory/<topic>`, `codex/<topic>`, `claude/<topic>`. Authorship stays obvious in history, a bad run is one `git branch -D`, and nobody has to reconstruct who wrote what from commit messages.

Keep convention and spec changes off feature branches. They ride along with unreviewed work and contaminate the diff. Land work on `main` only after review.

## Commits are the baton

Agents do not read each other's reasoning. They read diffs. When you hand off, you hand off a commit, and the reviewing agent reads what changed, not what you were thinking. This mirrors the framework's own thesis: independent context, no transcript bleed.

Push branches to the remote as you go. The local machine is not a backup, and a branch that only exists locally is one power loss away from gone.

## The commit body recipe

Every commit that runs a model carries the model attribution in its body — evidence that a separation-bearing seat was held by the model it claims, not decoration. The exact format lives in `tools/conventions/commit-body-recipe.md`; the model-pinning policy behind it (which seats must pin `--model`, which may use `--auto`) is in `tools/conventions/model-discipline.md`. Read those directly rather than a copy here — the format has changed before, and a second copy is a second place to forget to update it.

## The multi-agent handoff

Three agents, one tree. Avoid simultaneous edits. If you are about to touch a file, pull first and check that no other agent has it open. The clean way to coordinate is to finish a chunk, commit, push, and let the next agent pick up from the commit.

The split should be deliberate, not whoever is open in a window. The agent that authored a plan should not approve it. The agent that writes an implementation should not validate it. That is the framework's first invariant applied to the humans-and-agents layer.

## What to read first

- `AGENTS.md` for the conventions that apply to every agent
- [patterns and conventions](patterns-and-conventions.md) for where the operating rules and model discipline actually live
- [testing](testing.md) for how to run the suite before you push
- [getting started](../overview/getting-started.md) if you have not cloned yet

If the workflow feels clumsy in practice, that is real signal about the design. Record it in `planning/phase-0/README.md` under Notes.
