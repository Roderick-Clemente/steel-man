# Adopting the method

You can run an adversarial sprint against your own project without modifying this repo. The framework ships a per-pilot overlay you drop into your pilot repo, and from there one command fires the runner. This page is the setup guide.

The overlay is the only operator-facing entrypoint. `tools/sprint-loop.py --help` is the debugging surface. You do not invoke the framework CLI directly.

## What you need first

- A pilot repo with its own test suite. The runner drives your tests as the acceptance signal.
- API keys for each model family in your panel (Factory API keys, or individual vendor keys). The default config uses an OpenAI executor with Google and xAI validators, but you edit the roster.
- The `droid` CLI installed, for live runs. A dry-run needs none of these.
- `EVIDENCE_SIGNING_KEY` set in your environment. The runner signs every chunk-completion token with it. In live mode, a missing key is a §7 fail-closed refusal, not a warning.

## Install the overlay (one-time per pilot)

The exact commands, the resulting file layout, and the config placeholders to edit are in `templates/overlay/README.md` — that file is the install source, kept here would just be a second copy that can drift from the templates it's describing the moment either one changes.

One thing worth calling out ahead of reading it: set `EVIDENCE_SIGNING_KEY` in your shell before you launch anything live. The config references it by env-var name, not by value, so the key never lands in the repo.

## Install the skills

The agent-facing skill assets install in one command; see `tools/conventions/skill-distribution.md` for the exact command and the per-agent recipes. One canonical skill body, four install paths (Factory, Claude Code, Cursor, Codex) — no per-agent copies to keep in sync.

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
