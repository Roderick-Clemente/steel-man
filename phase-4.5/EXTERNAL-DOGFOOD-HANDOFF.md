# External dogfood handoff — adversarial-sprint framework

You are working in the framework repo:
  /Users/factory/work/adversarial-sprint-dev
  branch: factory/phase-4.5-loop-runner  (HEAD 90f08dd, Phase 4.5 = PAUSED)

Context: the framework was dogfooded end-to-end against a NEW, external
PRD (an EOS/"Ninety-style" MVP) in a fresh pilot repo
(Roderick-Clemente/evan-os). The run went: PRD -> cross-family PRD
review (grok-4.5 + gemini-3.1-pro-preview, both REJECT_PLAN) -> 6 spec
fixes -> chunk -> overlay dry-run (green). It surfaced findings that are
framework-level, not pilot-level. Your job is to triage and fix the
framework issues below. The pilot's own findings file is
evan-os/.adversarial-sprint/DOGFOOD-FINDINGS.md (D-1..D-5) if you want
the raw source.

Read first: phase-4.5/KNOWN-ISSUES.md (KN-J*), phase-4.5/RUN-PROMPT.md,
tools/OPERATING-RULES.md §7/§11/§12, tools/sprint_loop/per_chunk.py,
phase-1/scripts/{valid-red,verify-green}.py.

## Findings to act on (priority order)

### P1 — Language-agnostic test-runner adapter (was D-1; Backlog E)
`phase-1/scripts/verify-green.py` and `valid-red.py` hard-code
`python -m pytest`. Any non-Python pilot (the EOS pilot is Next.js/TS)
cannot be verify-green'd. Today the only way to run the loop on a JS
pilot is to shape chunks as fake pytest commands, which defeats the
RED→GREEN gate.

**Ask:** introduce a test-runner adapter (e.g. `tools/adapters/test_runner.py`)
that maps a `pilot_test_runner` config value (`pytest|vitest|jest`,
extensible) to a command + a normalized (returncode, stdout, stderr)
result. Thread `pilot_test_runner` through `config.py` → `RunState`
→ `per_chunk.py`'s `validate_red` / `verify_green` → the two scripts
(new `--test-runner` flag, default `pytest`). Make `valid-red.py`'s
`INVALID_RED_SIGNATURES` and pass/fail detection runner-aware.

**Acceptance:** existing 80/80 tests stay green with `pytest` as default;
new unit tests cover the `vitest`/`jest` command construction and a JS
pass / fail / invalid-RED classification; a JS pilot can complete one
chunk.

### P2 — Dry-run COMPLETED banner lies (confirmed KN-J15)
From a clean external pilot, `run-sprint --dry-run --non-interactive`
prints `branch: factory/sprint-...-dry-run` and `commits: N`, but
`git branch --list 'factory/sprint-*'` shows no branch and no commits
in either repo. This is a §7 silent-green-shaped surface: an operator
who trusts the banner will believe a branch exists. (The good news: the
dry-run IS genuinely side-effect-free, so H-2 is really fixed — the bug
is only the banner text.)

**Ask:** make the dry-run banner state simulated/no-branch honestly (or
suppress the branch/commit lines under dry-run). Add a test pinning that
dry-run creates no branch and the banner does not claim one.

### P3 — RUN-PROMPT §15 truth-table row/flag mismatch (confirmed KN-J7)
An external operator reading `phase-4.5/RUN-PROMPT.md` §15 cannot
distinguish `--non-interactive` / `--unattended` / `--skip-reconcile`;
the table presents 3 mode columns and folds the flags together. This
was the named BLOCKER and it did bite (had to read KN-J* per-flag).

**Ask:** correct the operator-facing truth-table so each gate flag's
behavior is distinguishable, and reconcile it with the actual
`gate_auto_decide` plumbing.

### P4 — Resume path unusable (KN-J9 / J10 / J11), note only
We deliberately avoided `--resume-from` (dry-run can mutate git J-9;
family guard dropped on resume J-10; documented `--resume-from <path>`
fails at parse J-11). Fresh-per-run was the only safe path. Flagging so
resume is prioritized before you advertise pause/resume to pilots.

## What worked (keep / don't regress)
- The pre-chunk cross-family PRD review caught 8 convergent spec defects
  (cascade state divergence, backwards drop-down API, un-buildable phase
  sequencing, missing meeting-status field, serverless connection
  exhaustion, EOS-canon errors) BEFORE chunking. This is the framework's
  highest-value moment; preserve it as a first-class step, not an
  implicit side effect of the planner gate.
- The per-pilot overlay (`bin/run-sprint`) wired a brand-new external
  repo with only path edits. Good.

## Deliverable
A short triage note (accept / defer per finding) + PRs on author-branches
(`factory/` | `codex/` | `claude/`) per `AGENTS.md`, with the P1 adapter
test-covered. Keep convention/spec changes off the feature branches.
Do not land on `main` without cross-family review (invariant #1).

## Self-assessment follow-on

The EOS pilot agent hand-drafted a 4-section self-assessment
(`DOGFOOD-SELF-ASSESSMENT.md` in the pilot repo). It is mirrored
here as `phase-4.5/EXTERNAL-DOGFOOD-SELF-ASSESSMENT.md`.

Headline verdict (operator must read this before scoping chunk-14):

> The runner fired 0 real model calls in the pilot. Of the 9 §11
> steps: 2 HAND (PRD review, chunks.json), 1 RUNNER (auto-accept),
> 1 partial (telemetry rows present but unjoined), **5 GAP**
> (plan, plan-review, inner loop, chunk commit, post-chunk
> adversarial review). The runner's contribution to the actual
> deliverable: 0 lines produced, 0 lines reviewed.

The framework-affecting findings are now wired into
`phase-4.5/KNOWN-ISSUES.md` KN-A-1..KN-A-4:

- KN-A-1 — runner fires 0 real model calls; closeout cannot
  advertise "runner as builder" until a live run is recorded.
- KN-A-2 — telemetry/banner `run_id` mismatch; the audit trail
  cannot join the banner. **Chunk-14 owns.**
- KN-A-3 — post-chunk adversarial code review never ran (author
  == validator). **Chunk-15 owns** (promoted from previous
  "Phase 4.7" idea to first-class runner step).
- KN-A-4 — live mode = 4-precondition conjunction (signing key,
  contract reader, toolchain, prior dry-run). **Chunk-14 +
  chunk-15 own.**

**Implication for chunk-14 scope expansion:** the minimum set
originally J-7 BLK + J-8/9/10/11/15/16 HIGH now includes
KN-A-2 (telemetry join) and KN-A-4 (live-path preconditions
checklist) as first-class items.

**Implication for chunk-15 scope expansion:** pre-chunk cross-
family PRD review is now paired with **post-chunk adversarial
code review** (the EOS GAP step 8). The chunk-15 fresh-agent
prompt has been rescoped accordingly.
