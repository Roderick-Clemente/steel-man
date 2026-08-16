# Patterns and conventions

## The operating rules

`tools/OPERATING-RULES.md` is 24 rules, each with the incident that produced it. The rules are the operating discipline on top of `AGENTS.md`'s repo conventions. The load-bearing principles:

1. **Assert on artifacts, never on exit codes or plausible strings.** Silent-green is the platform's default failure mode. A successful exit with a plausible-looking answer is not evidence.
2. **Every droid call is a script invocation.** No manual paste. The orchestrator script is the default.
3. **Prompts describe problems and constraints, not fixes.** The executor is a solver, not a sed command.
4. **Droid exec routes through `tools/run-with-model.sh`; envelopes parse through `tools/adapters/factory.py`.** Never raw.
5. **Git history is reality.** Never judge a phase on uncommitted working-tree state alone.
6. **Refuse unbounded foundation programs.** Name 1-3 deliverables per chunk.
7. **Compose existing primitives.** Fix ergonomic friction inline. Build in chunks. Review at the end.
8. **Chunk close is gated, not declared.** Every chunk close produces a signed token. The next chunk refuses to start without one.

The full text with incident context is in `tools/OPERATING-RULES.md`. The agent-facing digest is in `skills/adversarial-sprint/SKILL.md`.

## Model discipline

Every invocation's model is recorded. Separation-bearing seats (plan reviewer, test designer, validator) pin `--model` before running so the provider cannot swap. The planner and executor may use `--auto`, provided the resolved model ID and family are recorded in the commit body and telemetry.

The standing family map lives in `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`. Unknown models resolve to `unknown` and cannot satisfy a hard separation constraint. The run stops rather than optimistically admitting an unknown model.

See `tools/conventions/model-discipline.md` for the full policy.

## Commit body recipe

Every commit that runs a model carries the model attribution:

```
Model: gpt-5.4-mini (providerLock: openai, apiProviderLock: openai)
Role: executor
Reviewer-panel: gemini-2.5-pro, grok-4.5 (Codex excluded — same family as author)
```

See `tools/conventions/commit-body-recipe.md` for the exact format.

## Skill distribution

One canonical skill body (`skills/adversarial-sprint/SKILL.md`), four install paths (Factory, Claude Code, Cursor, Codex). No per-agent body copies. The install is one command:

```bash
$REPO/tools/install-skill.sh all
```

See `tools/conventions/skill-distribution.md` for the per-agent recipes.

## Branch conventions

Branch by author: `factory/<topic>`, `codex/<topic>`, `claude/<topic>`. Authorship stays obvious in history. Commits are the baton between agents. Land work on `main` only after review.

## The honesty constraints

- Different model families are an independence control, not proof of correctness.
- Tests are executable evidence, not truth.
- Two reviewers agreeing means no known dispute, nothing more.
- A demo illustrates the mechanism; it does not validate the hypotheses.
- A clean null result is valid data.
