# Referee prompt — DESIGN-ROLE-SPLIT-AND-SIGNALS

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
  -f phase-5/prompts/design-review-role-split.md
```

---

## PROMPT BEGINS

You are reviewing a design document in this repository. You did not write it and
you have not seen the discussion that produced it. Judge it on its own merits and
against what is actually on disk.

**Artifact under review:** `phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md`
(branch `factory/role-split-and-signals`)

**Grounding — read these before judging, and cite them:**

- `AGENTS.md` — conventions binding every agent in this repo
- `tools/OPERATING-RULES.md` — especially §7 (assert on reality), §9 (not
  scripted = didn't happen), §11 (exit criteria are checked, not assumed)
- `PRD.md` §4 and §17.2 — family separation and model discipline
- `PRD.md` §5.3 — the review round cap this design proposes to change
- `skills/` — the current single-skill layout the design proposes to split
- `phase-1/KNOWN-ISSUES.md` — the finding schema and severity vocabulary to reuse

**What the design proposes**, in brief: split one skill into `PROTOCOL` +
`BUILDER` + `REFEREE`; define a runtime-agnostic operator signal vocabulary; and
add a mechanical "convergence readout" that classifies whether review rounds are
narrowing or dispersing, based on where findings land.

**Its stated evidence is n=1** — a single live run in which a plan went five
review rounds, the panel never raised scope, and the human caught it.

### Judge these specifically

1. **Is the n=1 evidence load-bearing beyond what it can carry?** The document
   claims to state this limit honestly. Verify that every conclusion actually
   respects it. This repo has a documented history of verdicts outrunning sample
   size — check for a recurrence.
2. **Does the convergence heuristic survive scrutiny?** It keys on a `location`
   field. Confirm that field exists, is populated, and is consistent enough to
   key on. If locations are free-form prose, the readout is noise. Say so.
3. **Is the thresholding defensible or invented?** "cumulative distinct sections
   ≥ rounds + 2" is guessed. Attack it.
4. **Does the split actually satisfy invariant #2?** The claim is that a shared
   skill file leaks author framing to the reviewer. Does `PROTOCOL.md` — which
   must carry shared vocabulary — reintroduce the same leak? Vocabulary is
   framing.
5. **Are the emoji constraints sufficient?** The design says emoji are never
   parsed and never in identifiers. Check whether anything already in the repo
   violates that, and whether the proposed grep-test would actually catch it.
6. **Is the exit-criteria set checkable?** Per §11, criteria must be verifiable,
   not aspirational. Flag any that cannot be mechanically checked.
7. **Is this the right tier?** The design argues a deterministic check beats the
   panel for this class, citing Phase 3.1. Is that analogy sound, or is scope
   judgment genuinely a reviewer responsibility (the design's own open question 5)?

### Also worth attacking

- Does this add mechanism where a prompt change would do? Open question 5 raises
  the cheaper alternative and then does not take it. Is that the wrong call?
- Is the operator-only display decision right, or is withholding the readout from
  reviewers protecting them from useful context?
- Does the design conflict with anything already committed in `phase-5/`?

### Output format

Emit one JSON object per finding, in fenced blocks, using the schema this repo
already uses:

```json
{
  "finding_id": "F-DRS-001",
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
