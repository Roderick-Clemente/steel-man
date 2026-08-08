# Phase 0 — Feasibility Spike

Phase 0 was the build gate. Nothing in the later phases could start until we answered a set of platform questions with working probes rather than documentation reading or product assumptions. The repo's thesis is that multiple model families, separated by role, can author tests and review code without sharing each other's blind spots. Phase 0 tested whether Factory actually lets you set that up.

The environment was Factory CLI `0.186.0` on macOS, using a local pilot repo. The probes were scoped to that version; a capability that appears or disappears between versions is itself a finding.

## Key source files

| File | What it contains |
|---|---|
| `/Users/factory/work/adversarial-sprint-dev/phase-0/README.md` | Full probe results and verdict |
| `/Users/factory/work/adversarial-sprint-dev/phase-0/GO-NO-GO.md` | Written go/no-go decision |
| `/Users/factory/work/adversarial-sprint-dev/phase-0/evidence/` | Committed evidence per probe |
| `/Users/factory/work/adversarial-sprint-dev/PRD.md` | Framework spec that Phase 0 gates |

## The seven probes (plus one addendum)

Each probe asked a question that could kill or reshape the design.

1. **Per-role model pinning** — Can distinct models be pinned to planner, worker, and validator roles? **BLOCKED.** `droid exec --mission` returned zero turns, zero tokens, and exit 0 with a real prompt. The `--worker-model` / `--validator-model` flags exist but could not be exercised because the Mission did no work. This forced the command-orchestrated design.
2. **Fallback safety** — Can the plugin resolve effective model IDs before a family-violating fallback occurs? **CONDITIONAL PASS.** The resolved model is absent from the JSON envelope but present in the session transcript, so a `PreToolUse` hook can read it before any tool acts. `--model auto` is unusable for role-pinned work because the caller cannot know the resolved model in advance. `--reasoning-effort xhigh` on an unsupported model silently downgrades to `off` at exit 0.
3. **Custom Droid context isolation** — Do custom Droids give genuinely fresh context and enforceable tool restrictions? **SPLIT.** Tool allowlists are enforced by schema omission, and subagents get their own context. But read tools are not path-scoped: a validator with `Read`, `Grep`, `Glob`, and `LS` recovered a secret from the session store by grepping `~/.factory/sessions/<cwd-slug>/*.jsonl`. `droid search` surfaced the same secret. So invariant #2 needs a validator that has no `Execute`, plus a hook that asserts on both paths.
4. **Deterministic hook blocking** — Can hooks reliably block edits to locked test files? **PASS, with a hard rule.** A `PreToolUse` hook blocks an `Edit` to a SHA-256-locked test, the file stays unchanged, the executor gets `SPEC_OR_TEST_BLOCKED`, and the run continues. The guard must match `Execute` commands too and must fail closed on unparseable input; a `sed -i` slipped through when the guard only matched paths. Also, hooks are read from `/Users/factory/work/quantum-bank--llms-txt-pilot/.factory/settings.json`, not from `/Users/factory/work/quantum-bank--llms-txt-pilot/.factory/hooks.json` as the docs say. A misregistered hook produces no warning and exit 0.
5. **Rejection routing** — Can Mission validation route a rejection to retry or re-plan? Unanswered, blocked by Probe 1. Triggered the command-orchestrated contingency.
6. **Plugin distribution boundary** — Which settings, hooks, and Mission artifacts ship inside a plugin? **PASS.** A minimal plugin carrying a Droid, skill, and `PreToolUse` hook installed cleanly and activated without repo-local setup. The hook fired from the plugin even though standalone `/Users/factory/work/quantum-bank--llms-txt-pilot/.factory/hooks.json` did not. Some papercuts: `${DROID_PLUGIN_ROOT}` expands in the hook command but the env var is a literal sentinel, local marketplace is keyed by directory basename, and uninstall leaves stale config behind.
7. **Usage attribution** — Can credit/token usage be associated per role? Unanswered, blocked by Probe 1. The §13 cost hypothesis needs this.
8. **Self-declared risk as a policy input** — Does the autonomy tier gate on the model's own `riskLevel` label? **PASS with a caveat.** `--auto low` permits low, denies medium and high. The label responds to argument: `rm scratch.txt` was `high` unprompted and `medium` once a rationale was supplied. A hook can inspect `riskLevel` and `command` together and deny on mismatch, so this is buildable but not trustworthy by default.

## The central finding

The platform cannot fail loudly. A Mission that does nothing, a hook that never loads, a model silently downgraded from maximum reasoning to none, and a run whose every tool call was denied all report exit 0. Phase 0's verdict was therefore: **build the guard first; treat every green check as unproven until something we wrote has asserted it.**

## Verdict

**GO, with one mandatory design change: command-orchestrated, not Mission-native.**

No invariant was red. Three were green, three were amber that turn green once one component exists, and one was unprobed and low risk. The component is a single `PreToolUse` hook that reads the transcript, inspects what actually happened, and fails closed. That hook enforces locked tests, context isolation, and model-family separation, and it ships inside a plugin that activates on install.

## What carried into Phase 1

- Lock tests by SHA-256.
- Block edits with a `PreToolUse` hook that also guards `Execute` and fails closed.
- Register the hook in the right place (`/Users/factory/work/quantum-bank--llms-txt-pilot/.factory/settings.json` for standalone, plugin `hooks/hooks.json` for distributed).
- Never trust exit code or the final `result` string; gate on the hook's own log and per-tool `is_error`.
- Use explicit `--model` per role, not `--model auto`.
