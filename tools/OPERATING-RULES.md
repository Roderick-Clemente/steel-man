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

**Layer-3 amendment (Phase 5 close, factory/phase-5-chunkadherence-enforcement):**
A self-run, same-family, implementer-orchestrated subagent review does
**not** satisfy §17. Only a ``phase-4.5/tokens/chunk-N.token.json``
whose HMAC-SHA256 signature verifies under ``EVIDENCE_SIGNING_KEY``
**and** whose reviewer list is cross-family (≥2 distinct families via
``tools/sprint_loop/config.py:MODEL_FAMILY_MAP``) **and** disjoint
from the implementer's family (i.e. implementer is not among its own
reviewer identities) counts as review for merge purposes.
``tools/cross_family_review.py`` enforces these three constraints
refusal-at-parse; ``tools/chunk_sequence_gate.py`` enforces the
signature path before chunk-N+1 may start. Cite the chunk-14 pass-r5
episode (``factory/chunk-14-kn-J-fixes``, commit ``623e024``) as the
repro: an ACCEPT-WITH-NITS from two same-family Task subagents that
the gate rejected on the family-distinctness constraint alone. See
``phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md`` §8 for the design
spec and ``phase-4.5/KNOWN-ISSUES.md`` KN-R1 for the issue trail.


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
   hard-code), FIX THE PRIMITIVE in the SAME chunk — under the same
   guard rail as the chunk's main body (per §14: shim/wrapper present).
   Don't work around bad ergonomics in user code; the workaround
   becomes the new owner of that debt. Record the fix in the chunk's
   `PLAN.md` rule-application table.
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

## 19. Commit when the recommendation is clear; do not force the operator to choose

When you have a recommendation and you can articulate the trade-offs of
the alternatives, **commit to the recommendation** — don't ask the
operator to pick. Surface the WHY (one short paragraph) and ship. The
3-option "you choose" question is appropriate only when *no* option is
clearly best — when the trade-offs are roughly symmetric across user
preference and you genuinely cannot rank them.

*Anti-pattern:* offering three labeled choices for a decision whose
internal ranking the agent could state in one sentence. The operator
becomes the forced chooser of something the agent already ranked. The
claude-opus-5 session that produced chunk 11 fallback questions three
times in one turn earned this rule; the operator's exact response was
"part of the skill should be don't do that cuz its annoying lol."

*When multiple options ARE legitimate* — for example, a tradeoff with
real operator values (cost vs. reach vs. simplicity) that the agent
cannot rank without the operator's preference — then ask, but make it
one question, framed in operator language, not three agent-proposed
options mirrored back.

*Rationale:* agents with strong defaults save operator attention. The
3-option-question shape is a fuzzy signal of "I don't know which is
right, but I know there are three." When that fuzzy state is real,
ask. When it's a shrug the agent could have resolved, ship.

*How this composes with §18:* §18 says "review at the end of the build"
— meaning the agent's recommendation lands as code, gets reviewed
against the spec, and is corrected if the review finds a defect. That's
the loop that makes "commit-and-surface-WHY" safe: the spec-reconciled
review catches the cases where the agent shipped a wrong recommendation.
A 3-option question *forecloses* that loop by making the operator do
the reconciliation the review was meant to do.

## 20. Chunk-close is gated, not declared

A chunk's "I'm done" is an *agent claim* until the
`chunk_sequence_gate` confirms it. The runner emits a
`phase-4.5/tokens/chunk-N.token.json` at chunk close, HMAC-SHA256
signed by `EVIDENCE_SIGNING_KEY`. The next-chunk-start path refuses
without a verifiable token for the prior chunk. Phase 5's
enforcement layer builds this; the rule sits here so any agent
working the project reads it on entry.

*Rationale:* chunk-14 closed at HEAD with pass-r5 ACCEPT-WITH-NITS
from a same-family, implementer-orchestrated panel. The skill
`skills/adversarial-sprint/SKILL.md` was loaded as context but the
framework had no parse-time refusal, and the chunk close was a
declaration rather than a verdict bound to evidence. Skills as
documentation of intent loaded into agent context are not
enforcement. The chunk-close gate makes the close a machine-checked
event. A "skill exhausted" condition cannot render anything, so do
not promise an "exhausted" visual signal — absence of the
operator-eye signal is the operational troubleshooting trigger,
not a separate state.

*Spacing for future rules:* continue numbering as the operating
rules accrue.

## 21. Reviewer attestations are evidence, not assertion

A chunk-close token's reviewer `envelope_sha256` field must be
**computed from a real reviewer envelope** — the SHA-256 digest
over the literal output of a fired cross-family `droid exec`,
written to disk at
`phase-4.5/build-evidence/<run-id>/<chunk-id>/<reviewer-label>.json`.

