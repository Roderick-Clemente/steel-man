# Phase 4.5 — adversarial panel input request (pass-r3)

**Scope:** Review the build state at commit `0feaaa4` (chunk-12b
close) on the §15 demo-delta claim. This is the third adversarial
review pass. Pass-r1 fixed F-1…F-11; pass-r2 fixed G-1…G-13
(blocker + lifecycle, and chunk-12b delivered the distribution
shape + per-pilot overlay). This pass is specifically about
whether **the runner can complete one real chunk end-to-end as
the §15 structural guarantee**.

Two things matter:

1. **Visibility of Act 1 vs Act 2.** The chunk-12b per-pilot
   overlay (`templates/overlay/`) was supposed to collapse the
   four-path drift (skills, RUN-PROMPT, examples/, framework CLI)
   to a single operator entrypoint: `.adversarial-sprint/bin/run-sprint`.
   The meta-skill was supposed to drop "How to invoke" in favor
   of "Universal Rules." Was the collapse real? Or is there a
   second operator-facing path that I missed — and an operator
   who uses it can silently skip a structural guarantee?

2. **Truth of the §15 claim.** The §15 framing in RUN-PROMPT says
   "the demo's delta is the transition between modes." The
   truth-table distinguishes what `--dry-run --non-interactive`
   simulates vs what live mode enforces. Is the truth-table
   honest about what `--dry-run` does NOT do? Did chunk 12b
   accidentally introduce a code path that lets `--dry-run` say
   ACCEPT where the §5.3 preconditions would refuse live?

READ ONLY. `Read`, `Glob`, `Grep`, `LS`. No `Execute`, no `Edit`.

## Code + doc audit scope

Changes since pass-r2 (commit `e820dd7 → 0feaaa4`):

- **`tools/sprint_loop/config.py`** — `evidence_output_dir` Config
  field + `--evidence-output-dir` CLI flag. Framework audit tree
  can be staged anywhere.
- **`templates/overlay/`** (NEW) — `bin/run-sprint` (executable
  shell wrapper → finds config → fires runner), `*.template.json`
  with `REPLACE-WITH-FRAMEWORK-CHECKOUT-PATH` etc. placeholder
  contract, `README.md` documents install + edit.
- **`skills/adversarial-sprint/SKILL.md`** — stripped the
  duplicated "How to invoke" block. Meta-skill now Universal
  Rules only (digest + index + rehydrate). References the
  per-pilot overlay for invocation.
- **`tools/sprint-loop.py`** — adds `--unattended` argparse flag.
  Decoupled from `--dry-run` at the parser layer. The reconcile
  gate runs `_enforce_5_3_preconditions` and on refusal writes
  `checkpoint.json` then `SystemExit(4/5)`. Resumes via
  `--resume-from`.
- **`phase-4.5/RUN-PROMPT.md`** — §15 Act-1/Act-2 framing with
  truth-table distinguishing `--dry-run` vs live vs
  `--dry-run --non-interactive` vs `--unattended`. Per-pilot
  overlay invocation block.
- **`phase-4.5/BUILD-NOTES.md`** — §15 framing intro + chunks
  10/11/12a/12b inventory entries; "12 chunks" replaces "9 chunks."
- **`tests/test_sprint_loop.py`** — +4 chunk-12b regression tests:
  meta-skill no-invocation-block (G-2),
  `tools/sprint-loop.py --help` exposes `--unattended` (G-7),
  `templates/overlay/bin/run-sprint` is executable (G-3),
  `examples/sprint-loop-{config,chunks-example}.json` no longer
  exist (G-3).
- **`tools/install-skill.sh`, `.gitignore`** — restructured so the
  `.factory/skills/**` exception actually carves out the committed
  symlinks (was shadowed by parent `.factory/*` rule before).
- **`examples/` → `templates/overlay/`** rename.
- **`phase-4.5/EXIT-CHECKS.md`, `KNOWN-ISSUES.md`,
   `BACKLOG-D-CAPABILITIES-FRAMEWORK.md`** — test count updated
  (63 → 75 → 79), KNR4 → RESOLVED, BACKLOG-D renumbered.

## Decision 1 — Act-1 vs Act-2 visibility

