# Design: role-split skill, operator signals, and the convergence readout

Three changes to the human-facing loop, bundled because they share one
motivation: **the operator is a participant in this system, and right now the
system tells them almost nothing while it runs.**

Unlike most of Phase 5, this design did not come from a probe or a review round.
It came from a **live run** — the first one — and from the operator noticing
something the panel did not.

## 0. One-line summary

Split the single skill into `PROTOCOL` + `BUILDER` + `REFEREE` so the referee
stops reading builder guidance; emit a small fixed emoji vocabulary at startup
and at every state transition so a scrolling log is readable at a glance; and
replace the advisory round-3 escalation with a **mechanical convergence readout**
computed from finding locations, so "should I run another round?" is answered
with data instead of instinct.

## 1. Motivating evidence (live run, 2026-08-12)

A real plan — a DAO refactor of the pilot — went through **five review rounds**.
Each round produced findings; each round the plan was revised. After round four
or five the operator noticed something felt off, asked whether the plan could be
scoped down, and it was split into at least two pieces.

Three facts about that run, stated precisely because they matter more than the
outcome:

1. **The panel never raised scope.** Five rounds, multiple families, and no
   reviewer said "this plan is too big." Each round answered *"what is wrong
   with this plan"* — competently. None asked *"should this plan exist at this
   size."*
2. **The human caught it, not the framework.** This is not a story about the
   system preventing a mistake. It is a story about the system converging on the
   wrong question four times while a human eventually broke the loop.
3. **The escalate-after-3 rule existed and was overridden.** The operator judged
   it "seemed close" and ran more rounds. That judgment is defensible — the cost
   was roughly two rounds and was reported as cheap — but *"seemed close"* is
   precisely the near-miss bias the rule exists to counter. Each round feels like
   convergence, so you run one more.

**n=1.** One plan, one operator, one session. This is an existence proof that the
gap is real, not a measurement of how often it bites. Treat every claim below as
a design response to a single observed failure.

Corroborating shape, independently recorded: the Phase 5.1 plan cycles ran v1
sign-authority → v2 HMAC-verify → v3 schema-contract. Three rounds, three
*unrelated* blocker areas. Same signature as the DAO run.

## 2. Change A — split the skill, share the contract

### Problem

One skill file serves both the builder and the referee. Invariant #2 says the
validator sees the spec, the diff, and test evidence — **never the author's
reasoning**. A shared skill file is a shared frame: the referee loads guidance
written to steer the builder. That is mild context contamination sitting inside
the mechanism whose entire job is to prevent it.

### Non-solution

Two free-standing skill files. They drift. This repo has already paid for that
once: a skill body and its `.cursor/rules` mirror diverged and left `main` red
with two failing drift tests.

### Design

```
skills/adversarial-sprint/
  PROTOCOL.md    single source of truth: verdict vocabulary, finding schema,
                 emoji legend, evidence format, round/gate semantics
  BUILDER.md     role instructions for the building agent; includes PROTOCOL
  REFEREE.md     role instructions for the reviewing agent; includes PROTOCOL
```

One contract, two entry points. Anything both roles must agree on lives in
`PROTOCOL.md` and is referenced, never restated. Anything role-specific lives in
exactly one of the two and is never visible to the other.

**Drift guard:** the existing mirror-drift test pattern extends to assert that
neither `BUILDER.md` nor `REFEREE.md` restates a `PROTOCOL.md` section rather
than including it.

## 3. Change B — operator signals

### Scope, stated up front

**Emoji are for the operator's eyes. They are never load-bearing for the
machine.** The HMAC token and the sequence gate are the enforcement; a symbol in
a log is not and must never become one. Nothing in the runner may parse them.

**Emoji never appear in identifiers** — not in skill names, model ids, branch
names, or file names. That is not a style preference: an emoji in the skill name
broke skill matching in production during its first week.

### Runtime-agnostic by design

This is the part that matters beyond ergonomics. The protocol orchestrates work
across **model families and across vendor runtimes** — Claude Code skills,
Factory droid, Cursor rules, Codex. Each has its own log format, its own
verbosity, its own idea of what a session looks like.

A conforming runtime emits the **same vocabulary regardless of vendor**, so an
operator watching any of them sees one signal language. This is what makes a
mixed-runtime run legible: you should not have to know whose CLI is scrolling
past to know what just happened.

`PROTOCOL.md` is therefore not "shared text between two skill files." It is a
**portable operator-signal specification**, implementable by any agent runtime,
and the role files are its first two consumers.

### The conformance mark

**🐺 — emitted once at session start by any agent running this protocol**, before
the role marker.

It answers a question no vendor log answers: *is this agent running the
adversarial-sprint protocol at all, or is it just a model in a terminal?* In a
mixed-runtime session that distinction is otherwise invisible.

```
🐺 adversarial-sprint protocol v1 · runtime: droid · model: grok-4.5
⚖️ referee ready
```

### Legend

Small on purpose. If everything carries a symbol, nothing signals.

| Symbol | Meaning |
|---|---|
| 🐺 | **protocol conformance** — emitted once at session start, any runtime |
| 🔨 | builder speaking |
| ⚖️ | referee speaking |
| 🔍 | review round starting (with round number) |
| ✅ | ACCEPT |
| ⚠️ | ACCEPT-WITH-NITS |
| ⛔ | REJECT |
| 🟢🟡🔴 | convergence: narrowing / mixed / dispersing (§4) |
| 🛑 | gate refused — run halted |

