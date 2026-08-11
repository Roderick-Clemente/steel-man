# Phase 5 launch — two prompts

This file holds the two prompts the operator fires against
fresh Factory Droid sessions in this order:

1. **Prompt 1 — Skill-invocation smoke test.** Verifies the
   canonical `skills/adversarial-sprint/SKILL.md` loads into a
   fresh agent's prompt context, including the new digest rule
   `#9` (chunk-close is gated, not declared) added in commits
   `40f0fff` + `c6a1a7a`. Operator reads the reply's structure
   to confirm.

2. **Prompt 2 — Phase 5 build chunk.** Fires after Prompt 1's
   smoke test passes. The fresh agent builds the 5 Phase-5
   deliverables on a fresh worktree branched from `main` HEAD
   `2918bd6` (post-cleanup; the Phase 5 PRD promotion
   (`40f0fff`+`c6a1a7a`+`fa14360`) was FF-merged to `main`
   before the origin-merge (`83b75cb`) and the chunk-14
   executor's design-doc fold (`2918bd6`) both landed
   no-ff-atop).

Prompts inherit `AGENTS.md` rules: zero commit rights for the
authoring thread; the fresh agent owns the branch; the cross-family
reviewer (separate model family) closes.

Both prompts render the operator-eye "mixed" emoji signature:
`🤺👀✅⛔` is the project's four-tone visual signal (adversarial
plan review / validation gate / token signed / token refused).
The signals mean: the underlying runtime check passed. They are
NOT decorative — absence is a debugging trail, presence is
enforcement at the operator-eye layer.

## Pre-launch state (post-cleanup)

The branch state at the time this file was last updated:

- **`main`** = `2918bd6`. The Phase 5 PRD promotion triple
  (`40f0fff` + `c6a1a7a` + `fa14360`) is followed by the
  origin-merge commit `83b75cb` (wiki-phase-3.1 PR #1 + Phase
  3.1 follow-up program), then the chunk-14 executor's
  `DESIGN-REVIEW-ATTESTATION-GATE.md` fold as commit `2918bd6`.
  This is the canonical Phase 5 base — the fresh agent branches
  from `main` HEAD `2918bd6`.
- **`factory/phase-4.5-loop-runner`** — deleted. FF-merged into
  `main` before `fa14360`; branch removed in the clean-up. No
  follow-up branch references it.
- **`factory/review-attestation-gate-spec`** at `5e8774e` —
  folded into `main` as commit `2918bd6` (no-ff; the spec-doc
  was on a branch off `5449c06` and main now includes the
  Phase 4.5/5 promotion triple + the origin merge, so no-ff
  was forced). The design-doc is on `main` and Phase 5's
  build-chunk reads it as the concrete layer-1/2/3 reference.
  Branch can be safely deleted.
- **`factory/chunk-14-kn-J-fixes`** at `623e024` — paused.
  Routes through `chunk_sequence_gate` once Phase 5 enforcement
  tool lands in Prompt 2's deliverables. Branch rebases onto
  `main` at that point.
- **`factory/chunk-e-contract-reader`** at `9c069e0` — paused.
  Rebased onto `main` `2918bd6` after operator resume; single
  commit (10 files, +826/-36), 14 new tests pass + 2 pre-existing
  failures confirmed on clean main. NOT routed through merge
  until `chunk_sequence_gate` exists. Same gate applies.

The user-facing cleanup candidates (worktrees, residual branches)
are documented in this file so the operator can dismiss or
re-target them quickly.

---

## Prompt 1 — Skill-invocation smoke test

You are a clean Factory Droid session on this project
(`/Users/factory/work/adversarial-sprint-dev`). The canonical
skill is `skills/adversarial-sprint/SKILL.md`. Light-skill the
digest (rules 1-9 in the canonical version) before answering.

Per `AGENTS.md`: the receiving agent MUST read the canonical
asset at session start. Confirm explicitly in your reply.

This is **read-only.** Do not edit files. Do not run `droid exec`.
Reply with **exactly** this structure (paraphrase the headings,
do not change the emoji signature line):

```
🤺👀✅⛔
   skill-load-confirmed: I read skills/adversarial-sprint/SKILL.md
       at session start (AGENTS.md invariant).

digest (one line per rule):
   1. <rule 1 paraphrase>
   2. <rule 2 paraphrase>
   3. <rule 3 paraphrase>
   4. <rule 4 paraphrase>
   5. <rule 5 paraphrase>
   6. <rule 6 paraphrase>
   7. <rule 7 paraphrase>
   8. <rule 8 paraphrase>
   9. <rule 9 paraphrase>

🤺👀✅⛔
   operator-eye signal: smoke-test ran. Do not proceed to build.
   Operator: confirm rule 9 paraphrase mentions EVIDENCE_SIGNING_KEY
       and chunk-N.token.json. If absent, the canonical asset is
       stale; restart after `git pull && bash tools/install-skill.sh
       factory` on this branch.
```

