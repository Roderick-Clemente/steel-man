# Referee prompt — DESIGN-ROLE-SPLIT-AND-SIGNALS (v2, post model-id-in-banner)

Fire against a **non-Claude family** (the design was authored by a Claude-family
model; §17.2 forbids same-family review). Grok, Gemini, GPT and Kimi are all
legal seats here.

**Invocation must include `Execute` in the tool allowlist.** In Phase 1 round 1 a
reviewer refused to render judgment because `Execute` was absent and it could not
read the artifact — a wasted frontier call.

```sh
droid exec --model <model-id> \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --output-format stream-json \
  --cwd <repo-root> \
  -f phase-5/prompts/design-review-role-split-v2.md
```

---

## PROMPT BEGINS

You are reviewing a design document in this repository. You did not write it and
you have not seen the discussion that produced it. Judge it on its own merits and
against what is actually on disk.

**Artifact under review:** `phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md`
(branch `factory/role-split-and-signals`, tip `945871f`)

**Grounding — read these before judging, and cite them:**

- `AGENTS.md` — conventions binding every agent in this repo
- `tools/OPERATING-RULES.md` — especially §7 (assert on reality), §9 (not
  scripted = didn't happen), §11 (exit criteria are checked, not assumed)
- `PRD.md` §4 and §17.2 — family separation and model discipline
- `PRD.md` §5.3 — the review round cap this design proposes to change
- `skills/` — the current single-skill layout the design proposes to split
- `phase-1/KNOWN-ISSUES.md` — the finding schema and severity vocabulary to reuse
- `tools/sprint_loop/droid.py` — the `_resolved_provider_and_family` and
  `recheck_family_guard_post_resolution` code the banner cross-check cites
- `tools/plan-lint.py` — the deterministic pre-review tier already in the repo;
  does the convergence readout overlap with it, compose with it, or duplicate it?

**What the design proposes**, in brief: split one skill into `PROTOCOL` +
`BUILDER` + `REFEREE` so the referee stops reading builder guidance; emit a small
fixed emoji vocabulary at startup and at every state transition so a scrolling
log is readable at a glance; require the model ID in the startup banner, sourced
from the invocation (not self-report), with a cross-check against the resolved
model from the envelope; and replace the advisory round-3 escalation with a
**mechanical convergence readout** computed from finding locations, so "should I
run another round?" is answered with data instead of instinct.

**Its stated evidence is n=1** — a single live run in which a plan went five
review rounds, the panel never raised scope, and the human caught it. A second
incident (2026-08-13) motivated the model-id-in-banner addition: the operator
discovered days later from commit history that the executor seat was filled by
`claude-haiku-4-5` rather than the intended tier.

### Judge these specifically

1. **Is the n=1 evidence load-bearing beyond what it can carry?** The document
   claims to state this limit honestly. Verify that every conclusion actually
   respects it. This repo has a documented history of verdicts outrunning sample
   size (H-CI at N=3 with a sign flip, H3 at N=1) — check for a recurrence.
2. **Does the convergence heuristic survive scrutiny?** It keys on a `location`
   field. Confirm that field exists in the finding schema, is populated in
   recorded findings, and is consistent enough to key on. If locations are
   free-form prose, the readout is noise. Say so. Check `phase-4/` and
   `phase-3.2/reviews/` for actual finding JSON to see what `location` looks like
   in practice.
3. **Is the thresholding defensible or invented?** "cumulative distinct sections
   ≥ rounds + 2" is guessed. Attack it. Is there any basis for the +2, or is it
   round-number-shaped? What happens at round 2 (threshold = 4 sections, which is
   a lot for a 2-round plan)?
4. **Does the split actually satisfy invariant #2?** The claim is that a shared
   skill file leaks author framing to the reviewer. Does `PROTOCOL.md` — which
   must carry shared vocabulary — reintroduce the same leak? Vocabulary is
   framing. Read the current `skills/adversarial-sprint/SKILL.md` and identify
   what would go in PROTOCOL.md vs BUILDER.md vs REFEREE.md. Does the split
   actually separate anything, or does PROTOCOL.md carry most of the current
   body?
5. **Is the model-id-in-banner cross-check sound?** The design says the banner
   cross-checks requested vs resolved, citing `_resolved_provider_and_family`.
   Read that code. Does it actually expose a resolved model ID that can be
   compared? The family guard compares family strings; does the model-id check
   have the same plumbing available, or is it assuming a field that doesn't
   exist yet?
6. **Are the emoji constraints sufficient?** The design says emoji are never
   parsed and never in identifiers. Check whether anything already in the repo
   violates that, and whether the proposed grep-test would actually catch it.
   The project already had one production incident from emoji in skill names.
7. **Is the "not a lockout" design strong enough?** The operator overrode the
   existing escalate-after-3 rule on a "seemed close" judgment. The replacement
   is a written justification line. Is that a stronger or weaker constraint than
   what was already overridden? If it is weaker, say so.
8. **Is this the right tier for scope judgment?** The design argues a
   deterministic check beats the panel for this class, citing Phase 3.1. In 3.1
   the deterministic gate caught an ordering dependency in a test — squarely
   within the gate's coverage domain. Is scope judgment in the same category, or
   is it genuinely a judgment call that the panel is the right tier for (open
   question 5, which the design raises but does not answer)?
9. **Does the design conflict with anything already committed in `phase-5/`?**
   Check for overlap with the chunk-close gate infrastructure, the plan-lint, the
   persistent referee, or the §20/§22/§23/§24 amendments.

### Also worth attacking

- Does this add mechanism where a prompt change would do? Open question 5 raises
  the cheaper alternative (give the referee an explicit scope mandate) and then
  does not take it. Is that the wrong call?
- Is the operator-only display decision right, or is withholding the readout from
  reviewers protecting them from useful context?
- The design says emoji are "decorative-but-useful" and "never load-bearing."
  Does the design's own attention budget match that claim? If 40% of the document
  is about emoji and 1% is about the `location` field reliability, is the
  priority right?
- The model-id-in-banner was added after the original design was written. Does
  it integrate cleanly, or does it feel bolted on? Does the motivating incident
  (misconfigured executor, discovered days later) actually justify the banner
  mechanism, or would a simpler fix (log the model at invocation start, which
  §17.1 already requires) suffice?

### Output format

Emit one JSON object per finding, in fenced blocks, using the schema this repo
already uses:

```json
{
  "finding_id": "F-DRS2-001",
  "severity": "blocker|high|medium|low",
  "category": "factual-error|internal-inconsistency|completeness-gap|scope-creep|missing-reference|unsupported-claim",
  "location": "file:section",
  "description": "",
  "evidence": "verbatim quote or command output",
  "recommendation": ""
}
```

Then a short table of what checks out, then exactly one verdict:

**ACCEPT** · **ACCEPT-WITH-NITS** · **REJECT**

Ground every finding in something you actually read. Do not accept the document's
claims about the repository — verify them. If a claim about on-disk state is
wrong, that is a finding, and it is the most valuable kind you can produce here.

## PROMPT ENDS