Emitted at **startup** (so the operator can confirm which protocol and which role
loaded) and at **every state transition** (so a scrolling log is readable without
being read).

### Portability constraints

Because this crosses runtimes, the vocabulary has to survive environments that
handle unicode badly:

- **Every symbol is followed by its plain-text meaning**, always. `⛔ REJECT`,
  never a bare `⛔`. A runtime that strips emoji loses decoration, never meaning.
- **No emoji is ever parsed** — not by the runner, not by a gate, not by a test.
  Grep-asserted. If a symbol failing to render can change a verdict, the design
  is wrong.
- **No emoji in identifiers**, per the production incident above.
- **No ZWJ sequences or skin-tone modifiers.** Single code points only; composed
  emoji break inconsistently across terminals and log shippers.

## 4. Change C — the convergence readout

### Problem

The round-3 escalation rule asks the operator a question they have no data to
answer. "Are we converging?" was answered from feel, and the feel was wrong for
two rounds.

### Insight

Convergence is mechanically observable from data already emitted. It is not
*how many* findings a round produces — it is **where they land**.

- Successive rounds hitting the **same sections**, narrowing → converging.
  Another round is likely to finish it.
- Successive rounds hitting **different sections** each time → the plan is not
  nearly-done, it is being *surveyed*. Breadth of defect is a scope signal.

The DAO run is the second shape. So is Phase 5.1.

### Design

At every round ≥ 2, compute from the `location` field the finding schema already
requires:

- distinct sections cited this round
- overlap with prior rounds
- cumulative distinct sections across all rounds

Render before asking whether to continue:

```
🔍 Round 3 — convergence readout
   r1: §4 auth-model, §7 storage
   r2: §11 migration
   r3: §2 scope, §9 rollback
   5 distinct sections across 3 rounds, 0 repeats.
🔴 DISPERSING — findings are spreading, not narrowing. Plans that disperse
   across rounds are usually mis-scoped rather than nearly-done.
   Continue to round 4? State why it will converge: ________
```

Classification (deliberately crude; tune with data, not taste):

- 🟢 **narrowing** — this round's sections are a subset of prior rounds'
- 🟡 **mixed** — some overlap, some new
- 🔴 **dispersing** — no overlap with any prior round, and cumulative distinct
  sections ≥ rounds + 2

### Not a lockout

The operator is never blocked. The round-3 rule stays advisory in *outcome* and
becomes mandatory in *articulation*: continuing past 3 requires one written line
saying why round N+1 will converge when 1..N did not. That sentence is the whole
mechanism — it forces the question the operator eventually asked anyway
(*is the plan wrong, or is my review of it wrong?*), and it lands in the ledger.

### Why this is the right tier

The project's strongest recorded finding is that the deterministic tier outranks
the panel: in Phase 3.1 the standalone gate caught the planted defect every run
while the panel split. This is another instance. Dispersion is a mechanical check
over data already recorded, costing zero tokens, catching a class the panel
demonstrably missed five times in a row.

## 5. Exit criteria

- [ ] `PROTOCOL.md` exists; `BUILDER.md` and `REFEREE.md` include it and restate
      none of it; drift test asserts this
- [ ] A referee run loads `REFEREE.md` and demonstrably does **not** load builder
      guidance (assert on the loaded context, not on intent)
- [ ] All eight legend symbols emitted at startup and at every transition, in a
      live run, captured in a transcript
- [ ] No emoji in any identifier — asserted by test
- [ ] Nothing in the runner parses an emoji — asserted by grep test
- [ ] Convergence readout renders for rounds ≥ 2 with correct classification on
      three fixtures: narrowing, mixed, dispersing
- [ ] Continuing past round 3 writes the operator's stated justification to the
      ledger; absence of a justification is itself recorded
- [ ] Replay of the DAO run's five rounds through the readout classifies 🔴 at or
      before round 3

That last one is the real test. If it does not go red by round 3 on the run that
motivated it, the heuristic is wrong and should be reworked before shipping.

## 6. Open questions for the panel

1. **Is `location` reliable enough to key on?** The readout is only as good as
   reviewers citing sections consistently. If location strings are free-form,
   dispersion is noise. May need a controlled vocabulary, or normalisation.
2. **Does the crude classifier survive contact?** Thresholds are guessed from
   n=1. Should ship logging-only for several plans before it renders a verdict.
3. **Should the readout be shown to reviewers, or operator-only?** Showing it
   risks anchoring — a reviewer told "this looks mis-scoped" may go hunting for
   scope findings. **Recommend operator-only** until measured.
4. **Does `PROTOCOL.md` leak builder framing into the referee anyway?** It has to
   carry shared vocabulary, and vocabulary is framing. Worth a read specifically
   for that.
5. **Is scope a reviewer responsibility at all?** An alternative to the readout:
   give the referee an explicit mandate to answer "should this plan exist at this
   size" as a first-class verdict, not just "what is wrong with it." That is a
   prompt change rather than a mechanism, and it is cheaper — but it relies on
   the panel, which is the tier that just failed five times.

## 7. What this does not do

- Does not make emoji enforcing. They stay decorative-but-useful.
- Does not block the operator. No lockout, by explicit request.
- Does not claim the framework caught the DAO scope problem. **It did not.** A
  human did, late, having overridden the rule that existed to prompt them earlier.
- Does not establish a rate. n=1.