Failure modes the operator eyes for:

- **Mixed emoji line absent or rendered as ASCII**: skill did not
  load. Troubleshooting per PRD §11 Phase 5 §5 step 6.
- **Rule 9 paraphrase missing or wrong**: the canonical SKILL.md
  has my rule #9; if the agent paraphrases only rules 1-8 it
  loaded from a stale copy (likely an old worktree / cache).
- **Reply proposes to edit files**: prompt was misread as Prompt 2.

Acceptance: the reply has both `🤺👀✅⛔` lines and rules 1-9
present, including rule 9 about chunk-completion tokens. No
filesystem mutations.

---

## Prompt 2 — Phase 5 build chunk

**Branch:** `factory/phase-5-chunkadherence-enforcement`,
fresh worktree branched from `main` HEAD `2918bd6`
(post-cleanup; the Phase 5 PRD promotion triple landed FF on
`main`, then the origin-merge and the chunk-14 executor's
design-doc fold landed no-ff atop. So the fresh agent's base
is `main` at `2918bd6`, *not* an intermediate branch).
Operator picks the worktree path; the fresh agent runs
`git worktree add -b factory/phase-5-chunkadherence-enforcement
<path> main` first, then `cd` into it.

**Clean WIP discipline.** `factory/chunk-e-contract-reader`
is at `9c069e0` on its own worktree, rebased onto clean main
`2918bd6`, working tree clean. The Phase-5 fresh-agent does NOT
inherit Backlog-E WIP. After operator resume of the chunk-e
fresh-agent, the contract-reader files live on
`factory/chunk-e-contract-reader`, not on `main` and not on
the Phase-5 fresh-agent's worktree. Phase 5 builds the gate;
Backlog E routes through the gate as its own chunk. The
chunk-e fresh-agent's contract-reader adapter is the
first consumer of the gate, but it commits separately after
Phase 5 closes.

The shared worktree (`/Users/factory/work/adversarial-sprint-dev`)
currently has no uncommitted Phase-5 WIP. Stash `stash@{0}`
(`pre-origin-merge-backlogE-stash`) holds the old
pre-cleanup chunk-e state for archival; the Phase-5 fresh-agent
does not touch it. The `9c069e0` chunk-e commit has its own
worktree; do not revert, do not cherry-pick.

**Read-this-first list:**

- `PRD.md` §11 Phase 5 (chunk-adherence enforcement layer, 5
  deliverables, 4 exit criteria) — the source of truth.
