# Phase 5 launch — two prompts

This file holds the two prompts the operator fires against
fresh Factory Droid sessions in this order:

1. **Prompt 1 — Skill-invocation smoke test.** Verifies the
   canonical `skills/adversarial-sprint/SKILL.md` loads into a
   fresh agent's prompt context, including the new digest rule
   `#9` (chunk-close is gated, not declared) added in commit
   `40f0fff`. Operator reads the reply's structure to confirm.

2. **Prompt 2 — Phase 5 build chunk.** Fires after Prompt 1's
   smoke test passes. The fresh agent builds the 5 Phase-5
   deliverables on a fresh worktree branched from `40f0fff`.

Prompts inherit `AGENTS.md` rules: zero commit rights for the
authoring thread; the fresh agent owns the branch; the cross-family
reviewer (separate model family) closes.

Both prompts render the operator-eye "mixed" emoji signature:
`🤺👀✅⛔` is the project's four-tone visual signal (adversarial
plan review / validation gate / token signed / token refused).
The signals mean: the underlying runtime check passed. They are
NOT decorative — absence is a debugging trail, presence is
enforcement at the operator-eye layer.

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
fresh worktree branched from commit `40f0fff` (Phase 5 PRD
promotion). Operator picks the worktree path; the fresh agent
runs `git worktree add -b factory/phase-5-chunkadherence-enforcement
<path> 40f0fff` first, then `cd` into it.

**Read-this-first list:**

- `PRD.md` §11 Phase 5 (chunk-adherence enforcement layer, 5
  deliverables, 4 exit criteria) — the source of truth.
- `tools/OPERATING-RULES.md` §20 (chunk-close is gated, not
  declared).
- `skills/adversarial-sprint/SKILL.md` digest rules 1-9 + index;
  light-skill the digest before answering.
- `phase-4.5/RUN-PROMPT.md` §15 truth-table rows
  chunk-close-token, sequence-gate, operator-eye signal.
- `phase-4.5/KNOWN-ISSUES.md` KN-A-1..A-4 (frame *why* this
  layer exists; chunk-14 close did not enforce §17.2).

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
```

If any deliverable didn't land, that line carries
"BLOCKED: <shippable reason>" instead of a number. Long
post-mortems are for the chunk-close notes,
**not** in this reply.
