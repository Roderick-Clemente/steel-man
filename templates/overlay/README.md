# Per-pilot adversarial-sprint overlay

Drop this directory's contents into `<PILOT_REPO>/.adversarial-sprint/` to make that pilot sprint-ready. The overlay gives the operator **one command to fire the runner** (`.adversarial-sprint/bin/run-sprint`) without changing the framework repo.

## Layout

```
<PILOT_REPO>/.adversarial-sprint/
├── sprint-loop-config.json    # per-pilot config (copy from ./sprint-loop-config.template.json)
├── chunks.json                # chunk spec (copy from ./sprint-loop-chunks-example.template.json)
├── bin/
│   └── run-sprint             # one-command runner entrypoint
└── README.md                  # this file
```

## Install (one-time per pilot)

```sh
# From the framework repo's templates/overlay/ dir:
mkdir -p <PILOT_REPO>/.adversarial-sprint/bin
cp templates/overlay/sprint-loop-config.template.json     <PILOT_REPO>/.adversarial-sprint/sprint-loop-config.json
cp templates/overlay/sprint-loop-chunks-example.template.json <PILOT_REPO>/.adversarial-sprint/chunks.json
cp templates/overlay/bin/run-sprint                      <PILOT_REPO>/.adversarial-sprint/bin/run-sprint
chmod +x <PILOT_REPO>/.adversarial-sprint/bin/run-sprint
```

Then edit `<PILOT_REPO>/.adversarial-sprint/sprint-loop-config.json`:
- replace `/REPLACE-WITH-FRAMEWORK-CHECKOUT-PATH` with the framework repo's absolute path
- replace `/REPLACE-WITH-PILOT-REPO-PATH` with the pilot's absolute path
- replace `/REPLACE-WITH-PILOT-VENV-PYTHON` with the pilot's venv python (e.g., `.venv/bin/python`)
- update model roster if the pilot's panel differs

## Use

```sh
# First time: dry-run end-to-end. Per §15 Act 2 / §16 demo-delta, this
# is the wiring test before any real model credits are spent.
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --dry-run --non-interactive

# Real run (operator in the seat at the reconcile gate):
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint

# Real run, unattended (no stdin pauses):
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --unattended
```

## What this overlay IS NOT

- **Not the universal rules.** Those live at the agent layer via `skills/adversarial-sprint/SKILL.md` for adversarial-sprint framework adopters, and at `tools/OPERATING-RULES.md` for the framework repo. The overlay does NOT duplicate them.
- **Not the runner.** The runner is `tools/sprint-loop.py` in the framework repo. The overlay is per-pilot wiring.
- **Not a per-pilot i18n / config layer for everything.** The overlay is a narrowly-targeted adapter: a) the path-bridging between framework and pilot, b) the one-command entrypoint.

## §15 framing (Act 1 vs Act 2)

- **Act 1** ("vibe code as usual"): the operator + agent in conversation. No runner invoked. Universal rules followed via the agent's skill layer.
- **Act 2** (this overlay): runner-driven sprint with structural guarantees at the §11 acceptance gate.

The runner isn't an *optional overlay* — it's the structural guarantee. This template lets you fire it correctly without per-pilot bash rituals.

## Failure modes the overlay guards against

- **Missing config** → SystemExit(2) with a clear "did you edit the placeholders?" message.
- **Wrong marketplace path** → SystemExit(2) with a similar diagnostic.
- **Missing chunks-file** → SystemExit(2) with a list of paths tried.
- **Missing EVIDENCE_SIGNING_KEY** → runner refuses in live mode per §7 (chunk-10 F-10).
- **Family-guard preflight fails** → SystemExit(2) before any droid call.
