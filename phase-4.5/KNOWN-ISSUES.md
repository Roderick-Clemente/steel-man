# Phase 4.5 — Known issues & clean-null results

Per `OPERATING-RULES.md` §12: unexercised safety paths are **named
gaps**, not phase blockers. Per PRD §13: a clean null result is
valid data — "models disagree at least once" is NOT a success gate.
This file records BOTH categories so the next operator has the full
unexercised-path picture.

Each entry: **what** (path / mechanism / invariant) + **why not**
(rationale for the null / gap classification) + **reproduction**
(if applicable) + **when to fix**.

## Clean-null results — unexercised paths recorded per §12

### KN1. End-to-end pilot run not exercised in this branch

- **What:** the runner's full loop has been dry-run-tested against
  a synthetic chunk spec but has NOT been exercised against a real
  pilot. The 80 pytest tests cover unit + integration paths under
  the runner (chunk-13 close); they do not exercise the per-chunk
  inner loop's calls to
  `droid exec`, `lock.py`, `verify-green.py`, `local_backend.py`
  end-to-end against a real pilot repo.
- **Why not (rationale for null):** the runner intentionally falls
  short of "execute a sprint" in this branch because: (a) the pilot's
  droid CLI subscription state was not in-scope for the build;
  (b) OPERATING-RULES §17 capacity envelope says "name the next 1–3
  deliverables" — running a full pilot is a separate deliverable.
- **Reproduction (pass-r3 H-7 fix; chunk-13):** the deleted
  `<PILOT_REPO>/examples/sprint-loop-{config,chunks-example}.json`
  files were moved in chunk-12b to `templates/overlay/*.template.json`.
  Per the panel's prescription, the overlay — not the framework
  runner — is the operator-facing entrypoint:
  `./run-sprint --dry-run --non-interactive` exercises the
  dry-run path. Framework-level equivalent (debug-only): `python3
  tools/sprint-loop.py --config templates/overlay/sprint-loop-config.template.json
  --chunks-file templates/overlay/sprint-loop-chunks-example.template.json
  --dry-run --non-interactive`.
- **When to fix:** when an operator session is set up to drive
  QuantumBank through this branch (Phase 4.5 close-out). Treat the
  actual pilot run as Phase 4.5's exit criterion per PRD §11.

### KN2. Reconciliation rotation under real disagreement not exercised

- **What:** the runner's reconcile-loop is set up to loop back to
  the planner up to `--max-review-rounds` times. Only the dry-run
  happy path has been exercised.
- **Why not:** PRD §13 is explicit: "manufactured disagreements" is
  exactly the wrong response to "models disagree at least once."
  Phase 4's review used real disagreement corpora (Phase 2
  amendments, Phase 3.1 panel-split, Phase 3.2 orchestrated REJECT).
  Phase 4.5 should mine those existing corpora before forcing new
  disagreements; that mining is named in ROADMAP-REVIEW.md Backlog D.
- **Reproduction:** the runner code path is
  `tools/sprint-loop.py:main` → `reconcile_human_gate` → reject → planner.
- **When to fix:** Backlog D — calibration backlog, not a Phase 4.5
  gate.

### KN3. `--validation-backend=ci` raises NotImplementedError per the prompt's "interface only"

- **What:** the CIBackend is a stub raising NotImplementedError with
  a clear, refusing message.
- **Why not:** the prompt is explicit ("do not build the CI side yet").
  Building CIBackend prematurely is the §6 scope-shift mistake; the
  H-CI experiment (ROADMAP-REVIEW.md Backlog E prerequisite) is the
  right gate before further investment.
- **Reproduction:** `python3 tools/sprint-loop.py --validation-backend=ci ...`
  fails fast with `NotImplementedError`.
- **When to fix:** Backlog E. The CI WORKFLOW (Track C) is a separate
  artifact (`.github/workflows/adversarial-sprint-ci.yml`) that
  inlines `local_backend.py` + `orchestrate-review.py` directly
  instead of going through the runner's process.

### KN4. Bundled-MCP server invocation not exercised

- **What:** the runner's per-chunk step reads the bundle from disk;
  it does NOT call an MCP server to fetch it. The MCP integration is
  a future slice (`tools/orchestrate-review.py` has support; the
  runner does not exercise it).
