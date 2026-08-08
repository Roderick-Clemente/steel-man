# Operating rules — multi-agent, multi-machine

Rules learned the hard way running this repo across several agents (Claude Code,
Factory `droid`, Codex) and more than one machine. `AGENTS.md` covers repo
conventions (the public-repo fence, branch-by-author, commits-as-baton). This file
covers the *operating discipline* on top of that — the things that bit us in Phase 0
and the canary run, written down so the next session starts with them instead of
rediscovering them.

Read this alongside [`wake-loop.md`](./wake-loop.md), which describes the
orchestrator/worker pattern these rules assume.

## 1. Commits are the only cross-machine channel

There is no shared working tree across machines, and there is no shared session
state — Factory sessions are machine-scoped (`hostId` in `~/.factory/host.json`
stamps each transcript). The **git repo on the dev remote is the entire coordination
surface** between machines.

Consequences:

- **`STEER.md` is machine-local.** It is gitignored, so it never travels. A steering
  note written on one machine is invisible to a droid on another. Don't rely on it for
  cross-machine coordination — use commit messages, branch names, and tracked docs
  like this one.
- **Untracked files don't travel.** If a rule, tool, or protocol needs to reach
  another machine, it has to be *committed*. That is why this file and `wake-loop.md`
  are tracked and `STEER.md` is not.
- **Don't try to sync `~/.factory`.** The session store is a shared-surface leak
  (Probe 3), not a coordination channel. Reaching another machine's transcripts is the
  isolation bug the reference guard exists to close — do not build on it.

## 2. Capture before you change

Before upgrading, wiping, or reconfiguring any environment that is itself *evidence*,
commit the evidence first. A control environment is only as durable as what's in git.

- The 0.180.0 canary box is a **known-good baseline** — it is the only machine that can
  prove the `hooks.json` regression (works at 0.180 → silent at 0.186). Its value
  evaporates the moment it's upgraded, unless the evidence is committed. It is
  (`phase-0/evidence/canary-0.180.0/`).
- `droid update -v <version>` pins to a specific version, so an upgrade is reversible —
  but reversible ≠ free. Capture, then upgrade, then re-measure. Never upgrade-first.

## 3. Version-stamp every finding

A version-less result cannot be rechecked, and CLI behavior is not stable across patch
releases. Two axes of drift were observed between `droid` 0.180 and 0.186 alone
(`hooks.json` loader, `usage.factory_credits` envelope shape). So:

- Every claim that depends on CLI behavior carries the version it was observed under.
- Capture the **field name** you relied on, not just the value — field names drift too
  (`factory_credits` was present at 0.186, absent at 0.180).
- A CLI upgrade **invalidates the go/no-go** until the probes are re-run. The verdict is
  scoped to a version, not forever.

## 4. Two numbering schemes — never collapse them

A finding has two stable identifiers with different sources of truth. They disagree,
and that is correct:

| Scheme | Canonical source | Example: `.factory/hooks.json` |
|---|---|---|
| **Repo defect-N** | `phase-0/GO-NO-GO.md`, `droid-wiki/background/open-questions.md` | **#2** |
| **GitHub issue-N** | the upstream Factory-AI/factory tracker | **#3** |

Do not renumber either to match the other. When referring to a defect, say *which
scheme*. This trap has already caused one round of confusion.

## 5. No unsupervised building — the gate is the point

This project exists to disprove unsupervised single-agent building. So the worker
never crosses from probing/planning into building without an explicit human go and a
named unit of work.

- **No "Tier B" / real GROK→CHUNK→EXECUTE work without a named pilot chunk** from the
  human. "Pick something and go" is the anti-pattern.
- The worker records **BLOCKED-with-evidence** rather than retry-looping or
  building around a blocker.
- Every run has an explicit **STOP** condition, stated up front.

## 6. Enforcement is not calibration — prove it with a weak executor

The single most important methodological rule the canary taught us: **a boundary held
by a well-behaved model is not enforced.** At `--auto low`, `opus-5` refused a
locked-test bypass; at `--auto medium`, `gpt-5.4-mini` ran the same bypass and reported
success. The hook never fired in either case — once because the model declined, once
because the matcher missed the tool.

- Never conclude "the guard works" from a run where a strong model simply behaved.
  Re-run with the **cheapest cross-family executor available** and try to break it.
- H3 (role-tiered cheaper executors) is a *design goal*, so weak-model behavior is the
  case that matters, not the exception.
- Name-based matchers (`Edit|Create|ApplyPatch`) are necessary but not sufficient — a
  shell write (`Execute` + `sed -i`, `python -c`, `>`, `tee`) walks through any
  tool-name list. The fix is a guard that **inspects reality** (the command, or the
  post-tool file state), not the tool name.

## 7. Assert on reality, never on exit code

The platform's default failure mode is **silent green** — it reports success while
doing nothing, being blocked, or being misconfigured (four independent sightings in
Phase 0). Therefore:

- Never trust `exit 0` or a plausible result string as proof work happened.
- Assert on the hook log, per-tool `is_error`, file SHAs, and captured output — the
  actual artifacts of what occurred.
- A finding is "reproducible from a clean shell" or it is not evidence.

## 8. When scope shifts, name it — don't absorb it silently

During Phase 3.2 (evidence provider), the orchestration gap was discovered: the
process was ad hoc, run by an AI agent manually executing commands instead of by
a scripted pipeline. That gap was a framework-level concern (PRD Act 2:
automation), not a 3.2-specific concern (externalize the evidence tier). It got
built inside 3.2 because it emerged naturally, but it should have been its own
loop with its own prompt.

The rule when scope shifts mid-phase:

1. **Name it.** If the work you're doing is not what the phase's RUN-PROMPT
   scoped, say so explicitly. Don't silently absorb it.
2. **Decide: absorb or push out.** Small, in-scope additions that emerge
   naturally can be absorbed (log in ASSUMPTIONS.md). Larger scope shifts that
   are really a different concern should be **pushed out** to their own loop /
   prompt / phase — record it as a follow-on, finish the current scope, then
   give it the full treatment separately.
3. **Record the decision.** Either way, the scope shift and the decision go in
   the phase's ASSUMPTIONS.md or KNOWN-ISSUES.md. A scope shift that nobody
   recorded is the same defect as a silent green: it happened, but there's no
   evidence it was considered.

The temptation is to keep building because you're already in the flow. The
discipline is to stop, name the shift, and decide whether it belongs here or
in its own loop. Most scope shifts want their own loop.
