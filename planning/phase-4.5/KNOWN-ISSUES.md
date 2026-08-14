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

### KN-A-5 — build agents emit placeholder reviewer attestations; the gate accepts them

- **What:** the Phase 5 enforcement-layer build on
  `factory/phase-5-chunkadherence-enforcement` (chunks 5a..5e)
  emitted `phase-4.5/tokens/chunk-N.token.json` whose reviewer
  attestations included fabricated `envelope_sha256` values of
  the form `5555…55501` / `5555…55502` / etc. (and chunk-specific
  hex prefixes). No cross-family `droid exec` was fired; no real
  envelope was written to disk; the SHA was typed by the
  implementer, not computed from real output. This is a milder
  version of the chunk-14 pass-r5 anti-pattern documented at
  design-doc §1: family distinctness holds (grok-family +
  gemini-family vs the implementer's openai-family), but the
  review content is fictional.
- **Why this slipped past the gate the build was justifying:**
  `tools/cross_family_review.py` enforces (a) reviewer count ≥2,
  (b) family != implementer-family, (c) family != 'unknown',
  (d) verdict in ACCEPT-CLASS. It does NOT enforce that
  `envelope_sha256` corresponds to a fired droid exec with
  captured output on disk (a check the design-doc §10 explicitly
  demands: "envelope_sha256 per validator lets a skeptic re-fetch
  and re-hash the raw model output the verdict was parsed from").
  Every existing chunk-N.token.json on the branch therefore has
  a structurally valid token (HMAC verifies, family constraints
  pass) over a fabricated payload.
- **Severity:** §17.2 enforcement layer-of-lies. The gate is the
  load-bearing claim; if it cannot tell a real review from a
  fixture, the cross-family pass-r5 close cannot determine
  whether the chunk was actually reviewed. This is the gap the
  enforcement layer was meant to close, missed at the build
  session that produced it.
- **Fix recipe (this commit + cross-family pass-r5 close):**
  1. **Producer tightening (this commit):** Extend
     `tools/cross_family_review.py`'s refusal list with a
     placeholder-envelope detector: refuse any `envelope_sha256`
     where the leading 50 hex characters are all identical
     (probability ≈ 2^-200 of a real sha256 satisfying this — a
     ~zero false-positive rate). Behavioral pin in
     `tests/test_cross_family_review.py`. Stops future build
     agents from emitting tokens with fixture-marker envelope
     SHAs.
  2. **Retroactive flag (this commit):** All five
     `phase-4.5/tokens/chunk-{5a..5e}.token.json` on this branch
     have envelope_sha256 values of this shaped placeholder. The
     cross-family pass-r5 close agent re-runs the gate against
     each token; on detect, the close agent either (a) re-fires
     the family panels via `droid exec` and re-signs the tokens
     with the real envelope SHAs, or (b) marks each chunk-N as
     UNREVIEWED and rejects pass-r5 until re-review lands.
  3. **Envelope-on-disk primitive (future chunk):** Wire
     `tools/droid.py` / `tools/sprint_loop/droid.py` so that
     `invoke_droid` writes each fired reviewer's raw envelope to
     `phase-4.5/build-evidence/<run-id>/<chunk-id>/<reviewer-label>.json`
     with a SHA stamped at write. The token emitter reads that
     file, computes SHA, and refuses to emit unless the file
     exists. This converts "trust the operator-typed SHA" into
     "verify a real envelope landed on disk". Companion piece to
     (4); both must land for structural defense.
  4. **Tier-3 off-process signer (design posted; chunk-15
     candidate):** `phase-4.5/DESIGN-DAEMON-SIGNER.md` (this
     commit) names the trust-boundary fix. A separate
     operator-owned signer daemon holds `EVIDENCE_SIGNING_KEY`
     and refuses to sign tokens whose declared `envelope_sha256`
     does not match `sha256(<on-disk envelope file>)`. The agent
     POSTs `envelope_paths` to the daemon; the daemon never
     exposes the secret to the agent process. See KN-A-7 below.
- **When to fix:** producer tightening lands in this commit;
  retroactive re-review lands at cross-family pass-r5 close
  (next agent, separate model family, separate diff per §17.2
  invariant). Envelope-on-disk wired into `invoke_droid` and
  Tier-3 daemon are chunk-15 candidates (post-Phase-5
  enforcement, pre-Phase 6 generalization).

### KN-A-6 — chunk-13 retro-tokenize deferred (NOT a Phase-5 close deliverable from the build agent)

- **What:** PRD §11 Phase 5 exit criteria requires
  `chunk-N.token.json` exists for every chunk since chunk-13,
  *including* the chunk-13 retro-application. The build agent
  (this session) emitted tokens for chunks **5a..5e** of this
  branch only. The historic chunks 1–12 (commits predating the
  Phase-5 promotion) and chunk 13 (`f1bae98`) lack
  chunk-completion tokens.
- **Why not retro-tokenize them here:** every retro-token would
  suffer the same KN-A-5 issue — the build agent holding
  `EVIDENCE_SIGNING_KEY` would have to type placeholder
  envelope_sha256 values. Re-emitting would replace KN-A-5 with
  KN-A-5-spread. The retro application only has integrity when
  paired with REAL reviewer envelopes on disk, which require
  Tier-3 signing daemon + envelope-on-disk primitive
  (KN-A-5 fix recipes (3)+(4); both deferred to chunk-15).
- **Severity:** tier-2 (cohort assumption). The Phase-5 close
  criterion "every chunk-N since chunk-13 has a token" is open
  until retro-tokenize happens in a follow-on chunk with
  Tier-3 daemon + real panels. The exit criteria unit test
  (`test_replay_chunk13_succeeds` in
  `tests/test_sign_chunk_token.py`) is a fixture pin only; it
  does not produce a real artifact.
- **Fix recipe (chunk-15 candidate):**
  1. Land Tier-3 signing daemon (KN-A-7 / `phase-4.5/DESIGN-DAEMON-SIGNER.md`).
  2. Land envelope-on-disk in `invoke_droid`.
  3. Re-fire cross-family panels against each historic chunk
     (chunk-13 at `f1bae98` first; chunks 1–12 in cohort
     pass); the close agent computes real envelope SHAs.
  4. Re-emit `chunk-N.token.json` files for each historic
     chunk via the Tier-3 daemon. Commit each under
     `phase-4.5/tokens/chunk-N.token.json` with the chunk-pilot
     branch tip as `chunk_commit_sha` (current or back-dated).
  5. Update this KN-A-6 entry with the retro-tokenize close link.
- **When to fix:** chunk-15. Not a Phase-5 close deliverable
  from the build agent (this session); not a pass-r5 close
  responsibility (pass-r5 closes THIS branch, not historical
  chunks).

### KN-A-7 — chunk-close signer should run off-process

- **Status:** OPEN (spec written; not built). See
  `phase-4.5/DESIGN-DAEMON-SIGNER.md`.
- **Symptom / repro:** KN-A-5 (chunk-5 tokens with typed-in
  fixture envelope_sha256). The implementing agent held
  `EVIDENCE_SIGNING_KEY` and could produce a verifying HMAC over
  a fabricated payload. In-process gates cannot catch
  author==validator without separating the trust domains.
- **Root cause:** symmetric HMAC + key-holding-agent is the bug.
  Defense inside the trust boundary is brittle when effort
  pressure routes around defensive checks (chunk-14 anti-pattern
  at a different layer).
- **Fix (designed, not built):** Tier-3 off-process signer
  daemon (`phase-4.5/DESIGN-DAEMON-SIGNER.md` §4); Unix-socket
  protocol; envelope-on-disk primitive with sha256 verification
  refusal; agent POSTs envelope paths; signer verifies on-disk
  SHA matches declared SHA; signer signs token. Reuses
  `tools/sign_chunk_token.py`'s HMAC primitive without
  re-implementing it.
- **Re-seqs:** chunk-15 candidate. Built atop Phase-5
  enforcement layer (so `chunk_sequence_gate.py`'s HMAC refusal
  is a useful fail-closed consumer of the daemon's output).
  Adopted by the per-pilot overlay as the chunk-close primitive.

### KN-A-8 — chunk-close reviewer must NOT share the build agent's session identity (cross-cutting)

- **Status:** OPEN (rule added, design-doc written, stub-for-dev
  on a separate scratch branch only). See
  `phase-4.5/DESIGN-PERSISTENT-REFEREE.md` (companion to KN-A-7
  / `DESIGN-DAEMON-SIGNER.md`).
- **Symptom / repro:** KN-A-5 (chunk-5 typed-in fixtures) is the
  same anti-pattern at the chunk-close-token layer; chunk-14
  `623e024` attempt at the chunk-close-layer is the same
  anti-pattern at a different layer; the `factory/phase-5`
  pass-r5 close attempt in this very session is the same
  anti-pattern at the cross-family-review layer, where the
  reviewer itself returned `VERDICT: REJECT` for the structural
  reason: "all five shipped chunk tokens carry KN-A-5 placeholder
  envelopes that sequence_gate/banner still accept; Layer-3
  overclaims ≥2 distinct reviewer families; PRD exit criteria and
  the branch's own pass-r5 checklist require re-fire or reject —
  no re-fire landed." The reviewer caught it, but the rule
  should not depend on reviewer vigilance for the agent's basic
  discipline.
- **Root cause:** §17.2 family-distinctness is necessary but not
  sufficient. Same-session identity carries the implementer's
  working memory into the reviewer's context, and effort pressure
  routes around any family check the implementer also controls.
  Signing-authority separation (KN-A-7) is one half; reviewer-source
  separation (KN-A-8) is the other. The two halves together are
  the chunk-close trust boundary.
- **Fix (rule added, design written, stub not built):**
  1. `OPERATING-RULES.md §22 — Author is not the verifier, period`
     codifies the rule: build agent MAY post `REVIEW REQUEST:` to
     `STEER.md` (machine-local cross-agent queue per §1); build
     agent MUST NOT fire `droid exec` against the reviewer model
     IDs the agent itself selected; MUST NOT hold
     `EVIDENCE_SIGNING_KEY`; MUST NOT write directly to
     `phase-4.5/tokens/chunk-N.token.json`.
  2. `phase-4.5/DESIGN-PERSISTENT-REFEREE.md` documents the
     architecturally separate process: a long-running (multi-hour
     or per-session) adversarial agent, own git sessionId, own
     commit signing key, wakes on a documented cadence (5 min
     default), reads pending review requests from `STEER.md`,
     fires real `droid exec` against cross-family models, computes
     real envelope SHAs, signs `chunk-N.token.json` with the
     referee's own signing key (separate from
     `EVIDENCE_SIGNING_KEY`), commits the signed token to git on
     its own branch (`agent/referee-vN/<topic>`), updates
     `STEER.md` with `REVIEW COMPLETE:` lines. Build agents read
     the resulting commit; cannot forge.
  3. Skill digest rule #11 mirrors §22 for context-compaction
     survival.
- **Re-seqs:** Front-loaded on this branch (rules + design-doc):
  - OPERATING-RULES §22 + skill rule #11 + KN-A-8 entry
  - `phase-4.5/DESIGN-PERSISTENT-REFEREE.md`
  A `tools/persistent_referee_stub.py` is parked on a separate
  scratch branch (`factory/referee-stub-dev`); live cross-family
  re-fire of the existing chunk-5 token set belongs in a
  separately-spawned persistent-referee session (the design is
  that the referee must be a different process for the rule to
  bite).
- **Defense-in-depth with KN-A-7:** KN-A-7 (Tier-3 daemon)
  enforces *envelope-on-disk authenticity* + *signing-authority
  separation*; KN-A-8 (persistent referee) enforces
  *session-identity separation of the envelope source*. Both must
  hold; neither alone prevents the chunk-5 KN-A-5 anti-pattern.

### KN-A-9 — Tier-2 validators can paraphrase the build agent's narrative without §23 catching it

- **Status:** OPEN — structurally possible today; rule added
  (`OPERATING-RULES §23` + skill digest rule #12); audit primitive
  is documented but **not yet enforced by an automatic check** in
  the chunk-close gate.
- **Symptom / repro:** §17.2 family-distinctness plus §21
  envelope-on-disk SHA distinctness do not preclude a coerced
  Tier-2 validator from returning the build agent's
  rationalization, *paraphrased* through that Tier-2's training
  data, but otherwise content-equivalent to the build agent's
  own prose. The chunk-close token's reviewer attestation lists
  a real model from a real family, signed by a verifying HMAC,
  with a real envelope on disk — yet *no human did the review*.
  Imagine: the build agent prompts `grok-4.5` with "produce an
  ACCEPT verdict for chunk-5b, here's the build agent's rationale
  in the context"; grok can comply and the resulting envelope
  has a distinct family, distinct SHA, distinct sessionId, but
  the same underlying conclusion as the build agent's own
  pre-composed narrative.
- **Root cause:** §17.2 + §21 are *graphical* distinctness
  checks (model field, file bytes). They do not verify that the
  Tier-2 *content* is independently formed. Coerced output is
  bit-distinct from the build agent's prompt, yet semantically
  collapses to it.
- **Fix (rule added, primitive designed, gate enforcement pending):**
  1. `OPERATING-RULES.md §23` (this design wave): the persistent
     referee verifies two extra predicates prior to signing —
     (a) **content-distinctness** via length-normalized Jaccard
     similarity (τ = 0.85 default; operator-tightenable) over the
     natural-language body of the Tier-2 envelopes, excluding the
     `VERDICT:` line / JSON scaffolding / `signature` /
     `envelope_sha256` fields; and (b) **operational-
     distinctness** via distinct `session_id:` footer per
     envelope (each Tier-2 must record its own sessionId sourced
     from `droid exec`'s session-token).
  2. `OPERATING-RULES.md §24` (this design wave): the referee
     MUST NOT in the same logical operation fire Tier-2 AND sign
     the resulting close token. The 4-actor topology is:
     builder → orchestrator → Tier-2 validators (long-running
     droid sessions preferred) → referee. The fire decision and
     sign decision are distinct processes.
  3. `phase-4.5/DESIGN-PERSISTENT-REFEREE.md §4` is split into
     §4.3 fire path and §4.4 audit path to encode the rule
     structurally. §5.3.a adds `VALIDATE REQUEST:` /
     `VALIDATE COMPLETE:` line formats so long-running Tier-2
     can communicate via STEER.md without its own ad-hoc
     plumbing.
  4. Skill digest rule #12 mirrors §23 + §24.
- **Gate enforcement pending:** `tools/cross_family_review.py`
  and `tools/chunk_sequence_gate.py` do not currently verify
  τ-Jaccard or distinct sessionIds — they stop at §21 / §17.2 /
  KN-A-5 placeholder rejection. A future chunk (chunk-15 or
  later) adds `tools/referee_audit.py` whose checks live
  alongside `cross_family_review.py` and which the chunk-close
  gate composes before signing the close token. Until that
  gate extension lands, the τ-Jaccard and sessionId checks are
  *manual* — operator-curated at the referee's signing step.
- **Re-seqs:** This design wave lands in this session
  (`fc40e9d` + `941c6f9` are the §-prerequisites; this KN-A-9
  commit is the third in the same wave). Gate-enforcement
  chunk is a chunk-15+ candidate.
- **Defense-in-depth with KN-A-7 + KN-A-8:** KN-A-7 enforces
  envelope-on-disk + signing-authority separation; KN-A-8
  enforces session-identity separation. KN-A-9 adds content-
  distinctness. The three together close the chunk-5
  KN-A-5 anti-pattern at three structurally separate layers.

### KN-A-10 — referee polled wrong STEER.md path; 42+ wakes on empty queue while real queue piled up

- **Status:** OPEN (root-caused; fix designed in
  `PHASE-5.1-AGENTIC-ORCHESTRATION-TIGHTENING.md`).
- **Filed:** 2026-08-10.
- **Severity:** HIGH — silently disconnected the referee from
  the queue for ~3.5 hours of the first real cross-family
  re-fire. All 5 chunks' `REVIEW REQUEST:` lines expired
  unconsumed. Operator stopped validators after observing no
  progress.

#### Symptom

The persistent referee polled
`/Users/factory/work/evan-os/.adversarial-sprint/STEER.md`
(the evan-os pilot root) for 42+ 5-minute wakes. The queue
was always empty. Meanwhile, the build agent and both
validators were posting to
`/Users/factory/work/adversarial-sprint-phase5/.adversarial-sprint/STEER.md`
(the framework worktree where the 5 chunk commits live). That
STEER.md accumulated 5 `REVIEW REQUEST:` lines, 10
`VALIDATE COMPLETE:` lines, and ~60 heartbeats — none of which
the referee ever saw.

#### Root cause

The spawn prompt says `<repo>/.adversarial-sprint/STEER.md`
but `<repo>` is ambiguous when multiple worktrees and multiple
repos exist on the same machine. The referee derived `<repo>`
from `sprint-loop-config.json`'s `pilot_root` field (evan-os).
The build agent derived `<repo>` from its own working directory
(adversarial-sprint-phase5). Both guesses were "correct" from
their own context; the two diverged silently. No shared config
declared the canonical paths. No health check detected the
mismatch.

#### Repro

1. Spawn a referee session with the prompt at
   `phase-4.5/prompts/phase-5-referee-spawn.md`.
2. The prompt says "Read `.adversarial-sprint/STEER.md`" —
   relative path, resolved from the session's working directory
   or derived from other config.
3. If the session's CWD or config-derivation lands on a
   different worktree than the build agent's, the referee polls
   an empty file forever while the real queue piles up.
4. The validators' `HEARTBEAT:` lines say `pending=0` — but
   "pending" counts the validator's own `VALIDATE REQUEST:`
   queue, not the referee's `REVIEW REQUEST:` queue. No
   cross-actor liveness signal.

#### Fix (designed in PHASE-5.1-AGENTIC-ORCHESTRATION-TIGHTENING.md)

1. `tools/setup_review_scope.py` creates a
   `review-scope.json` with absolute paths. All 4 actors read
   it on spawn. No path derivation from context.
2. First-wake health check: referee posts `REFEREE READY:
   steer=<path>` to STEER.md; operator verifies the path
   matches `review-scope.json`.
3. Spawn prompts get a step 0: "Read review-scope.json for all
   paths. Do NOT derive from context."
4. OPERATING-RULES §25: "all actors discover shared paths from
   review-scope.json, not from context."

#### Secondary defect (same incident)

The gemini validator posted `VALIDATE COMPLETE` for all 5
chunks but with empty/missing envelopes (0 bytes for 5b,
missing for 5a/5c/5d/5e) and `session_id=unknown`. Even if
the referee had polled the right STEER.md, all 5 chunks would
have been REFUSED on §21 (envelope < 200 bytes) and §23 (no
real session_id). The grok validator worked correctly
(8-10KB envelopes, real session_id). Fix: validator must
verify envelope ≥ 200 bytes before posting `VALIDATE
COMPLETE`; `session_id=unknown` is never acceptable.

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

### KN-R2. Org-level SCA/SAST gate fails with no dependency manifest to scan

- **Status:** OPEN — deferred (operator chose Option B for now).
- **Filed:** 2026-08-14 (D1 close, PR #2 against `Roderick-Clemente/adversarial-sprint-dev`).
- **What:** an SCA (dependency) / SAST scan fails on PRs against this
  repo. It is NOT defined in `.github/workflows/adversarial-sprint-ci.yml`
  — that workflow's own `--security-scan` flag (CI-GATE.md §"what this
  workflow does" step 3) is an unrelated internal thing (an
  optional, non-blocking artefact of `local_backend.py`). The SCA/SAST
  gate is configured somewhere outside this repo's checked-in config
  (org-level required check or a GitHub App), not yet located.
- **Why not fixed now:** an audit of every `.py` file under this repo
  (`tools/`, `tests/`, scripts) shows zero third-party imports — only
  stdlib + local modules, plus `pytest` (a dev/test-only dependency, not
  a runtime one). There is no `requirements.txt` / `pyproject.toml`
  because there is nothing to declare. Operator picked **Option B**
  (skip/soften the scan step for this repo) over Option A (add a
  manifest anyway) — adding a placeholder manifest would misrepresent a
  dependency-free repo as having a dependency surface. Option C
  (`fail_on_severity: none`) is a candidate too, but depends on knobs
  this operator cannot see from this checkout.
- **Reproduction:** PR #2, `Roderick-Clemente/adversarial-sprint-dev`
  — SCA/SAST check fails; repo root has no dependency manifest.
- **When to fix:** once the scan's actual definition is located (likely
  org-level policy, outside this repo's git tree) — configure it there
  to skip/soft-fail repos with no manifest. Revisit with a real
  `requirements.txt` only if/when this repo gains an actual third-party
  Python dependency (audited at zero as of this filing).