- **Why not:** PRD §11 Track B says: "Switching backends is a flag."
  The MCP server is one such backend (the future CIBackend might
  use one). Until CIBackend is actually built, MCP stays unused.
- **When to fix:** with KN3 (CIBackend) + ROADMAP-REVIEW.md
  Backlog E ("flavor (b) Harness-native").

### KN5. The runner does not auto-extract chunks from the plan document

- **What:** the runner accepts `--chunks-file <path>`. Auto-extraction
  from the planner's markdown would mean parsing free text.
- **Why:** PRD §5.5 says chunking AFTER test design; the planner-or-human
  decision is real. Auto-extraction hides a §7 silent-green trap
  (the parser could "accept" the wrong plan). Combined decision
  (structured input + future parser) deferred.
- **Reproduction:** `python3 tools/sprint-loop.py --config <cfg>.json` (without
  `--chunks-file`) errors with "FATAL: --chunks-file is required."
- **When to fix:** as part of Backlog D / Phase 6 hardening, with a
  regex-driven chunk-extraction that maps "## Chunk X — <scope>" sections
  in the plan document into ChunkState objects. Until then, the operator
  maintains the chunks-file.

### KN6. The CI workflow's droid CLI install is best-effort

- **What:** `.github/workflows/adversarial-sprint-ci.yml` warns
  (non-blocking) when droid is not on the runner image.
- **Why:** GitHub-hosted runners do NOT ship droid; the install path
  is platform-specific. The runner's `--strict-droid-required` flag
  is an optional toggle (Coding later if needed).
- **Reproduction:** a GitHub-hosted run of the workflow surfaces a
  warning in the install step; the subsequent `droid --version`
  check fails the job.
- **When to fix:** when a stable upstream-tarball URL is documented,
  OR a Factory-side managed-runner image is in GA. Until then:
  self-hosted runner with pre-installed droid is the working path.

### KN7. Auto-chunking state marker overwrites in mid-loop

- **What:** the runner's `commit_chunk_change` dry-run path emits
  structured commit-message output but does NOT mutate git. Each
  per-chunk evidence sub-dir IS a real artifact of the framework
  repo (committed on the audit branch when the run completes).
- **Why not:** dry-run should not commit; the operator must opt in
  via `--no-dry-run`.
- **Severity:** zero (by design) — the dry-run path is documented.

### KN8. The runner does not produce a Human Decision Packet format file

- **What:** the runner checkpoints RunState to JSON when a chunk
  pauses at HUMAN_DECISION. Per PRD §6, a "decision packet"
  explains what changed, why the run paused, the competing
  positions, evidence, cost of delay, available actions. The JSON
  checkpoint has the run state but is not a decision packet in the
  narrative sense.
- **Why not:** the prompt's "human decision packet" was described
  generically. A narrative packet on top of the JSON checkpoint
  is a future follow-on (potentially Phase 7's
  operator-cost-compression work).
- **When to fix:** Phase 7 (post-MVP pain-point-driven).

## Residual gaps that the build intentionally deferred

### KNR1. Phase 0.5 / Phase 1 invalid-RED fixtures

- **What:** `phase-1/fixtures/invalid-red/` should hold 3-4
  fail-mode RED fixtures used in Track A2 of ROADMAP-REVIEW.md.
- **Why not deferred:** ROADMAP-REVIEW Track A is parallel and
  non-gating. Phase 4.5 did not block on Track A items.
- **When:** Track A's own commit window.

### KNR2. PRD §15 "close the laptop" durability

- **What:** PRD §15 Act 2 promises "kick off, close the laptop, come
  back to a completed sprint." The runner checkpoints RunState and
  has `--resume-from` but the close-laptop durability is not
  demonstrated end-to-end.
- **Why deferred:** save the laptop claim for a real pilot run
  (KN1) — it's the same machine that needs to be tested.
- **When:** after KN1's pilot run lands and the human picks a
  representative resume scenario.

### KNR3. Hidden-test corpus

