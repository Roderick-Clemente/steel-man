# Phase 4.5 — adversarial panel input request (pass-r2)

**Scope:** Review the build state at commit `f971887` (chunk 11
close) and the proposed chunk-12 architectural corrections. This
is the second adversarial review pass; the first (pass-r1,
chunk 10) surfaced F-1 through F-11 and ten were fixed in-place.
This pass is specifically about:

1. The skill distribution shape (chunk 11) — was the chunk-11
   hybrid the right call, given the new framing of "Universal
   Rules belong with the agent, Project Runner belongs with the
   project" that emerged after the chunk 11 commit?
2. The §15 Act 1 / Act 2 transition framing — does the
   two-state simplification (manual = don't invoke the runner;
   runner = invoke with default refusal hooks) make the
   structural guarantee visible without overengineering?
3. The chunk-12 plan — six concrete moves; rank them by
   net delta to the demo.

READ ONLY. `Read`, `Glob`, `Grep`, `LS`. No `Execute`, no `Edit`.

## Code + doc audit scope

Changes since pass-r1 (commit `548a29a → f971887`):

- `tools/OPERATING-RULES.md` §19 added: "Commit when the
  recommendation is clear; do not force the operator to choose."
- `skills/adversarial-sprint/SKILL.md`: digest entry 8 (§19),
  rehydration trigger for §19, index table updated.
- `skills/sprint-invocation/SKILL.md`: NEW small skill (~80 lines),
  contains the runner CLI surface + 3 example invocations.
- `tools/conventions/skill-distribution.md`: NEW convention doc
  on the four install paths and zero body drift.
- `tools/install-skill.sh`: NEW install bootstrap.
- `.claude/skills/{adversarial-sprint,sprint-invocation}/SKILL.md`:
  committed symlinks.
- `.cursor/rules/{adversarial-sprint,sprint-invocation}.mdc`:
  committed generated wrappers.
- `AGENTS.md`: multi-agent handoff section adds a cross-ref to
  the canonical skill asset.
- `tests/test_sprint_loop.py`: +6 tests pinning body-draft
  equivalence and chunk-11 install paths.
- `phase-4.5/BACKLOG-D-CAPABILITIES-FRAMEWORK.md`: NEW forward
  design note for the runner-as-skill-orchestrator extension.

Plus the chunk-12 plan as described in the conversation log
(operator's brief): move `examples/`-side config to per-pilot
`.adversarial-sprint/` overlay, split meta-skill into Universal
Rules vs Project Runner cleanly, two-state act transition (no
`--act2-strict` flag), explicit §15 framing in RUN-PROMPT +
BUILD-NOTES, three seed capabilities as the Phase 6 anchor.

## Decision 1 — Skill distribution shape after the framing flip

The operator reframed after chunk 11. The runner is *project
context* (lives with the pilot repo, in `.adversarial-sprint/`
overlay). The rules are *agent context* (universal, single copy
per machine). Chunk 11 shipped a single canonical file conflating
both.

**Question:** was the framing flip right? Should chunk 12 split
the canonical asset into Universal Rules content (digest + index
+ rehydration) and Project Runner content (CLI flags + chunks
file + per-pilot config pointer) — with NO body overlap? Or
does the operator's actual workflow tolerate the conflated
shape as-is?

## Decision 2 — §15 Act 1 / Act 2 transition

Two-state simplification: manual mode = don't invoke the runner;
runner mode = invoke and the runner *is already in refusal-mode
post-chunk-10*. Visibility lives in `--dry-run`'s honest
truth-table, not in a third flag.

**Question:** does the simplification accurately reflect the
§15 structural guarantee, or is there a real value to a third
mode (e.g., `dry-run --treat-as-live`)?

## Decision 3 — Chunk-12 plan ranking

Six moves proposed:
1. Move `examples/sprint-loop-config.json` + chunks-example to
   `templates/`, copy-into per-pilot `.adversarial-sprint/`
   overlay.
2. Split meta-skill into Universal Rules + Project Runner with
   no body overlap.
3. Add `.adversarial-sprint/` overlay template (runner symlink,
   per-pilot config, chunks file, small `bin/run-sprint` shell
   wrapper).
4. Update BUILD-NOTES, RUN-PROMPT, skill to name §15 Act 1 /
   Act 2 explicitly.
5. Add an act-mode flag (`--act1` / `--act2` / `--act2-strict`).
   (Note: this is being *removed* per operator feedback in the
   chunk-12 plan — included here for completeness; panel may
   still weigh in on the deeper question.)
6. Three seed capabilities: `priority-ranker` (during-plan),
   `feature-clarifier` (pre-sprint), `silent-green-sniffer`
   (post-chunk).

**Question:** rank the net-delta-to-demo of moves 1-6 (move 5 is
soft-deprecated). What should be cut for §17 capacity envelope?

## Method of response

Same shape as pass-r1: last line of response is one of
`ACCEPT-WITH-NITS` / `ACCEPT` / `REJECT` / `REJECT_TEST` /
`REJECT_IMPLEMENTATION` / `HUMAN_DECISION`. Body has findings
numbered **G-1** through **G-N** (use **G-** to keep these
distinct from pass-r1's F-*).

## Sufficient evidence

- `phase-4.5/BACKLOG-D-CAPABILITIES-FRAMEWORK.md` — forward
  design note.
- `tools/conventions/skill-distribution.md` — chunk-11 convention.
- `skills/adversarial-sprint/SKILL.md` — meta-skill canonical.
- `skills/sprint-invocation/SKILL.md` — small extraction.
- `tests/test_sprint_loop.py` (now 69 tests) — body pinning.
- Bash log at the conversation record (chunk 10 commits + chunk
  11 commit body + the §15 framing discussion).

Do NOT read the diff in detail; the criteria-check.md already
maps the PRD §11 exit criteria. Focus on the three decisions.