- `tools/OPERATING-RULES.md` §20 (chunk-close is gated, not
  declared) + check whether §17 amendment per KN-R1 (Layer 3 of
  the chunk-14 executor's design doc) is already in place; if
  not, that is owed §A-1 followup before pass-r5 close.
- `skills/adversarial-sprint/SKILL.md` digest rules 1-9 + index;
  light-skill the digest before answering.
- `phase-4.5/RUN-PROMPT.md` §15 truth-table rows
  chunk-close-token, sequence-gate, operator-eye signal.
- `phase-4.5/KNOWN-ISSUES.md` KN-A-1..A-4 + KN-R1 (frame
  *why* this layer exists; chunk-14 close did not enforce §17.2;
  KN-R1 records the three-layer fix design with KN-A-1..A-4 as
  rationale pointers).
- `phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md` — the concrete
  shape for deliverables 5a/5b/5c/5d: HMAC-SHA256 + `tree_sha`
  binding + signature envelope, fail-closed verifier, the
  `bin/review-branch <base>..<head>` entrypoint as Layer 1, and
  the OPERATING-RULES §17 amendment as Layer 3. The design
  doc has already chosen the cryptography (reuses
  `EVIDENCE_SIGNING_KEY`) and the gate predicate (≥2 distinct
  families + implementer disjointness + ACCEPT-class verdict);
  the build-chunk executes that choice, doesn't redo it.
- `phase-4.5/ROADMAP-REVIEW.md` + `phase-4.5/BACKLOG-D-
  CAPABILITIES-FRAMEWORK.md` — Phase 5 row was added during the
  promotion triple; verify the audit row reads "chunk-adherence
  enforcement layer" not "generalisation."

**Five deliverables (from PRD §11 Phase 5):**

1. **chunk-completion token shape + signer.** Write
   `tools/sign_chunk_token.py` (or inline in
   `commit_chunk_change`): HMAC-SHA256 by `EVIDENCE_SIGNING_KEY`
   over `canonical_json({chunk_commit_sha, reviewers, signed_at,
   signed_by})`. Output: `phase-4.5/tokens/chunk-N.token.json`.
2. **`tools/cross_family_review.py`** — refusal-at-parse +
   dual-ACCEPT emit. Validator-family taxonomy lives in
   `tools/sprint_loop/config.py: MODEL_FAMILY_MAP`. Refusal cases:
   (a) reviewer list empty, (b) any reviewer family equals
   implementer family, (c) reviewer family `unknown`, (d) reviewer
   verdict not in `{ACCEPT-WITH-NITS-or-better}`. Emit token only
   on dual ACCEPT-WITH-NITS-or-better from reviewers that pass
   (a)-(c).
3. **`tools/chunk_sequence_gate.py`** — refuses chunk-N+1 from
   starting when chunk-N's token is missing, unreadable, or
   signature mismatched. Exit code 6 on refusal. Wire into the
   runner's chunk-close path so token emit precedes commit.
4. **Skill + distribution update.** (rule #9 already in
   SKILL.md from `40f0fff`; just verify.) `tools/install-skill.sh`
   re-emits `.factory/skills/`, `.claude/skills/`,
   `.cursor/rules/` against the new rule.
5. **Operator-eye visual signal — runtime-bound, not decorative.**
   Helper at `tools/sprint_loop/chunk_close_banner.py` (or
   inline in `commit_chunk_change`). Output rule: emit `✅` only
   when `chunk-N.token.json`'s HMAC verifies; emit `⛔` when
   token missing/invalid. ABSENCE ≠ skill exhausted; ABSENCE is
   a runtime contract violation. The 6-step troubleshooting
   checklist lives in PRD §11 Phase 5 §5; the operator runs it
   on absent signal.

**Build chunks (per OPERATING-RULES §18):**

- **Chunk 5a** = token signer + replay on chunk-13 fixture.
  Behavioral pin: `tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds`.
  (Run `python3 -c "import json,hmac,hashlib; ..."` over the
  chunk-13 fixture commit; signature must verify.)
- **Chunk 5b** = `cross_family_review.py`. Behavioral pins:
  `test_same_family_refuses`, `test_unknown_family_refuses`,
  `test_dual_accept_emits_token`, `test_missing_reviewer_refuses`.
  Drive via `argparse.Namespace`; refuse-on-parse means the
  ScriptError fires before output.
- **Chunk 5c** = `chunk_sequence_gate.py` + runner integration.
  Behavioral pins: `test_prior_token_missing_refuses`,
  `test_prior_token_invalid_signature_refuses`,
  `test_prior_token_valid_proceeds`.
- **Chunk 5d** = operator-eye signal binding. Behavioral pins:
  `test_signal_present_when_token_verifies`,
  `test_signal_absent_when_token_refuses`, `test_absence_triggers_checklist_pointer`.
- **Chunk 5e** = install-skill.sh re-emit + dress rehearsal.
  Behavioral pin: `test_install_skill_emits_rule_nine_to_factory_claude_cursors`.

**Anti-patterns (do not do):**

- Source-grep tests (J-12 / J-16 vacuous-pin pattern). Use
  behavioral pins that drive through main()/argparse, not via
  `grep -F`.
- Trust agent claim "I produced token." Materialize the file and
  assert HMAC verification by direct hmac.compare_digest call.
- Skip the cross-family §17.2 step because a single reviewer is
  "already there." Two-family (or more) is required.
- Do not allow the chunk-e (`factory/chunk-e-contract-reader`
  at `9c069e0`) or chunk-14 (`factory/chunk-14-kn-J-fixes`
  at `623e024`) merges to bypass this gate once it exists.
  The gate is the load-bearing claim; fast-path or
  `--no-verify` exemptions recreate the chunk-13/14 vacuous-pin
  pathology for any chunk with passing tests.
- Do not collapse Act 1 (conversational edits) into Act 2
  (runner/panel): this is the chunk-14 §15 anti-pattern. Stay
  runner-driven: every chunk close is a `chunk_sequence_gate`
  run, not a prose declaration.

**Ownership of this chunk:**

- The fresh agent owns the branch. The previous thread (this one)
  has zero commit rights on `factory/phase-5-chunkadherence-enforcement`.
- Pass-r5 close on this branch: reviewed by an operator outside
  this thread. Cross-family §17.2 satisfied (two distinct model
  families on separate diffs). Empirical mutation-testing of the
  gate required.

**Reporting back to the operator (per OPERATING-RULES §19; ships
recommendation with WHY, numbers + paths + sha, no long prose):**

```
branch:        factory/phase-5-chunkadherence-enforcement
worktree:      <path>
sha:           <commit-sha>
chunk5-token:  phase-4.5/tokens/chunk-5.token.json  (signed)
install run:   <install-skill.sh output line count, or crash>
test count:    <pytest --tb=no | tail -1>
behavioural:   <5 chunks; each ≥1 pin name; total pin count>
op-rule-17:    <yes — Layer 3 amendment in OPERATING-RULES.md, line N>
               <or BLOCKED: Layer 3 prose amendment pending>
design-doc:    <read DESIGN-REVIEW-ATTESTATION-GATE.md before build start? yes/no>
```

If any deliverable didn't land, that line carries
"BLOCKED: <shippable reason>" instead of a number. Long
post-mortems are for the chunk-close notes,
**not** in this reply.

The `op-rule-17` line is the close-criterion for the chunk-14
executor design's Layer 3 (the prose amendment voiding same-
family self-run subagent reviews). If it is not already
applied to `tools/OPERATING-RULES.md`, the chunk-5 build owns
the patch as part of its deliverables; the operator-side follow-
up is for chunks that close without the amendment in place.