The per-pilot overlay path is supposed to be the **one true
entrypoint**. An operator in seat runs
`<PILOT_REPO>/.adversarial-sprint/bin/run-sprint` and that fires
the framework CLI with the right config. SKILLS live as Universal
Rules on the agent's side. RUN-PROMPT documents the overlay and
points at it. The meta-skill does not teach the framework path.

**Question:** does this **collapse to one operator path**? Are
there second paths hidden in:
- `tools/install-skill.sh` — does it accidentally suggest
  `tools/sprint-loop.py` as a path?
- The `*.mdc` cursor wrappers — do they leak the framework CLI?
- The `.claude/skills/...` and `.factory/skills/...` symlinks —
  do they behave like a "real installation" that opens the
  second path?
- BUILD-NOTES.md / KNOWN-ISSUES.md — do they tell the operator
  to "follow the framework CLI" anywhere?

## Decision 2 — §15 truth-table honesty

The truth-table claims:
- `--dry-run --non-interactive`: simulated ACCEPT (no commit; no
  actual model call; the runner prints the dry-run branch's
  auto-decision).
- live (no flag): human-pause gate.
- live with `--non-interactive`: bypass gate; §5.3 preconditions
  still enforce family/separation/etc.
- live with `--unattended`: §5.3 preconditions enforced; on refusal,
  writes `checkpoint.json` + raises `SystemExit(4/5)`.
- live with `--skip-reconcile`: same as `--non-interactive` but
  loud — _enforce_5_3_preconditions runs; operator override via
  `--allow-test-author-collide` is explicit.

**Question:** does any code path produce GREEN where the truth-
table claims RED? Specifically inspect:
- `tools/sprint-loop.py:600–630` — the dry-run vs --non-interactive
  vs --unattended gate handling. Does dry_run=True short-circuit
  bypassing `_enforce_5_3_preconditions`?
- `tools/sprint_loop/config.py` — the `default_evidence_dir` /
  `evidence_output_dir` path. Does the new flag accidentally
  redirect git force-add into a wrong tree?
- `tools/sprint_loop/droid.py` (chunk-10 fix F-8) — the bounded
  retry loop. Does `--unattended` accumulate retries without
  writing a checkpoint per retry?
- `--skip-reconcile` (chunk-12a G-8) — does it really run
  `_enforce_5_3_preconditions` or is it a papered-over branch?

## Decision 3 — Demo-delta claim

The §15 claim is that the **transition** between Act 1 (vibe code)
and Act 2 (runner-driven) is the demo. In Act 1, the operator
+ agent in a conversational loop, no runner, agent's prompt-
discipline only. In Act 2, the runner is the §11 gate.

**Question:** is there a place where Act 1's promise "follow the
skill digest + index" is silently doing what Act 2's runner
should do? For instance:
- Does the meta-skill contain a "what I do" probe that *invokes*
  things (which is Act 2 territory)?
- Does `tools/OPERATING-RULES.md` §19 say "don't 3-option-question"
  by itself invoke a runner-style orchestration that conflicts
  with the ACT 1 semantics?

## Method of response

Same shape as pass-r1, pass-r2. Numbered findings **H-1** through
**H-N** (use **H-** to keep these distinct from F-*, G-*).
Last line: one of
`ACCEPT-WITH-NITS` / `ACCEPT` / `REJECT` / `REJECT_TEST` /
`REJECT_IMPLEMENTATION` / `HUMAN_DECISION`.

## Sufficient evidence

- `phase-4.5/RUN-PROMPT.md` — §15 framing + truth-table.
- `phase-4.5/BUILD-NOTES.md` — chunks 10–12b inventory.
- `phase-4.5/KNOWN-ISSUES.md` — KNR4 RESOLVED, test count 79.
- `tools/sprint-loop.py:600–630` — gate handling.
- `tools/sprint_loop/config.py` — `evidence_output_dir` field.
- `tools/sprint_loop/droid.py` — bounded retry loop (chunk-10
  F-8 fix).
- `templates/overlay/README.md` — operator install steps.
- `templates/overlay/bin/run-sprint` — one-command firing.
- `skills/adversarial-sprint/SKILL.md` — Universal Rules only.

Do NOT read the diff in detail. Focus on the three decisions.
