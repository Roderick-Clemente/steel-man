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


## 9. If it's not scripted, it didn't happen

A phase that runs its `droid exec` invocations by manually copy-pasting
commands has no reproducible evidence. The orchestration script must be the
default way reviews are run. A RUN-COMMANDS.md file is documentation for the
script, not a substitute for it. If the script doesn't exist yet, the first
deliverable of the phase is to build it — **bounded to the phase's actual
repeat surface**, not a full panel orchestrator by default.

*Exception:* pure probe spikes (Phase 0-style) may run manually — they are
one-off capability checks, not repeatable loops.

*Rationale:* Phases 1-3 ran manually. The orchestration script was built in
3.2 and partially works. This rule makes "script the loop" the default, not
the retrofit.


## 10. Telemetry rows are written by the script, not by the operator

From adoption forward, multi-invocation phases must emit `runs.jsonl` (and
`findings.jsonl` / `dispositions.jsonl` when applicable) from the
orchestration script as part of each `droid exec` invocation, not appended
manually after the fact. Committed envelopes + auditable reconstruction
recipes (e.g. `gen-telemetry.py`) remain valid evidence for past phases and
disaster recovery. Do not equate "missing live SoR row" with "phase
incomplete" when reconstructable artifacts exist.

*Rationale:* Phase 2 planned telemetry in detail and wrote zero rows. Phase
3's rows were overwritten. Phase 0.5 and Phase 1 used `RUN-LEDGER.md` as
their SoR, which was valid at the time. This rule is forward-looking, not
retroactive.


## 11. Exit criteria are checked, not assumed

A phase's exit criteria must be checked against actual artifacts before the
phase is declared complete. "Invalid RED cases are rejected" means at least
one invalid-RED case was run and rejected — not that the classifier script
exists. "Replayable demo" means a demo artifact exists — not that the wiki
entry is comprehensive. "Local PR creation" means a PR was created — not
that the README says "present the slice."

*Rationale:* Phase 1 declared "invalid RED cases are rejected" as met, but
`valid-red.py` was never run. Phase 3 declared completion without a demo,
baseline comparison, or PR. The exit criteria exist to be checked, not to
be interpreted.


## 12. Unexercised safety paths are named gaps, not phase blockers

