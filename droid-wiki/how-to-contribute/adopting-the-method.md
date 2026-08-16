# Adopting the method

You can run an adversarial sprint against your own project without modifying this repo. The framework ships a per-pilot overlay you drop into your pilot repo, and from there one command fires the runner. This page is the setup guide.

The overlay is the only operator-facing entrypoint. `tools/sprint-loop.py --help` is the debugging surface. You do not invoke the framework CLI directly.

## What you need first

- A pilot repo with its own test suite. The runner drives your tests as the acceptance signal.
- API keys for each model family in your panel (Factory API keys, or individual vendor keys). The default config uses an OpenAI executor with Google and xAI validators, but you edit the roster.
- The `droid` CLI installed, for live runs. A dry-run needs none of these.
- `EVIDENCE_SIGNING_KEY` set in your environment. The runner signs every chunk-completion token with it. In live mode, a missing key is a §7 fail-closed refusal, not a warning.

## Install the overlay (one-time per pilot)

From the framework repo at `/Users/factory/work/adversarial-sprint-dev`:

```bash
mkdir -p <PILOT_REPO>/.adversarial-sprint/bin
cp templates/overlay/sprint-loop-config.template.json \
   <PILOT_REPO>/.adversarial-sprint/sprint-loop-config.json
cp templates/overlay/sprint-loop-chunks-example.template.json \
   <PILOT_REPO>/.adversarial-sprint/chunks.json
cp templates/overlay/bin/run-sprint \
   <PILOT_REPO>/.adversarial-sprint/bin/run-sprint
chmod +x <PILOT_REPO>/.adversarial-sprint/bin/run-sprint
```

The overlay layout, once installed:

```
<PILOT_REPO>/.adversarial-sprint/
├── sprint-loop-config.json    # per-pilot config, edited from the template
├── chunks.json                # your chunk spec, edited from the example
└── bin/
    └── run-sprint             # one-command runner entrypoint
```

## Edit the config

Open `<PILOT_REPO>/.adversarial-sprint/sprint-loop-config.json` and replace the placeholders:

- `framework_root` — the absolute path to your checkout of this repo.
- `pilot_root` — the absolute path to your pilot repo.
- `pilot_python` — the pilot's venv python, e.g. `.venv/bin/python`.
- `validators` — the model roster for your panel, in `model:provider:family:model-id` form.
- The per-role model fields (`planner_model`, `executor_model`, etc.) if your panel differs from the defaults.

Set `EVIDENCE_SIGNING_KEY` in your shell before you launch. The config references it by env-var name (`signing_key_env`), not by value, so the key never lands in the repo.

## Install the skills

The agent-facing skill assets install in one command from the framework repo:

```bash
/Users/factory/work/adversarial-sprint-dev/tools/install-skill.sh all
```

This drops the canonical adversarial-sprint skill into each agent's install path. No per-agent body copies are maintained. See `tools/conventions/skill-distribution.md` for the per-agent recipes.

## Three run modes

```bash
# 1. Wiring test — no model credits, no commits.
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --dry-run --non-interactive

# 2. Real run — you stay in the seat at the reconcile gate.
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint

# 3. Unattended — live run, no stdin pauses; refusals write a checkpoint.
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --unattended
```

Start with the dry-run. It simulates the whole pipeline without invoking the executor or committing. If the overlay exits 0 and prints `COMPLETED · run_id=...`, the wiring is good. That banner is not a real verdict — it is a §7 silent-green shape — so treat it as proof the plumbing is intact, not proof a chunk would land.

For the real run, you type `accept`, `amend <reason>`, or `reject <reason>` at the reconcile gate. If both reviewers flag a blocker or high finding, `accept` refuses with `SystemExit(4)`. Use `amend` to record a disposition or `reject` to loop back to the planner.

The unattended mode runs the same §5.3 preconditions but skips the stdin pause. On a refusal it writes a `checkpoint.json` and exits 4 or 5, never silent. Resume with `--resume-from <checkpoint.json>`.

## Write your chunks

Edit `<PILOT_REPO>/.adversarial-sprint/chunks.json`. Each chunk names a scope, observable criteria, allowed files, locked test files, and the commands that prove it landed. The example template has one chunk you can copy and extend. Keep 1-3 deliverables per chunk — the runner refuses unbounded foundation programs.

## Where to read next

- [getting started](../overview/getting-started.md) for the quick version of this setup
- [the sprint loop runner](../features/sprint-loop-runner.md) for what the runner does between chunk start and close
- `skills/sprint-invocation/SKILL.md` for the operator-surface recap and flag semantics
- `templates/overlay/README.md` for the line-by-line install and the failure modes the overlay guards against
