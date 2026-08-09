# Panel input — Phase 4.5 build review (pass-r2)

**Target of review:** commit `f971887` (chunk 11 close) + the
chunk-12 architectural corrections proposed in conversation.

**Panel seat:** Factory Droid (Anthropic / claude-family),
single-family participation. Recorded as clean-null per PRD §13 /
OPERATING-RULES §12. KN1 (real two-family) is the named follow-on.

**Envelope:** `phase-4.5/build-evidence/r-panel-pass2/envelope.json`
(verbatim, 28 turns, ~26k output tokens).

**Verdict (last line):** `REJECT_IMPLEMENTATION`.

The panel accepted all three decisions; the rejection is on the
pre-decision state — two blocker-class defects (G-10, G-7)
outrank all six chunk-12 moves in net delta.

## Findings

### Blocker-class

- **G-10 (blocker)** — `commit_chunk_change` tries to
  `git add` the per-chunk evidence dir, which `.gitignore`
  excludes by design. First live accepted chunk crashes.
  **Fix (chunk-12a):** `git add -f` force-adds the audit-trail
  dir into the per-chunk commit, pinning the audit in git
  history per OPERATING-RULES §1.
- **G-7 (blocker)** — `--non-interactive` mode is coupled to
  `--dry-run`; there's no real *unattended-live* mode. Act 2's
  "close the laptop" promise has no working code path.
  **Fix (chunk-12a):** added `--unattended` flag (decoupled from
  `--dry-run`); on refusal, writes checkpoint so an operator
  can `--resume-from`.

### Highs (rule / distribution shape)

- **G-1** — operator's two-noun framing ("Universal Rules" /
  "Project Runner") masks a third noun: **per-pilot configuration**.
  Restate: **rules** / **config** / **runner**. Runner is
  framework-side; config is per-pilot. Three nouns, not two.
- **G-2** — the two skill canonicals already show body overlap
  (`adversarial-sprint/SKILL.md` "How to invoke" +
  `sprint-invocation/SKILL.md` "Invocation"). The convention
  pinned skill↔install-path equality, not skill↔skill, so
  drift already started.
- **G-3** — both skills teach a path that doesn't travel:
  `<PILOT_REPO>/tools/sprint-loop.py --config <PILOT_REPO>/examples/sprint-loop-config.json`.
  `tools/` and `examples/` are framework-side. RUN-PROMPT.md
  uses a fourth absolute path; four path shapes, zero of which
  are the one a second adopter has.
- **G-4** — `.factory/skills/*/SKILL.md` is gitignored, but
  `test_install_paths_commit_paths_exist` asserts they're
  installed. §1 says untracked files don't travel. The test
  applied the §7 silent-green shape to test infrastructure.
  **Fix (chunk-12a):** `.gitignore` exception `!.factory/skills/`
  + `.factory/*` re-pattern to allow per-file exceptions.

### Mediums

- **G-5** — `tools/install-skill.sh all` recursed forever via
  `"$0" "$@" factory claude cursor codex` while `$@` still
  contained `all`. No `--dry-run` propagation. *No
  `sprint-invocation` support* — three of six committed install
  paths cannot be produced by the documented installer.
  **Fix (chunk-12a):** explicit per-agent × per-skill loop,
  propagated `--dry-run`, added `sprint-invocation` to `SKILLS=()`.
- **G-6** — committed `.cursor/rules/*.mdc` files were not
  produced by `install-skill.sh` (different `description:`
  strings). Body-equivalence test passes because it strips
  frontmatter, so nothing pins generator-output ↔ committed-
  artifact. **Fix (chunk-12a):** `test_install_skill_sh_cursor_mdc_body_matches_canonical_g6`
  pins the body equivalence directly.
- **G-8** — KNOWN-ISSUES F-6 says `--skip-reconcile` deferral
  rationale is "now disproven by F-7." Was true in the previous
  chunk; the chunk-12a fix also makes `--skip-reconcile` run
  `_enforce_5_3_preconditions`. **Status (chunk-12a):**
  RESOLVED — KNOWN-ISSUES KNR4 updated.
- **G-11** — `BACKLOG-D` phases collides with PRD §11 (Phase 6
  = no new feature work, Phase 7 = outside 0-6 arc). **Fix
  (chunk-12a):** renumbered to "Backlog D, post-Phase-5."

### Lows (doc drift cluster)

- **G-12** — KNOWN-ISSUES / EXIT-CHECKS / SKILL.md all had
  drift numbers (63→69/75 tests; §1–§18 → §1–§19; "eviction
  of audit files" → "inclusion"). **Fix (chunk-12a):** all
  surfaces updated.
- **G-13** — `panel-prompt-r2.md` was untracked. §1: the request
  for this pass would not travel with the repo. **Fix
  (chunk-12a):** tracked.

## Disposition target

| Disposition            | Findings                                  |
|------------------------|-------------------------------------------|
| Fix now (chunk-12a)    | G-10, G-7, G-8, G-4, G-6, G-5, G-11       |
| Fix in-pass (chunk-12a)| G-12, G-13                                |
| Chunk 12b architectural| G-1, G-2, G-3 (templates + overlay + skill split) |
| Named gap if deferred  | G-1 (three-noun restatement)               |

## Three decisions (accepted, with nits)

1. Decision 1 — split is right; the noun needs the third
   element (config vs runner). Chunk 12b adds the third.
2. Decision 2 — two-state simplification is right; the
   third mode is `--unattended` (real unattended), not a
   strict-mode dial.
3. Decision 3 — ranking: blockers first (G-10, G-7), then
   move 4 (framing), then moves 1+3 collapsed, then move 2
   (skill split). Moves 5 + 6 cut per §17 capacity envelope.
