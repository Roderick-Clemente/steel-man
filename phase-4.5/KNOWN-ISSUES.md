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
  pilot. The 63 pytest tests cover unit + integration paths under
  the runner (chunk-10 close); they do not exercise the per-chunk
  inner loop's calls to
  `droid exec`, `lock.py`, `verify-green.py`, `local_backend.py`
  end-to-end against a real pilot repo.
- **Why not (rationale for null):** the runner intentionally falls
  short of "execute a sprint" in this branch because: (a) the pilot's
  droid CLI subscription state was not in-scope for the build;
  (b) OPERATING-RULES §17 capacity envelope says "name the next 1–3
  deliverables" — running a full pilot is a separate deliverable.
- **Reproduction:** `python3 tools/sprint-loop.py --config
  examples/sprint-loop-config.json --chunks-file
  examples/sprint-loop-chunks-example.json --dry-run --non-interactive`
  exercises the dry-run path. A non-dry-run exercises real droid
  once the pilot is ready.
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

### KNR4. `--skip-reconcile` is currently an unconditional auto-accept

- **What:** panel-finding F-6 (high). The current implementation
  maps `--skip-reconcile` straight to `ReconcileDecision.ACCEPT`
  with no §5.3 machine-check. The panel recommended deprecating
  this flag and replacing it with `--accept-on-dual-accept`
  guarded by preconditions (≥2 reviewers, ACCEPT verdicts,
  verdicts bound to current `plan_sha256`, zero open
  blocker|high, cross-family confirmed, `oversight=low`).
- **Why deferred in chunk 10:** the chunk-10 close fixes the
  central human-seat defect (F-7: machine-check §5.3 on `accept`
  from stdin) and the post-resolution family guard (F-2). The
  `--skip-reconcile` surface is now *safer than before* because
  the F-7 `_enforce_5_3_preconditions` runs at the gate before
  --skip-reconcile's auto-accept fires. Waiving that surface
  still requires an explicit operator flag, but the panel
  prefers deprecation; record here.
- **TODO:** introduce `--accept-on-dual-accept` as the safe
  replacement; map `--skip-reconcile` to a loud warning + run-level
  `--treat-skip-as-bypass` flag for the operator who really wants
  the unconditional path.

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
