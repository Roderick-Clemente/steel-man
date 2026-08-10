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

---

## KN-J* — pass-r4 panel findings at chew-13 close (47bdceb)

**Status:** Phase 4.5 = PAUSED (chunk 14 deferred until after the new-PRD
dogfood). Pass-r4 returned REJECT_IMPLEMENTATION with 20 J-findings;
operator chose to ship chunk-13 as the pause-point and dogfood the new
PRD on the framework-as-is rather than ship chunk-14 first.

When returning to Phase 4.5, the chunk-14 minimum set per pass-r4 is
J-7 BLK + J-8/9/10/11/15/16 HIGH. The MEDs and LOWs slot below
in priority order.

### KN-J7 — BLOCKER — §15 truth-table was NOT expanded; two KNI entries claim it was

- **What:** KN-H11 + KN-H12 (chunk-13) state that the §15 truth-table
  in RUN-PROMPT.md expanded to five columns covering all four modes.
  Pass-r4 finds the doc unchanged; the KNI entry is aspirational,
  not observational.
- **Why deferred:** operator chose to dogfood-first rather than ship
  chunk-14. The §15 truth-table as it stands today has three
  columns (`Act 1 / Act 2 live / Act 2 dry-run`), which does
  NOT distinguish `--non-interactive` / `--unattended` /
  `--skip-reconcile` — pass-r4 calls this the "real-behaviour map"
  not reflecting "actual code paths." Documented gap.
- **Honest accounting:** KN-H11/12 advisory text in this KNOWN-ISSUES
  is corrected below.
- **Fix recipe (chunk-14):** rewrite the truth-table to 5 columns
  (Act 1 / Act 2 live / Act 2 dry / Act 2 non-interactive / Act 2
  unattended), each row in the table is a behavioural property
  (git commits, model spend, family separation, signing-key), and
  add KN-H11 entry that does NOT claim the table was previously
  expanded.

### KN-J8 — HIGH — `--help` documents the H-2 alias as the intended contract

- **What:** the synthetic `_format_build_config_help_synthetic`
  function in main() emits a flag-surface help that documents
  `--non-interactive` with help text "Bypass the human reconcile
  gate stdin pause. Maps to gate_auto_decide=True." Pass-r4 calls
  this "the H-2 bug-as-contract" because the operational claim has
  been: *previously* `--non-interactive` was an alias for
  `dry_run=True` (always), and chunk-13's help text asserts the
  opposite without renaming the flag.
- **Fix recipe (chunk-14):** make the help text explicit that
  `--non-interactive` REQUIRES live mode (cfg.dry_run stays
  False) and prints the refusal banner if §5.3 fails. Same for
  `--skip-reconcile` and `--unattended`.

### KN-J9 — HIGH — `--dry-run --resume-from<path>` still mutates git history

- **What:** chunk-13 attempted to fix H-5 (load_checkpoint
  restores dry_run / plan_reviewer_verdicts / plan_round). Pass-r4
  tested the live path: `--dry-run --resume-from <path>` still
  runs commit_chunk_change with rs.dry_run defaults to False even
  though cfg.dry_run is True. The git commit lands and the
  branch advances; the chunk's audit trail attests `chunk_id`
  was executed under a simulated envelope.
- **Fix recipe (chunk-14):** in commit_chunk_change, branch on
  `cfg.dry_run`, NOT `rs.dry_run`. The distinction is load-
  bearing; rs.dry_run is only the **post-resume** snapshot,
  cfg.dry_run is the **mode** the operator asked for.

### KN-J10 — HIGH — `--resume-from` drops every RoleAssignment + family guard

- **What:** load_checkpoint restores RunState, but the family-guard
  preflight at main() runs BEFORE load_checkpoint
  (`sprint-loop.py:1108`). Per pass-r4, the resumed run never calls
  preflight_family_guard again, so a post-resume run with a
  cross-family validator panel sails through; §17.2 silenced.
- **Fix recipe (chunk-14):** move preflight_family_guard to be
  re-run AFTER load_checkpoint. Should require cfg to be
  sufficient on the resume path (or fail closed).

### KN-J11 — MED — `--resume-from=<path>` now fails at parse (H-4 inverted)

- **What:** chunk-13's cfg_argv stripping removed `--resume-from`
  and `--resume-from=` but kept `--resume-from <path>` to be
  parsed by build_config, which doesn't recognize the flag —
  parser.parse_args (strict) raises SystemExit(2) on unknown flag.
  Operators who follow the documented `--resume-from <path>`
  form (chunk-13 BUILD-NOTES.md:128) hit a parse error.