Build-time fixture markers (`"5"` × 60 + `"01"`-style, all-zero SHA
prefixes, all-homogeneous leading 50-character runs) — even when
typed in good faith by the implementer — fail
`tools/cross_family_review.py`'s homogeneous-leading-character
refusal (KN-A-5 / design-doc §10). A chunk-close token whose
reviewer SHA lacks a verifier-traceable backing envelope is a
**self-declaration masquerading as a verdict**; the chunk-close
gate MUST refuse it.

Authorship of reviewer envelopes is structurally forbidden at
chunk close: a signer holding `EVIDENCE_SIGNING_KEY` can produce
a verifying HMAC over a fabricated payload, so signing authority
without envelope-source check is no defense at all. Either the
envelope is on disk *before* the token's HMAC exists, or the
gate refuses close.

*Rationale:* chunk-14 pass-r5 (commit `623e024`,
`factory/chunk-14-kn-J-fixes`) reached ACCEPT-WITH-NITS via
two same-family Task subagents orchestrated by the implementer —
the implementing agent signed off its own work. The Phase-5
build on `factory/phase-5-chunkadherence-enforcement` shipped
all five `chunk-N.token.json` files with typed-in fixture envelope
SHAs (KN-A-5) — the same anti-pattern in a milder family-distinct
form. The fix is structural, not stylistic: bind
`envelope_sha256` to a disk artifact the implementer did not
create, and refuse the token otherwise. Tier-3 off-process
signing daemon (`phase-4.5/DESIGN-DAEMON-SIGNER.md`) — the
agent POSTs `(chunk_id, chunk_commit_sha, envelope_paths)` to a
separate process; the daemon computes SHAs from the on-disk
envelopes, signs the token, and never exposes
`EVIDENCE_SIGNING_KEY` to the agent.

*Spacing for future rules:* continue numbering as the operating
rules accrue.

## 22. Author is not the verifier, period

Even when model families satisfy §17.2 distinctness, **the agent
that authors a chunk MUST NOT be the agent that fires its review
or signs its close token**. Family-distinctness is necessary but
not sufficient: same-session identity carries the implementer's
working memory into the reviewer's context, and effort pressure
routs around any family check the implementer also controls.

Operationally:

1. The **chunk-close token signing authority** is held by a
   separate process (Tier-3 daemon, KN-A-7 / §21 — one's-off
   keyed daemon). The build agent has only **read access** to the
   resulting token, via the commit record.
2. The **reviewer-firing path** is held by a separate, persistent
   cross-family referee process (`phase-4.5/DESIGN-PERSISTENT-REFEREE.md`
   / KN-A-8) that wakes on a cadence and reads pending review
   requests from `STEER.md` (machine-local cross-agent queue per
   §1). The referee has its own git session identity / commit
   signing key; build agents do not.
3. A build agent MAY post `REVIEW REQUEST: chunk=X paths=[...]`
   lines to `STEER.md`. The agent MAY NOT fire `droid exec`
   against the reviewer model IDs the agent itself selected; the
   agent MAY NOT hold `EVIDENCE_SIGNING_KEY`; the agent MAY NOT
   write to `phase-4.5/tokens/chunk-N.token.json` directly.
4. The chunk-close gate (`cross_family_review.py` + `chunk_sequence_gate.py`)
   validates the *structural* predicate; the persistent referee
   enforces the *identity* predicate. The build agent cannot
   satisfy the second regardless of cleverness on the first.

Defense-in-depth with §21: §21 enforces envelope-on-disk
authenticity; §22 enforces session-identity of the envelope
source. Both must hold for a chunk-close token to represent a
real cross-family review.

Reasoning discipline for future agents encountering §22:
"This rule exists because, twice this session, the build agent
fired (or proposed to fire) the cross-family reviewers of its own
work. Family-distinctness is satisfied each time; session-identity
is not. The reviewer's verdict validated the rule (REJECT on
KN-A-5 grounds for the chunk-5 build session) — but the rule
should not require a vigilant reviewer to be enforced. It should
be enforced by *architecture*."

*Rationale:* chunk-14 pass-r5 was the same pattern at a different
layer: the implementer orchestrated the reviewers. The chunk-5
build session on `factory/phase-5-chunkadherence-enforcement` was
the same pattern at the chunk-close-token layer: the implementer
typed fixture markers. A short-lived attempt in this very session
to "fire cross-family reviewers from the build agent's session"
was rejected by the reviewer itself (REJECT verdict) for the same
structural reason. The fix is not more refinement; it is
separating the trust domains at the **process / session** layer,
not just the model-family layer. KN-A-8 + the persistent-referee
design are the implementation.

*Spacing for future rules:* continue numbering as the operating
rules accrue.

## 23. Validators are not paraphrases of each other