- **What:** PRD §13 efficacy evaluation requires hidden tests.
- **Why deferred:** a separate operator session; not Phase 4.5 scope
  per PRD §3 v1 non-goal ("rebuilding Factory Missions, Spec Mode,
  model selection, hooks, Droid Shield, or CI").

### KNR4. `--skip-reconcile` was historically an unconditional auto-accept

- **Status (chunk-12a):** RESOLVED. The chunk-12a fix runs
  `_enforce_5_3_preconditions` inside the `--skip-reconcile`
  branch — open blocker|high findings now SystemExit(4); no bound
  APPROVE on `plan_sha256` now SystemExit(5). On refusal, the
  runner writes a checkpoint to `phase-4.5/build-evidence/<run-id>/checkpoint.json`
  before raising, so an operator can `--resume-from` into a re-run.
- **What was previously deferred:** panel-finding F-6 (chunk 10)
  deferred deprecation in favor of `--accept-on-dual-accept` named
  for KNR4. The fix in chunk-12a kept the surface but made it
  machine-check-safe; deprecation remains an open DX question
  (panel-finding G-8 marked the previous deferral note as stale).
- **Test:** `test_skip_reconcile_still_enforces_5_3_g8` in
  `tests/test_sprint_loop.py`.

## Surface-level ergonomics (recorded, not gating)

### KNE1. Dry-run envelope has UNKNOWN verdict for plan reviewers

- **What:** when `--dry-run` runs `run_plan_reviewer`, the verdict
  parser returns `UNKNOWN` because the synthetic envelope's `result`
  text is `[dry-run] No droid exec fired. Planned call: ...` — no
  `VERDICT: ...` line.
- **Why:** dry-run is honest about NOT simulating model content.
  Dry-run does not pretend to validate.
- **Workaround:** real runs produce real verdicts. The unknown-verdict
  in dry-run does NOT block the auto-accept at the reconcile gate.

### KNE2. Round indicator off-by-one in the reconcile banner

- **What:** `_write_reconcile_packet` uses `plan_round + 1` to render
  "round N / max" so the first reconcile shows "round 2 / max 2"
  instead of "round 1 / max 2".
- **Severity:** cosmetic.
- **Fix:** `sed 's/rs.plan_round + 1/rs.plan_round/'` in the banner.

### KNE3. "Acceptance gate" line in the prompt templates hints at exact implementation

- **What:** the executor + test-designer role prompts mention
  "must hold observable from the test_id AND full suite" — this
  could be tightened against the §13 rule, which says the executor
  is not given the implementation. Reading the prompt again against
  §13: it says "the runner runs verify-green.py" — not "use this
  fixture." Concluded OK; flagged here in case future regression.

### KNE4. The CI workflow's chunk-id regex depends on PR title convention

- **What:** the workflow reads `[chunk:<id>]` from the PR title to
  extract the chunk id. PRs that don't follow the convention are
  blocked with an error annotation.
- **Workaround:** Retitle the PR with `[chunk:<id>]` prefix.
- **Why:** enforces a stable contract — the runner needs a chunk id
  to gate against. Documented in `phase-4.5/CI-GATE.md §3`.

### KN-H11. §15 truth-table in RUN-PROMPT lacks the rows the §15 claim rests on

- **Status:** chunk-13 partial fix (expanded truth-table to 5 columns).
  The remaining gap (pass-r3 H-11): the table is in the operator-facing
  RUN-PROMPT only; the meta-skill `skills/adversarial-sprint/SKILL.md`
  digest doesn't carry a §15 row, so a context-compaction event can drop
  it. Next chunk-14: pin the operator-facing truth-table in the meta-
  skill's §15 row of the digest.
- **Fix recipe:** Copy the RUN-PROMPT §15 truth-table markdown into
  `skills/adversarial-sprint/SKILL.md` as a §15 row; have
  `tests/test_sprint_loop.py::test_skill_md_has_§15_truthtable_row_h11`
  grep the canonical skill for it.

### KN-H12. `--skip-reconcile` and `--dry-run --non-interactive` are not equivalent

- **Status:** chunk-13 partial fix (H-12 collapse into one gate code
  path; H-2's dry_run coercion removed). Remainder: the dry-run branch
  still rubber-stamps before §5.3, while `--skip-reconcile` does run
  §5.3 first; that is the right asymmetry (dry-run is honest about
  being a simulator), but RUN-PROMPT §15 already explains it.
- **Honest accounting:** the §15 truth-table row for `--dry-run` and
  the row for `--skip-reconcile` are now visually adjacent in RUN-PROMPT
  so operators see the asymmetry at a glance.

### KN-H13. `--no-dry-auto-decide` was unreachable

- **Status:** RESOLVED (chunk-13). The flag is wired into main's
  argparse and into reconcile_human_gate as `no_dry_auto_decide`. Pin
  test: `tests/test_sprint_loop.py::test_help_surface_includes_no_dry_auto_decide_h13`
  (added in chunk-13) greps the synth help page for the flag.

### KN-H14. Gate-mode detection read `sys.argv`, not parsed argv

- **Status:** RESOLVED (chunk-13). Behavioral tests now pin the gate
  path: `test_unattended_writes_checkpoint_on_refusal_g7` and
  `test_skip_reconcile_still_enforces_5_3_g8` exercise the gate
  with explicit kwargs; `test_no_dry_run_coercion_h2_h14` confirms
  the §5.3-precondition met + live path returns ACCEPT without
  mutating rs.dry_run.

### KN-H15. Signing-key refusal is late, not preflight

- **Status:** deferred to chunk-14. The backends.py:252-264 refuse
  fires at step 7 of the per-chunk inner loop; by then planner +
  reviewers + executor + verify-green have all run. Need a preflight
  `if not dry_run and not EVIDENCE_SIGNING_KEY raise SystemExit`.
- **Workaround:** the operator sees the `[unattended] refused (exit
  <code>); checkpoint at <path>; resume with --resume-from` pattern
  but it's too late — model spend has happened. Chunk-14 should move
  the check to a preflight at main() startup, parallel to the
  family-guard preflight at sprint-loop.py:1108.
- **Fix recipe:** Add `_assert_signing_key_preflight(cfg)` called
  from main(\u2026) immediately after `guard_in_uncommitted_state`.
  Fail closed unless `--no-fail-closed`.

### KN-H16. `--unattended` checkpoints only §5.3 refusals

- **Status:** chunk-13 partial fix (the §5.3 checkpoint-on-refusal
  path is now BEHAVIORALLY pinned in test_unattended_writes_checkpoint_on_refusal_g7).
  Remainder: persistent droid invocation failures
  (run_planner:238-243 / run_plan_reviewer:359-364) raise RuntimeError
  *without* writing a checkpoint. Drift remains — chunk-14 fix recipe:
  add a `try/except RuntimeError\u2192write_checkpoint` around the chunk
  inner loop in main(), before the `return 2` propagation. Mirror
  spacecraft-style fault isolation: every failure shape writes a
  checkpoint that the operator can resume from.

### KN-H17. Test count "79" appeared nowhere + chunk-12b had green on unverified work

- **Status:** RESOLVED (chunk-13). Test counts reconciled to 80/80
  at chunk-13 close. Pin: `tests/test_sprint_loop.py` reports
  `80 passed`; `phase-4.5/{KNOWN-ISSUES,EXIT-CHECKS,BUILD-NOTES}.md`
  all show 80/80.

### KN-H18. bin/run-sprint install recipe said `tools/install-overlay.sh` which did not exist

- **Status:** RESOLVED (chunk-13 H-3). The recipe in the script's
  banner is now the actual `cp` commands, no `install-overlay.sh`
  reference. Pin test: `test_run_sprint_overlay_template_exists_g3`
  plus a new line-count check on the recipe body.

### KN-H19. Residue

- `.gitignore:11` and `:20` both carry `!.factory/skills/**` (duplicate;
  test ``test_factory_skills_unignored_in_gitignore_g4`` passes on
  either). Defer to chunk-15 cleanup.
- `droid.py:_retry_delay` (`:203-205`) is dead code (the live loop
  computes its own `retry_delay_seconds * (2 ** (attempts - 1))` at
  `:346`). Defer to chunk-15 cleanup.
- `skills/adversarial-sprint/SKILL.md` digest index vs body §1-\u00a718
  vs §19. Index-table lists \u00a719, body still says §1–§18 in two places.
  Defer to chunk-14 as a content-only fix.
- `droid.py:361` treats `output_tokens == 0` as transient, retrying a
  legitimately empty completion at full cost. Defer to chunk-15.
