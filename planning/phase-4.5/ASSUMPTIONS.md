# Phase 4.5 — Assumptions & gaps log

Per Phase 3.2 convention (`phase-3.2/ASSUMPTIONS.md`), every point
where the spec (`PRD.md` §11 Phase 4.5 + the Phase 4.5 sprint-loop
prompt + `tools/OPERATING-RULES.md`) was ambiguous or silent, and a
decision was made, gets recorded here. "Nothing was ambiguous" is a
valid entry only if genuinely true — and it is not here.

The format below is **decision / why / what was missing**. Each
entry is auditable from the git history; the SHA where each entry
was added is recorded so a re-reviewer can find the call.

## A1. The runner's "human gate" is a stdin pause, not a PagerDuty / Slack notification

- **Decision:** the reconcile gate reads a single line from stdin.
  Helper scripts wrap this for non-interactive / CI use.
- **Why:** PRD §6 + §11 say the operator seat stays human. Slack /
  Pager integration would expand scope. The runner's gate is a plain
  bytestream — anything that can write a line (a CronCreate
  automation, a webhook handler, an async autopilot) can drive it.
- **What was missing:** the prompt did not specify HOW the human
  pause works. Carrier (Slack, e-mail, web socket) was unspecified.
  Plain stdin is the simplest correct answer and matches the
  wake-loop pattern in `tools/wake-loop.md`.

## A2. Chunking input is a `--chunks-file` argument, not auto-extracted from the plan document

- **Decision:** the chunk list is a structured input. Per
  chunk-12b / chunk-13 (pass-r3 H-7 fix): the runner reads
  `templates/overlay/sprint-loop-chunks-example.template.json`
  shape, copied at install time into
  `<PILOT_REPO>/.adversarial-sprint/chunks.json`.
- **Why:** PRD §5.5 says chunking happens AFTER test design; the
  planner may do it or the human may. Both paths require a stable
  intermediate format. Auto-extracting chunks from natural-language
  plan docs would mean parsing free text — a §7 silent-green trap.
- **What was missing:** the prompt's "The planner may do this, or
  the human may do it manually" was vague. We chose the human path
  with a structured input. Auto-extraction is named in
  `KNOWN-ISSUES.md` as a follow-on.

## A3. RunState.pilot_spec_file lives alongside the runner; the bundle's signing key is `EVIDENCE_SIGNING_KEY` env var

- **Decision:** pilots spec is read from `--pilot-spec-file` (a
  free-form markdown path); the runner passes it through but does NOT
  parse it (it surfaces to the planner only). The bundle's signing
  key is the conventional `EVIDENCE_SIGNING_KEY` env var.
- **Why:** the existing `phase-3.2/evidence/local_backend.py` and
  `consumer.py` already use `EVIDENCE_SIGNING_KEY` per the
  Phase 3.2 SP/ke1-fix. Re-using it keeps the cross-process
  verification working.
- **What was missing:** the prompt implied a naming convention
  without pedagogy; we follow the existing priamry convention in
  `phase-3.2/evidence/local_backend.py:sign_bundle`.

## A4. The runner's per-chunk evidence dir is `phase-4.5/build-evidence/<run-id>/<chunk-id>/`

- **Decision:** framework tree houses the runner's artifact tree;
  pilot-tree mutations stay in the pilot repo (not in this one).
- **Why:** per PRD §9 the runner's artifacts live in
  `.factory/adversarial-sprints/<run-id>/`. This project uses
  `phase-4.5/build-evidence/` as the convention to avoid the hidden
  `.factory` dir for committed evidence. The pilot's own changes
  are committed into the pilot repo, framed by the runner's
  per-chunk commit on the audit branch (see
  `tools/sprint-loop.py:commit_chunk_change`).
- **What was missing:** the prompt said "evidence to disk" without
  specifying per which repo. We chose framework-side (operator-side)
  audit; pilot-side (product-side) is the executor's domain.

## A5. Commit body uses the existing recipe (`tools/conventions/commit-body-recipe.md`)

- **Decision:** per-chunk commit bodies follow the standing
  conventions; the runner's commit body injects the resolved model,
  role (executor), and a Telemetry-row trailer.
- **Why:** OPERATING-RULES §17 commits-as-baton. Convention
  prevents drift.
- **What was missing:** the prompt says "conventional commit message"
  but no convention exists in the prompt. The runner picks the
  project's existing recipe rather than inventing.

## A6. Family guard runs as preflight, not lazy on first collision

- **Decision:** `preflight_family_guard` is called BEFORE any
  droid invocation, in the runner's `main()`. The guard fails closed.
- **Why:** the §17.2 invariant is "not coincidentally satisfied."
  Lazy enforcement (only when a collision happens) would let the
  first droid call already happen with a colliding family. PRD §4
  + §7 + §17.2 compound: best to refuse preflight and surface the
  failure to the operator.
- **What was missing:** the prompt's order — "planner → reviewer →
  reconcile..." — implies the guard runs before each role, but
  per-role guards would catch less than preflight (the planner's
  family is decided at config time, not at planner invocation).

## A7. The dry-run path is a "synthetic but typed" envelope; it is NOT a real droid simulation

- **Decision:** `dry_run=True` writes a JSON envelope that matches
  the Factory `to_envelope` contract shape. Downstream code paths
  parse it as a real envelope. The runner does NOT simulate the
  planning / review / implementation content.
- **Why:** the runner's job is to flow-control; the model-side
  content is real-droid-only. A dry-run that mimics model output
  would either behallucinate or freeze on randomness. The honest
  dry-run is "real flow, fake content."
- **What was missing:** the prompt did not specify the dry-run shape.
  The chosen shape aligns with `tools/orchestrate-review.py`'s
  schema, which the runner composes.

## A8. Branch naming `factory/sprint-<run-id>-<ts>`

- **Decision:** the branch name embeds the run-id and timestamp.
  Dry-run branches add `-dry-run` suffix to the name (only for
  human-readable signalling; the branch is NEVER created in dry-run).
- **Why:** PRD §11 says "factory/sprint-<timestamp>" generically;
  this commit keeps that shape and adds the run-id for traceability.
  AGENTS.md says branches are agent-prefixed (`factory/` for Droid).
- **What was missing:** the prompt's branch shape is loose; we
  picked the traceable variant.

## A9. Mid-loop retry exhausts → `HUMAN_DECISION` pause + checkpoint

- **Decision:** when retries hit `retry_threshold+1`, the chunk's
  status moves to `HUMAN_DECISION`, RunState is checkpointed to
  `phase-4.5/build-evidence/<run-id>/checkpoint.json`, and the
  runner exits with code 3.
- **Why:** PRD §5.7 says "repeated rejection or ambiguous ownership
  pauses for a human." The checkpoint supports `--resume-from <path>`
  on the next invocation.
- **What was missing:** the prompt's "human decision packet when
  threshold exceeded" is vague. The checkpoint is the durable
  surface; the operator reads it and resumes.
