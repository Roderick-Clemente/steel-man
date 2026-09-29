# Patterns and conventions

This page used to restate the conventions inline. That meant every one of them had two homes — this page and the real source — and two homes is one more place for the copy to go stale than the fact ever needed. Below is the map: what exists, and where the actual text lives. Read the source, not a summary of it.

| Topic | Read this |
|---|---|
| The 24 operating rules, each with the incident that produced it | `tools/OPERATING-RULES.md` |
| The agent-facing digest of the load-bearing rules | `skills/adversarial-sprint/SKILL.md` |
| Model-pinning policy — which seats must pin `--model`, which may use `--auto` | `tools/conventions/model-discipline.md` |
| The commit body's model-attribution format | `tools/conventions/commit-body-recipe.md` |
| Installing the skill across Factory, Claude Code, Cursor, and Codex | `tools/conventions/skill-distribution.md` |
| Branch-by-author, the commit-as-baton handoff | [development workflow](development-workflow.md) |

## The honesty constraints

This part is short enough, and specific enough to this framework's stance, that it's worth stating here rather than sending you somewhere else for one paragraph:

- Different model families are an independence control, not proof of correctness.
- Tests are executable evidence, not truth.
- Two reviewers agreeing means no known dispute, nothing more.
- A demo illustrates the mechanism; it does not validate the hypotheses.
- A clean null result is valid data.

## Where to read next

- [development workflow](development-workflow.md) for the agent-handoff conventions
- [testing](testing.md) for what the suite enforces
- `tools/OPERATING-RULES.md` directly if you're about to touch a gate
