# Phase 5.1 — Build Plan

Companion to `PHASE-5.1-AGENTIC-ORCHESTRATION-TIGHTENING.md` (design doc).
This plan is committed BEFORE the chunks fire (OPERATING-RULES §18.2).

## Context

Phase 5.0 delivered 5 chunks (5a-5e) that built the chunk-close gate
infrastructure: `cross_family_review.py`, `chunk_sequence_gate.py`,
`sign_chunk_token.py`, `chunk_close_banner.py`, the 4-actor spawn
prompts, `persistent_referee_stub.py`, and OPERATING-RULES §20-§24.
All 5 chunks passed cross-family review (ACCEPT).

The first real cross-family re-fire exposed KN-A-10: the referee polled
the wrong STEER.md path for 42+ wakes while the real queue piled up.
Phase 5.1 tightens the orchestration layer to prevent this.

## Deliverables (7 items, 2 chunks)

### Chunk 5.1a — Path discovery + health checks (KN-A-10 fix)

| # | Deliverable | Type | Composes |
|---|-------------|------|----------|
| 1 | `tools/setup_review_scope.py` | New script | Creates `.adversarial-sprint/review-scope.json` with absolute paths (STEER.md, evidence dir, token dir, Tier-2 panel, build agent family, tau threshold). Refuses if file exists with different paths. Also creates `tools/read_review_scope.py` helper that all actors import. |
| 2 | Spawn prompt step-0 | Edit 3 files in `phase-4.5/prompts/` | All 3 spawn prompts (referee, grok-validator, gemini-validator) get a new first step: "Read review-scope.json for all paths. Do NOT derive from context." |
| 3 | First-wake health check | Edit spawn prompts | Referee posts `REFEREE READY: steer=<path> branch=<branch> tier2=<models>`. Validators post `VALIDATOR READY: validator=<model> steer=<path> session_id=<id>`. Operator verifies path match. |
| 4 | Validator post-write verification | Edit spawn prompts | Envelope MUST be >= 200 bytes before posting `VALIDATE COMPLETE`. `session_id=unknown` is never acceptable. If envelope is too small, post `REFUSED:` instead. |
| 5 | OPERATING-RULES §25 | Edit `tools/OPERATING-RULES.md` | "All actors discover shared paths from review-scope.json, not from context." |

**Chunk 5.1a tests:**
- `tests/test_setup_review_scope.py` — creates review-scope.json, refuses on path conflict, absolute paths only
- `tests/test_read_review_scope.py` — loads review-scope.json, exits with error if missing

**Chunk 5.1a verify check:** `python3 -m pytest tests/test_setup_review_scope.py tests/test_read_review_scope.py -v` + `python3 -m py_compile tools/setup_review_scope.py tools/read_review_scope.py`

### Chunk 5.1b — Gate composition + reviewer distinctness (grok nits)

| # | Deliverable | Type | Composes |
|---|-------------|------|----------|
| 6 | `cross_family_review.py` — reviewer-to-reviewer distinctness | Edit existing `check_reviewer_panel()` | Add refusal: if any two reviewers share the same family, refuse. Currently only checks implementer-disjoint + count>=2. This closes the gap where two reviewers from the same family (but different from implementer) would pass. |
| 7 | Wire close flow into `per_chunk.py` | Edit existing | Add `close_chunk()` function that composes: (1) `cross_family_review.check_reviewer_panel()` — verify panel, (2) `sign_chunk_token.build_token()` — emit token, (3) `chunk_sequence_gate` — verify prior chunk token, (4) `chunk_close_banner` — emit operator-eye signal. Called after `run_validators()` returns ACCEPT in `sprint-loop.py`'s chunk loop. |

**Chunk 5.1b tests:**
- `tests/test_reviewer_distinctness.py` — two same-family reviewers refused, two different-family reviewers pass
- `tests/test_close_chunk.py` — `close_chunk()` refuses without valid prior token, emits token + banner on success

**Chunk 5.1b verify check:** `python3 -m pytest tests/test_reviewer_distinctness.py tests/test_close_chunk.py -v` + `python3 -m py_compile tools/sprint_loop/per_chunk.py`

## Rule application table (§18.4)

| Rule | How this plan applies it |
|------|--------------------------|
| §7 | Assert on reality: tests check file existence, JSON validity, refusal behavior — not exit codes alone |
| §14 | `setup_review_scope.py` uses standard `argparse` + `json`; `close_chunk()` composes existing scripts via `subprocess.run` against tools/ primitives |
| §15 | Plan is committed before chunks fire; chunk commits carry the implementation |
| §17 | 2 chunks, 7 items, clear exit criteria per chunk — not an unbounded foundation program |
| §18 | Composes existing primitives (`cross_family_review`, `sign_chunk_token`, `chunk_sequence_gate`, `chunk_close_banner`); fixes ergonomic friction (path ambiguity) inline; builds in chunks; will be reviewed at the end |
| §20 | Chunk 5.1b wires the chunk-close gate into the runner — the gate enforces §20 structurally |
| §22 | Builder does not sign tokens or fire reviewers for chunk close; the persistent referee does that |
| §25 (new) | All actors read review-scope.json for paths — the fix for KN-A-10 |

## What this plan does NOT do

- Does not fix the gemini validator's underlying `droid exec` failure mode (empty envelopes). The spawn prompt tightening (item 4) catches it at the posting layer, but the root cause needs investigation in the validator session itself (design doc §5).
- Does not add cross-actor liveness watchdog (design doc §5). The health check catches path drift on first wake but not a referee that goes silent mid-sprint.
- Does not add TTL enforcement for REVIEW REQUEST lines (design doc §5). The path fix prevents the scenario that made TTLs expire.
