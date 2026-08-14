# Phase 4.5 — adversarial panel input request (pass-r4)

**Scope:** Review the build state at commit `f1bae98` (chunk-13
close) on whether the **§15 demo-delta claim now holds**. Pass-r3
REJECT_IMPLEMENTATION with 19 findings (H-1..H-19). Chunk 13 fixed:

- Blockers (H-1, H-2, H-3, H-4): rewritten sprint-invocation
  skill (overlay-only), gate-mode plumbing refactor (no longer
  `cfg.dry_run = True` aliasing `--non-interactive`),
  bin/run-sprint flag-first argv + EVIDENCE_SIGNING_KEY guard,
  `--resume-from` space-form flows through main + cfg_argv.
- Highs (H-5, H-6, H-7, H-8, H-9, H-10): load_checkpoint recovers
  lost fields; meta-skill stripped of framework-CLI path; 7-doc
  drift sweep; --help expanded; evidence_output_dir out-of-tree;
  run-level checkpoint committed.
- Source-grep tests **replaced with behavioral tests** for G-7/G-8
  + H-2 (gate-mode detection no longer reads `sys.argv`).

This pass is specifically: **does the §15 demo-delta hold now?**

Three axes of inquiry:

1. **Operator entrypoint is collapsed.** After chunk-13, is
   `bin/run-sprint --dry-run --non-interactive` the **only** path
   an operator sees in the canonical skills, in RUN-PROMPT, in
   EXIT-CHECKS, in EXIT-CHECKS (5)? Does it actually run end-to-end
   as documented?
2. **Live gate semantics are honest.** After chunk-13's gate-mode
   plumbing refactor, the test-and-verify pipeline is the §5.3
   preconditions met path, NOT a global alias for `--dry-run`.
   Are the §15 truth-table rows now accurate?
3. **Behavioral pins catch what source-greps missed.** The
   behavioral gate tests (test_unattended_writes_checkpoint_on_refusal_g7
   etc.) are the test bar going forward; if a panel call after
   chunk-13 still reveals H-2 / H-14-style drift, that means the
   behavioral coverage has gaps.

READ ONLY. `Read`, `Glob`, `Grep`, `LS`. No `Execute`, no `Edit`.

## Code + doc audit scope

Changes since pass-r3 (commit `0feaaa4 → f1bae98`):

- `tools/sprint-loop.py`:
  - `cfg.dry_run` no longer coerced from `--non-interactive` (was
    `:1034`; now `cfg.gate_auto_decide` opt-in).
  - `reconcile_human_gate` signature extended: `gate_auto_decide`,
    `unattended`, `no_dry_auto_decide`. No `sys.argv` reads remain.
  - `--skip-reconcile` no longer has its own special branch; it
    routes through `reconcile_human_gate(gate_auto_decide=True, …)`.
  - `load_checkpoint` now recovers `dry_run`, `plan_reviewer_verdicts`,
    `plan_round`, `max_review_rounds`, `retry_threshold`,
    `max_auto_retries`, `retry_delay_seconds` from JSON.
  - `commit_chunk_change` takes a new `run_evidence_dir: str | None`
    and force-adds `<run_evidence_dir>/checkpoint.json` so the
    run-level checkpoint lands in the chunk's git commit.
  - `commit_chunk_change` now checks stage-path inside `_REPO_ROOT`
    before force-add; out-of-tree evidence prints an H-9 banner and
    skips staging instead of raising RuntimeError mid-run.
  - The runner's own FATAL message (was at `:1208`) now points at
    `<PILOT_REPO>/.adversarial-sprint/chunks.json`.
  - `--help` now renders BOTH the runner-only flags AND the
    Config-side flags via `_format_build_config_help_synthetic`.

- `tools/sprint_loop/config.py`:
  - New Config fields `gate_auto_decide: bool`, `unattended: bool`.
  - New CLI flags `--gate-auto-decide`, `--unattended`,
    `--no-dry-auto-decide`, `--non-interactive`. (The last was
    previously only in main()'s parser; now in build_config so the
    Config is consistent.)
  - `args.non_interactive` → `cfg.gate_auto_decide = True`
    (was previously a hidden alias for `dry_run=True`).
  - Docstring cites `templates/overlay/sprint-loop-config.template.json`
    not the deleted `examples/sprint-loop-config.json`.

- `templates/overlay/bin/run-sprint`:
  - Rewrite: argv walker that recognises `--chunks-file=…` and
    `--chunks-file <path>`; chunks file defaults to
    `$OVERLAY_DIR/chunks.json`; warning uses
    `${EVIDENCE_SIGNING_KEY:-}` so unset doesn't crash on
    `set -u`.

- `skills/sprint-invocation/SKILL.md`:
  - End-to-end rewrite. No `<PILOT_REPO>/tools/sprint-loop.py` anywhere.
  - No `examples/sprint-loop-*.json` referenced.
  - Operator surface is exclusively the per-pilot overlay.

- `skills/adversarial-sprint/SKILL.md`:
  - "How to invoke" section rewritten; framework-CLI line removed
    (was lines 143-147 in pass-r3 version).