The `design-doc` line is a separate audit because the chunk-14
executor pattern (build without reading the rationale that
motivated the build) is exactly the failure the build is meant
to prevent. Closing both `op-rule-17` and `design-doc` is
required for cross-family review to attach to a chunk that
already has the prose amendment in place; build without that
amendment fails Layer 3 of the gate.

## Post-launch state (Phase 5 build close)

The Phase-5 fresh-agent build closed on
`factory/phase-5-chunkadherence-enforcement`. The branch was cut
off `main` HEAD `f2f14085c9119fe638a146a8b43817404ddb9a49` (the
`40f0fff`+`c6a1a7a`+`fa14360` promotion triple landed in `main`
ahead of the chunk-14 design-doc fold and the origin-merge; the
canonical Phase-5 base is therefore `main` HEAD `f2f1408`, *not*
the `2918bd6` reference cited at the top of this file). Per-pilot
operators who trigger a fresh Phase-5 build should branch from
this updated `main` HEAD.

**Build terminal points (audit trail):**

`factory/phase-5-chunkadherence-enforcement` branch tip
(`dda84d1` at the time this section was added). Cross-family
review at pass-r5 closes this branch; the next Agent's main
absorb is the merge that follows.

Chunk-5 commit sequence (code-commit then token-commit; each
token cross-family ACCEPT-WITH-NITS signed by EVIDENCE_SIGNING_KEY
via `tools/sign_chunk_token.py sign`, then independently
re-verified at chunk close via
`tools/sprint_loop/chunk_close_banner.py`):

| chunk | code-commit | token-commit |
|-------|-------------|--------------|
| 5a    | `364f15d`   | `f89275f`    |
| 5b    | `a8ba006`   | `663ee4c`    |
| 5c    | `e5178cc`   | `76eb3ab`    |
| 5d    | `386f2ac`   | `59442ab`    |
| 5e    | `5193cc9`   | `dda84d1`    |

Each `chunk-N.token.json` lives at
`phase-4.5/tokens/chunk-N.token.json`. The token binds to the
code-commit SHA via the `chunk_commit_sha` field; HMAC-SHA256
under `EVIDENCE_SIGNING_KEY` produces the operator-eye `✅`
signal at chunk close. Refusal produces `⛔` + the PRD §11
Phase 5 §5 troubleshooting checklist on stderr (§20 is
structural, not decorative).

**Build deliverables landed (vs. PRD §11 Phase 5):**

1. `tools/sign_chunk_token.py` — chunk-completion token shape + signer.
2. `tools/cross_family_review.py` — refusal-at-parse dual-ACCEPT gate.
3. `tools/chunk_sequence_gate.py` — next-chunk-start refusal on prior-token missing / HMAC-mismatched.
4. Skill + distribution update: rule #9 propagated through `tools/install-skill.sh` re-emit to `.cursor/rules/adversarial-sprint.mdc` and `.claude/skills/`, test pin `tests/test_install_skill_phase5.py`.
5. `tools/sprint_loop/chunk_close_banner.py` — operator-eye visual signal binding (✅ / ⛔ / checklist pointer).

Plus: OPERATING-RULES §17 Layer-3 amendment (in
`tools/OPERATING-RULES.md`, line ~272) closes the §17.2
rationalization hole documented at KN-R1 and `phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md` §8.

**Next-agent (cross-family review):**

Pass-r5 close on this branch is owned by an operator outside
this thread (a separate model family from this build session —
§17.2 distinct-families). Empirical mutation-testing of the
gate (chunk_sequence_gate refusal at every refusal mode in the
truth-table) is required for ACCEPT-WITH-NITS-or-better per
PRD §11 Phase 5 exit criteria.