If a phase's purpose is to test a mechanism (reconciliation, validation
blocking, retry/re-plan), and the mechanism was not triggered (e.g., the
plan converged on round 1, or all validators returned ACCEPT), the phase is
**complete with a clean null result** — this is valid data per PRD §13 ("a
clean null result is valid data; models disagree at least once is NOT a
success gate"). The unexercised path must be **recorded as a named
gap/follow-on** in the phase's KNOWN-ISSUES.md. Optional adversarial
fixtures may be built as calibration work, but they are **not exit gates**.

*Rationale:* Phase 2's reconciliation loop was never tested under
disagreement. Phase 3's retry path was never exercised. Both are valid
completions with named gaps. Forcing disagreement would incentivize
manufactured findings — the exact failure mode PRD §13 warns against.


## 13. Don't give the executor the answer

The executor prompt must describe the problem and the constraints, not the
implementation. If the prompt contains the exact code change to make, the
executor is a `sed` command, not an independent implementation. The
cheap-executor seat's value (H3) depends on the executor solving the
problem, not applying a known fix.

*Rationale:* Phase 1's executor prompt specified the exact one-line fix.
The executor's 4-turn run confirmed it was mechanical. The H3 cost
hypothesis (cheap executors can do the work) was never genuinely tested
until Phase 4 Track B H3 validated it.


## 14. Use the adapter shim and the model-discipline wrapper

Any script that reads `droid exec` envelope data must go through
`tools/adapters/factory.py` (or the equivalent vendor adapter). Any script
that invokes `droid exec` must go through `tools/run-with-model.sh` (or the
equivalent model-discipline wrapper). Reading raw envelope fields directly
or invoking `DROID_BIN` directly bypasses both the vendor-neutral
abstraction and the model-pinning enforcement, making the code brittle to
platform field-name drift and model-discipline gaps.

*Rationale:* `orchestrate-review.py` cited both the adapter and
`run-with-model.sh` in its docstring but bypassed both in the
implementation body. When a docstring cites a shim/wrapper, the
implementation must call it — or the citation is a §8-style silent scope
lie.


## 15. Assert on reality includes git history

Never judge the success of past phases solely on uncommitted working tree
state. Always inspect git history and the system of record (committed
artifacts, telemetry, lock manifests) before concluding that something was
"never built" or "never ran." A dirty working directory with empty files is
not evidence of failure if the committed state and telemetry tell a
different story.

*Rationale:* The v1 roadmap review concluded that `orchestrate-review.py`
"never successfully ran" based on 0-byte files in a dirty working tree. The
committed telemetry (12 rows, 10 from orchestrated runs with real
decisions) told a different story. This is the exact failure mode §7 warns
about, extended to include git history as part of "reality."


## 16. Demo claims bind to Phase-0-verified capabilities and the command-orchestrated GO decision

No demo beat may claim a capability that Phase 0 did not verify. Act 2
must be honest about the command-orchestrated spine — no Mission cosplay.
"Close the laptop" requires a demonstrated durable runner, not a promise.
Act 3 stays inside the probes that returned PASS.

*Rationale:* The PRD §15 Act 2 is Mission-shaped, but the GO-NO-GO
decision was command-orchestrated. The demo narrative has never been
reconciled with this decision. An audience will catch a Mission demo that
doesn't actually use Missions.


## 17. Capacity envelope: name the next 1-3 deliverables; refuse unbounded foundation programs

A roadmap re-sequencing must name a capacity bound: what can actually be
done next, not an unbounded list of priorities. If the proposed work is a
"foundation program" with no clear exit, it is the same anti-pattern as the
missed exits it criticizes.

*Rationale:* The v1 roadmap review proposed five priorities and six rules
without naming constraints. The cross-family panel flagged this as
recreating the unbounded-backlog pattern.


## 18. Compose existing primitives; build in chunks; fix ergonomic friction inline

A new build's first question is **"what existing primitives compose this?"**
— not "what do I write from scratch." The repo already ships tools whose
authors faced the same problem. A NEW abstraction that ignores them is
either reinvention (rule §14 silent-scope-lie), duplicate directory
(operational debt), or a missed reuse.

Concretely, before writing code:

1. **Compose first.** ``grep -l`` the project for the nearest existing
   primitive (``tools/``, ``phase-1/scripts/``, ``phase-3.2/evidence/``,
   the model-discipline conventions). Plan the build as a flow chart of
   *existing* calls with thin orchestration glue between them.
2. **Build in chunks.** Each commit lands one verifiable unit: state +
   tests, then composes the next layer, then composes the runner. The
   chunk plan is committed BEFORE the chunks fire (`phase-N/PLAN.md` or
   `templates/SPRINT-PLANNING-TEMPLATE.md`-shaped). A "build it all in one
   commit" run is a §17 unbounded-foundation-program in miniature.
3. **Verify at every commit boundary.** Each chunk has a script-runnable
   check that exits 0 against the chunk's specific deliverable
   (``pytest tests/``, ``python3 -m py_compile``, ``yaml.safe_load``,
   ``grep -n``, ``droid`` dry-run). §11 applies per chunk — chunks without
   a check are §1 silent-green shapes.
4. **Fix ergonomic friction inline.** If the chunk surfaces friction in
   an existing primitive (missing flag, wrong default, brittle
   hard-code), FIX THE PRIMITIVE in the SAME chunk — under the
   ``OPERATING-RULES §14 (shim / wrapper present) `` plus inline. Don't
   work around bad ergonomics in user code; the workaround becomes the
   new owner of that debt. Record the fix in the chunk's `PLAN.md` rule-
   application table.
5. **Run the adversarial review at the end of the build.** A build
   without a structural review against the PRD §5 acceptance criteria
   (§5.2 … §5.8 + §11) is a "I read it and it looks right" hand-wave.
   Use the cross-family review harness the project already ships
   (``tools/orchestrate-review.py``, silence-green guarding per §7) —
   record findings + dispositions in ``findings.jsonl``.
6. **Distill into a reusable asset.** After the build lands, scan the
   prompts/methodology used and ask: *would a future agent on a different
   task need to be told this?* If yes, distill the principle into either
   a new rule in this file (rules that ALL agents see on entry), a new
   Skill (skills agents invoke explicitly), or a new section in the
   PRD/PLANS. The principle is reusable when its omission causes the
   same defect elsewhere.

*Rationale:* "Use what exists" + "build small + verify" + "fix the friction
now" + "review against the spec" + "distill the lesson" were each
earnestly given in writing across multiple RUN-PROMPTs but never made
default. The result: every new build re-litigated the same scaffolding
questions, occasionally re-implemented something the project already
shipped, and the principles didn't propagate. A standing rule reads on
every agent entry — a prompt does not.