- **Fix recipe (chunk-14):** in main()'s peer_argv walker
  (currently strips `--resume-from <path>` correctly), but
  ALSO emit `--resume-from=<path>` to peer_argv as a form
  build_config can absorb. Or add `--resume-from` to
  build_config's parser as a no-op that just keeps it alive.

### KN-J12 — MED — three pin tests cited in the build record do not exist

- **What:** chunk-13 commit body cites three new tests by name:
  - `test_help_surface_includes_no_dry_auto_decide_h13`
  - `test_skill_md_has_§15_truthtable_row_h11` (typo in name)
  - one more referenced in KN-H14. None exist in
  tests/test_sprint_loop.py as of commit 47bdceb.
- **Fix recipe (chunk-14):** write the actual tests they should
  reference and lock them in the canonical test file. Pin the
  build record (BUILD-NOTES.md, KNOWN-ISSUES.md, panel-findings-
  r3.md, panel-findings-r4.md) to actual file presence.

### KN-J13 — MED — flag-help synthetic parser has already drifted from build_config

- **What:** `_format_build_config_help_synthetic` in main() is a
  second source of truth for the flag surface. It defines
  Config-side flags by hand. Pass-r4 found that
  `--create-pr`, `--signing-key-env`, `--security-allowlist`,
  `--security-baseline` were NEW flags added to build_config
  in chunk-13 but not reflected in the synthetic help.
- **Fix recipe (chunk-14):** refactor build_config to expose
  its internal parser; use that for the synthetic. OR document
  the synthetic as "in-progress" and add a test that compares
  the two surfaces for drift.

### KN-J14 — MED — `tools/sprint-loop.py` defines `main()` twice

- **What:** an earlier chunk-11 edit left a half-finished main()
  in the file with `_runner_argparser` and friends, then chunk-12
  truncated mid-function and the "second" main() (lines ~1066+)
  contains the actual current implementation. The first is dead
  but parseable code pays the file size.
- **Fix recipe (chunk-14):** localize the dead code and either
  delete it or move it to `tools/conventions/_runner_argparser_spec.md`
  as a historical artefact.

### KN-J15 — HIGH — dry-run COMPLETED banner reports branch + commit count git refuses

- **What:** the dry-run "would commit" path increments
  `rs.commit_count` and sets `rs.output_branch` to a synthetic
  name. The COMPLETED banner prints `branch: factory/sprint-
  <run-id>-dry-run` and `commits: <N>`, but git status on
  _REPO_ROOT shows zero new commits. Pass-r4 calls this a lie
  in the §15 contract.
- **Fix recipe (chunk-14):** dry-run's banner should report
  `(simulated)` markers next to mutable surfaces, OR a
  `--dry-run-quiet` flag silences the banner.

### KN-J16 — HIGH — H-2 behavioural pin is vacuous

- **What:** `test_no_dry_run_coercion_h2_h14` constructs a
  RunState with `gate_auto_decide=True` + plan_reviewer_verdicts
  pre-bound to APPROVE + `plan_sha256` matching, calls the
  gate, and asserts `rs.dry_run is False`. Pass-r4 found the
  test passes whether or not the gate mutates `rs.dry_run`,
  because the test inputs are NOT the node where the bug fires.
  The bug fires when *the orchestrator* (main) sets
  `cfg.dry_run = ns.non_interactive` — which this test doesn't
  drive via main().
- **Fix recipe (chunk-14):** route the test through a small
  helper `make_runner_argv_to_cfg(argv)` and assert
  `cfg.dry_run is False` after construction. Behavioral pin
  matches the actual code path.

### KN-J17 — MED — H-9 fix is dead code on every documented invocation

- **What:** commit_chunk_change's `rel.startswith("..")` check
  catches the case when `evidence_output_dir` is outside
  _REPO_ROOT. Pass-r4 found the runner's documented invocation
  goes through `cfg.evidence_output_dir = ...` from `--evidence-output-dir`
  CLI flag, but main()'s override only fires AFTER the cfg
  is already populated from build_config's default. The
  runner's documented `bin/run-sprint` overlay path passes
  `--evidence-output-dir` to the runner, but build_config wouldn't
  see it because cfg_argv stripped it. Result: documented path
  always falls into the default-relative case.