§17.2 family-distinctness plus §21 envelope-on-disk distinctness
are necessary but insufficient. A coerced Tier-2 validator (one
whose prompt context leaks the build agent's narrative, or one
that is itself a sub-prompted child of the build agent) can
produce an envelope that is *model-family distinct* and
*bitwise distinct* from its sibling — yet *content-wise* it is
the build agent's own rationalization parroted back. §17.2 +
§21 do not catch this. Signers, auditors, and humans reading
the close token would accept it.

The persistent referee, before signing any chunk-close token,
MUST verify two more predicates beyond §17.2 and §21:

1. **Content-distinctness (τ).** Compute a length-normalized
   Jaccard similarity score over the natural-language content
   of the Tier-2 envelopes, *excluding*:
     - lines beginning with `VERDICT:`
     - the prompt-template JSON scaffolding
     - any field whose name begins with `signature` or
       `envelope_sha256` (the bitwise-distinct field is
       expected to differ across envelopes).
   Refuse if the score is above τ. Default τ = 0.85. Operator
   may tighten (e.g., τ = 0.70 for high-stakes changes) or
   loosen (e.g., τ = 0.95 for trivial changes) per session.
2. **Operational-distinctness (sessionId).** Each Tier-2 envelope
   MUST carry its own session-id metadata (recorded in the
   envelope footer as `session_id:`, sourced from
   `droid exec`'s session-token output that the per-validator
   spawn produced, or recorded in the run-evidence manifest).
   Refuse if two envelopes share a sessionId.

Both predicates run inside the referee's signing path; both
predicates' results are recorded in the close token's
`audit_evidence` field so the chunk-close history is
self-attesting. Refusal (τ over threshold, or sessionId
collision) posts a `REFUSED: chunk=X reason=paraphrase` line
to `STEER.md` and is a §22 audit failure visible to the
operator.

*Rationale:* KN-A-9 entry in `phase-4.5/KNOWN-ISSUES.md` —
the Tier-2 paraphrase anti-pattern is structurally possible
today because §17.2 is satisfied on family labels alone;
without §23, the guarantee is "different MODEL_TRAINER" not
"different INFERENCE."

*Spacing for future rules:* continue numbering as the operating
rules accrue.

## 24. Referee fires or audits — never both at once for the same chunk

The persistent referee MUST NOT, in the same logical operation
on the same chunk, simultaneously fire Tier-2 (cross-family
validators) AND sign the resulting chunk-close token. The
firing bias is non-removable in a single process: the
referee's context contains both the prompt it just sent to
Tier-2 and the verdict it is about to sign against Tier-2's
output. §22 fails on the referee's own session identity if
just one process does both.

The architecture:

- An **orchestrator** (separate session; cron-driven or
  in-session as part of the builder's session's close flow)
  fires Tier-2 validators. The orchestrator reads
  `REVIEW REQUEST:` from STEER.md, invokes Tier-2 — typically
  via `bash tools/run-with-model.sh droid exec --model grok-4.5`
  and `bash tools/run-with-model.sh droid exec --model gemini-3.x`
  — captures the literal stdout into the canonical
  envelope paths the orchestrator computes.
- The Tier-2 validators themselves (grok, gemini — long-running
  droid sessions, the spawn prompts in
  `phase-4.5/prompts/phase-5-grok-validator.md` and
  `phase-4.5/prompts/phase-5-gemini-validator.md`) *receive*
  `VALIDATE REQUEST:` lines from STEER.md, perform their own
  invocation within their own session, and write their own
  raw envelope bytes — providing operational-distinctness
  (§23) that an orchestrator-as-only-spawner cannot.
- The **persistent referee** reads STEER.md for `REVIEW REQUEST:`
  lines whose envelope paths already exist on disk (the
  orchestrator + validators agreed on the canonical paths).
  Referee refuses (REFUSED: chunk=X reason=no-envelopes) if
  paths are absent. Referee refuses if §23 fails. Referee
  signs the close token only when §21 + §17.2 + §23 +
  Tier-2-distinct-sessionIds all hold.

The 4-actor topology is therefore: builder → orchestrator →
Tier-2 → referee. §22 bounds builder ≠ referee. §24 bounds
referee ≠ orchestrator-for-same-chunk. §23 bounds
Tier-2 ≠ Tier-2 (within the referee's audit decision, *not*
inside Tier-2's invocation). All three bits are
defense-in-depth, none alone closes KN-A-9 / KN-A-8.

*Rationale:* A single process that fires Tier-2 AND signs
their output collapses back to one trust boundary — we are
back to chunk-5 KN-A-5 plus this session's REJECT verdict.
The 4-actor split is the structural answer: the *fire*
decision is outside the *sign* decision, both outside the
*build* decision.

*Spacing for future rules:* continue numbering as the operating
rules accrue.