- `phase-4.5/RUN-PROMPT.md` Steps 3 + 5:
  - Reference the per-pilot overlay; framework-CLI equivalents are
    debug-only.
- `phase-4.5/EXIT-CHECKS.md` (5): same.
- `phase-4.5/KNOWN-ISSUES.md` KN1 reproduction: overlay form.
- `phase-4.5/ASSUMPTIONS.md` decision: chunks-file shape from
  `templates/overlay/sprint-loop-chunks-example.template.json`.
- `phase-4.5/CI-GATE.md` chunks-file convention: same.
- `phase-4.5/BUILD-NOTES.md` chunk-7 / chunk-9 dry-run recipe:
  per-pilot overlay.
- `phase-4.5/KNOWN-ISSUES.md`: KN-H11..H-19 KNI entries; test
  count 80/80.

- `tests/test_sprint_loop.py`:
  - **Behavioral pin** `test_unattended_writes_checkpoint_on_refusal_g7`
    replaces the source-grep `test_unattended_writes_checkpoint_on_refusal_g7`.
  - **Behavioral pin** `test_skip_reconcile_still_enforces_5_3_g8`.
  - **Behavioral pin** `test_no_dry_run_coercion_h2_h14`.
  - Substring-pins in `test_sprint_invocation_skill_is_small_and_trigger_focused`
    upgraded to allow 30-160 lines and assert absence of
    `tools/sprint-loop.py` + `examples/sprint-loop-` substrings.

## Decision 1 — did the operator entrypoint actually collapse?

After chunk-13:

- The only path RUN-PROMPT teaches operators.
- The only path the cursor `.mdc` cursor front-ends (after
  re-generation).
- The only path EXIT-CHECKS (5) executes.
- The only path KN1's reproduction uses.
- The framework CLI is documented as "debug-only" everywhere it
  appears.

**Question:** is the collapse real? Are there stragglers — e.g.,
spot checks for `examples/`-style references I missed, or the
meta-skill's digest index still pointing at products in
`examples/`?

## Decision 2 — is the live gate semantics honest?

Behavioral tests now exercise the gate. After chunk-13:

- `cfg.dry_run` is independent of `--non-interactive`.
- §5.3 enforcement is shared by `--non-interactive`,
  `--unattended`, `--skip-reconcile`, `--gate-auto-decide`.
- `--unattended` writes a checkpoint on refusal.
- `--dry-run` is genuinely side-effect-free (per gating; chunk-13
  leaves dry-run path untouched on purpose).
- The §15 truth-table in RUN-PROMPT covers all four modes
  (Act-1, Act-2 dry, Act-2 non-interactive, Act-2 unattended,
  Act-2 skip-reconcile).

**Question:** is there a code path that still slips past §5.3?
Did the H-2 refactor miss the `load_checkpoint` resume path?
Did the gate ever read `sys.argv` as a fallback?

## Decision 3 — does the §15 demo-delta hold?

The original §15 claim: "the transition between Act 1 and Act 2
is the demo's delta. Without Act 2 the structural guarantees are
aspirational." 

**Question:** is that claim now observable end-to-end via
`bin/run-sprint --dry-run --non-interactive`? Specifically:

1. Does the simulated ACCEPT in the dry-run mode still print the
   §7-silent-green banner, with the overlay-style message that
   *does not* claim "real verdict" semantics? (We need the
   simulator honest, not silent.)
2. Does the per-pilot overlay actually translate
   `--dry-run --non-interactive` into a dry_run-on, gate-auto-on,
   unattended-off call that exercises the simulator's full path
   back through reconcile? (run with the actual overlay + a real
   config to verify.)
3. Is the meta-skill's rehydration-trigger table in
   `skills/adversarial-sprint/SKILL.md` consistent with the new
   feature surface (was §15 itself added as a trigger row, since
   §15 framing is the operational demarcation)?

## Method of response

Same shape as pass-r1, pass-r2, pass-r3. Numbered findings
**J-1** through **J-N** (use **J-** to keep these distinct from
F-*, G-*, H-*). Last line: one of
`ACCEPT-WITH-NITS` / `ACCEPT` / `REJECT` / `REJECT_TEST` /
`REJECT_IMPLEMENTATION` / `HUMAN_DECISION`.

## Sufficient evidence

- `phase-4.5/adversarial_review/panel-findings-r3.md` — the
  findings pass-r3 raised at the prior commit.
- `phase-4.5/RUN-PROMPT.md` §15 framing + truth-table.
- `phase-4.5/KNOWN-ISSUES.md` §KN-H11..H-19.
- `tools/sprint-loop.py` (the four `cfg.dry_run`/`gate_auto_decide`
  lines + the gate function).
- `tools/sprint_loop/config.py` (the new Config fields and CLI flags).
- `templates/overlay/bin/run-sprint` (the argv walker).
- `skills/{adversarial-sprint,sprint-invocation}/SKILL.md`.
- `tests/test_sprint_loop.py` (80 tests; behavioural pins).

Do NOT read the diff in detail. Focus on the three decisions.