- **Fix recipe (chunk-14):** thread `--evidence-output-dir`
  through cfg_argv BEFORE the cfg_argv walker strips it; or
  remove the strip entirely.

### KN-J18 — MED — run-level checkpoint commit is one state stale

- **What:** chunk-13 wrote the run-level checkpoint BEFORE
  commit_chunk_change; commit_chunk_change then force-adds the
  checkpoint to the chunk's commit. Pass-r4 found the order of
  operations means the chunk's commit captures the
  *pre-completion* state, not the post-completion state.
  Subsequent writes to that checkpoint after commit_chunk_change
  don't reach any commit.
- **Fix recipe (chunk-14):** make commit_chunk_change accept
  a callable that produces the checkpoint, OR write the
  post-state checkpoint explicitly at run-end. Pin a behavioral
  test that reads back the audit-branch's latest checkpoint
  and verifies it matches the *final* RunState.

### KN-J19..J20 — LOW — meta-skill §15 row missing + test-count reconciliation

- **What:** KN-H11 deferred the meta-skill §15 row to chunk-14.
  Test-count 80/80 is claimed in EXIT-CHECKS.md, BUILD-NOTES.md,
  KNOWN-ISSUES.md, but PASS-r4 surfaced that the chunk-13
  BUILD-NOTES inventory entry actually describes the chunk work
  using past-tense is too compressed to be reconciled. KN-J20
  bundles these.
- **Fix recipe (chunk-14):** add a §15 row to the meta-skill
  digest + bump BUILD-NOTES.md to describe chunk-13 in plain
  prose. Cross-check test-count claims against pytest's
  reported count.


---

## KN-A* — EOS pilot self-assessment findings (new, post-pass-r4)

**Source:** `phase-4.5/EXTERNAL-DOGFOOD-SELF-ASSESSMENT.md`. Cited
verbatim from the EOS pilot agent's hand-drafted
`DOGFOOD-SELF-ASSESSMENT.md` after a single `--dry-run --non-
interactive` invocation against a new PRD.

### KN-A-1 — `bin/run-sprint` fired 0 real model calls in the EOS pilot

- **What:** every runner-emitted envelope in the pilot contained
  `"[dry-run] No droid exec fired. Planned call: droid exec --model ..."`.
  The cross-family PRD review (grok-4.5 + gemini-3.1-pro-preview)
  fired 32 findings + both REJECT_PLAN + 6 reconciled fixes — but
  all of that was operator-driven (ad-hoc `run-with-model.sh`
  invocations), NOT runner-driven.
- **Why:** the framework prescribes a wiring-test dry-run before
  spending real model credits; the operator chose "dry-run first,
  pause before live" per AskUser. Live mode was blocked by the
  conjunction of: (a) `EVIDENCE_SIGNING_KEY` unset → §7 fail-closed;
  (b) D-1 (verify-green.py pytest-only, PRD stack was Next.js);
  (c) D-5 (no Node/npm on host). The operator pivoted to
  hand-building a Python sample app rather than unblocking the
  runner, so the runner's builder path was never given a real
  test.
- **Honest self-criticism (from the EOS pilot agent):** "I could
  have set a throwaway signing key to at least exercise the real
  planner/reviewer calls before the verifier blocked. I didn't
  circle back to that once the goal became 'get an app.'"
- **Honest operator takeaway:** Phase 4.5 closeout cannot
  advertise "runner as builder" until a live run is recorded in
  the build-evidence chain with branches + commits + signed
  envelopes.
- **When to fix:** before chunk-15 close (telemetry/audit join
  + live-path preconditions checklist together admit "live run
  possible"). Otherwise chunk-15's "first-class runner step"
  claim is also aspirational.

### KN-A-2 — telemetry/banner run_id mismatch (audit trail cannot join banner)

- **What:** the dry-run COMPLETED banner printed
  `run_id=r-phase45-...`, while the telemetry row index wrote
  `run_id=r-dry-run-...`. They are distinct strings, so an
  operator cannot join the banner's "DONE" attestation to the
  telemetry's per-row records. Pass-r4 EOS reproduces this from
  a clean pilot repo.
- **Severity:** §11 audit-trail class violation, not a UI nit.
  This is silently-green-shaped: the operator trusting the
  banner cannot verify the trail.
- **Fix recipe (chunk-14):**
  1. Move `run_id` to a single module-level symbol imported
     across `tools/sprint_loop/__init__.py` (or
     `tools/sprint_loop/runner_id.py`).
  2. `commit_chunk_change(...)` writes the same `run_id` symbol
     to the COMPLETED banner args AND to the telemetry row
     `run_id` field.
  3. Add behavioral pin in `tests/test_sprint_loop.py`
     asserting both surfaces emit the SAME `run_id` string for
     a given chunk.
  4. Rollback §11 DoD wording in `phase-4.5/RUN-PROMPT.md` and
     `phase-4.5/EXIT-CHECKS.md`: replace "checkpoint.json
     committed" with "checkpoint.json AND telemetry row index
     share a run_id."

### KN-A-3 — post-chunk adversarial code review was a GAP (never ran)

- **What:** of the 9 §11 steps, step 8 — cross-family review of
  code mutations — was marked GAP by the EOS self-assessment.
  Author == validator. The runner does NOT currently fire a
  post-chunk review on the diff the chunk produced.
- **Severity:** §11 chain is broken without it: every other step
  can produce output the runner vouches for, but the actual
  mutation never gets an independent reader.
- **Fix recipe (chunk-15 — promoted from "Phase 4.7 idea" to
  first-class deliverable):**
  1. New step, AFTER `commit_chunk_change(...)`: read the chunk's
     diff, format as a "REVIEW-CODE" prompt that lists the patch
     hunks + the spec the chunk claimed alignment with.
  2. Fire two cross-family `droid exec` reviewers per the chunk-15
     cross-family invariant (grok-family + gemini-family). Each
     emits REJECT_PLAN/CONDITIONAL/APPROVE bound to the diff sha
     + spec sha pair.
  3. REJECT_PLAN-bound to diff sha → block the chunk commit
     (SysExit 7).
  4. CONDITIONAL → write a candidate-fix note to the chunk's
     evidence sub-dir; do not block the commit unless
     `cfg.post_chunk_review_strict`.
  5. Dual APPROVE → chunk closes; continue.
- This nullifies the previously-proposed Phase 4.7 scope. Phase
  4.7 is relabeled "telemetry/reporting polish" — not a runner
  step.

### KN-A-4 — live mode is structurally unreachable from a clean checkout

- **What:** live mode requires the conjunction of FOUR unrelated
  preconditions to all hold simultaneously:
  1. `EVIDENCE_SIGNING_KEY` env var set;
  2. a contract reader wired in (`tools/adapters/test_runner.py`,
     Backlog E);
  3. the pilot's toolchain present on the runner host
     (`pilot.cls.detect-toolchain`);
  4. the wiring-test dry-run transition WAS recorded (i.e. the
     operator executed `--dry-run --non-interactive` to GREEN
     before flipping to live).
  Failure of any one blocks live entirely. Each was true in
  isolation during past pilots but not in conjunction.
- **Why not:** PRD §11 says live mode = "kick off, close the
  laptop." PRD §7 says signing key is fail-closed. No
  precondition-checklist exists to actually predict this.
- **Fix recipe (chunk-14 + chunk-15):**
  1. New Config field `cfg.live_path_preconditions: dict` (4
     boolean slots).
  2. New RUN-PROMPT Step 0 (BEFORE the wiring-test dry-run is
     even attempted): operator-visible `live_path_preconditions_
     check` surface prints green/red for each of (signing-key,
     contract-reader, toolchain, prior-dry-run). The printout is
     itself a behavioral pin target.
  3. `--dry-run --non-interactive` now exits with code 1 if
     ANY precondition is not met, with a refusal banner naming
     the missing pieces (not a generic "refused").

### EOS pilot §11 step → driver table (preserved here for future role)

| §11 step | Driver | Evidence kind |
|---|---|---|
| 1. Pre-chunk PRD review | HAND (ad-hoc) | operator-routed |
| 2. chunks.json | HAND | operator-authored (1285 lines) |
| 3. Plan for chunk 1 | GAP — stub | `[dry-run]` envelope |
| 4. Plan-review (§5.3) | GAP — stub | both envelopes "No droid exec fired" |
| 5. Reconcile gate | RUNNER | auto-accepted (--non-interactive) |
| 6. Chunk-1 inner loop | GAP — executor fabricated | commit_sha `000…0`, tests_passed:1 |
| 7. Chunk commit | HAND | 34b86e3, 1285 lines, plain message |
| 8. Cross-family review of code | GAP — author == validator | never ran |
| 9. Telemetry | partial — rows present, run-id not joined | banner ≠ telemetry |

**Verdict (from the EOS pilot agent):** "The pilot validated the
framework's review philosophy and its dry-run plumbing. It did not
validate the runner as a builder or as an act-2 structural
guarantee. The runner's contribution to the actual deliverable: 0
lines produced, 0 lines reviewed."

---

## Backlog E — non-Python pilot support (new, post-dogfood)

**Status:** opened by external pilot dogfood (`Roderick-Clemente/evan-os`)
at pause commit 90f08dd. **P1 in `phase-4.5/EXTERNAL-DOGFOOD-HANDOFF.md`.**

- **What:** the runner's RED→GREEN gate (`phase-1/scripts/{valid-red,verify-green}.py`)
  hard-codes `python -m pytest`. Any non-Python pilot (Next.js/TS, Go,
  Rust, etc.) cannot complete a chunk; chunks must lie about their test
  shape to fit the runner.
- **Why not yet:** the framework was built around a Python pilot, and
  the test-runner adapter was deferred to keep Phase 4.5 bounded.
- **Acceptance (per the external dogfood handoff):**
  1. `tools/adapters/test_runner.py` maps `pilot_test_runner` config
     (`pytest|vitest|jest|<extensible>`) to command + normalized
     returncode / stdout / stderr.
  2. Threaded through `config.py` → `RunState` → `per_chunk.py` →
     `valid-red.py` / `verify-green.py`.
  3. `pilot_test_runner: pytest` keeps the 80/80 build green.
  4. New unit tests cover vitest/jest command construction + JS
     pass / fail / invalid-RED classification.
  5. A JS pilot (e.g. `Roderick-Clemente/evan-os`) can complete one
     chunk driven by the runner proper (not hand-executed).
- **Fix recipe (single-chunk target):**
  - chunk-14 candidate (`factory/chunk-14-pilot-test-runner-adapter`):
    add `Config.pilot_test_runner: str = "pytest"`. New module
    `tools/adapters/test_runner.py`. `valid-red.py` and `verify-green.py`
    accept `--test-runner pytest|vitest|jest`. Migration tests in
    `tests/test_sprint_loop.py::test_test_runner_adapter_<engine>`.
- **Renumbered from "P1 in EXTERNAL-DOGFOOD-HANDOFF.md":** the PRD
  defines Backlog D as the capability-orchestrator (Phase 6 territory);
  Backlog E is unrelated — it's a runtime-extensibility gap exposed by
  dogfooding.

### External dogfood log pointer

`phase-4.5/EXTERNAL-DOGFOOD-HANDOFF.md` carries the full triage
prompt: P1 (this entry) + P2 (KN-J15 fix recipe) + P3 (KN-J7 fix
recipe) + P4 (resume path — J-9/J-10/J-11). Plus the "what worked"
list: pre-chunk cross-family PRD review caught 8 convergent spec
defects in the EOS MVP (cascade divergence / backwards drop-down API /
un-buildable phase sequencing / missing meeting-status field /
serverless connection exhaustion / EOS-canon errors). That pre-chunk
review is the framework's highest-value moment and is worth protecting
as a first-class step, not an implicit side effect of the planner gate.

### KN-R1. Adversarial review is not enforced on framework-repo changes

- **Status:** OPEN (spec written; not built). See
  `phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md`.
- **Symptom / repro:** chunk-14 (commit `623e024`,
  `factory/chunk-14-kn-J-fixes`) was validated with two same-family
  Factory Task subagents authored and orchestrated by the implementer.
  That review reached ACCEPT-WITH-NITS but would be rejected by a real
  §17.2 gate on the family-distinctness constraint alone.
- **Root cause:** (1) `tools/orchestrate-review.py` has no diff/branch
  review entrypoint (it is pilot-chunk shaped: `--test-file` /
  `--lock-file` / bundle); (2) Act 1 / Act 2 collapse (implementer never
  crossed into runner/panel mode); (3) no forcing function ties "done" to
  a signed cross-family verdict.
- **Fix (designed, not built):** `bin/review-branch` emitting a
  tree-bound, HMAC-signed `review-attestation.json` (reusing
  `EVIDENCE_SIGNING_KEY`) + a fail-closed merge gate (CI status check
  `adversarial-sprint-review/attestation` + local pre-push hook) that
  verifies `tree_sha == HEAD^{tree}`, signature, ≥2 distinct families,
  implementer disjoint from reviewers, and an ACCEPT-class verdict, plus
  an `OPERATING-RULES §17` amendment. Applies to both the framework repo
  (self-dogfood) and pilot overlays.
