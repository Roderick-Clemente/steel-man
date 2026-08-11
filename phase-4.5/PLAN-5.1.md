# Phase 5.1 — Build Plan (revised after cross-family plan review)

Companion to `PHASE-5.1-AGENTIC-ORCHESTRATION-TIGHTENING.md` (design doc).
This plan is committed BEFORE the chunks fire (OPERATING-RULES §18.2).

## Revision history

- **v1** (commit `1777a93`): original 7-item, 2-chunk plan.
- **v2** (this revision): both Tier-2 validators (grok-4.5, gemini-3.1-pro-preview)
  returned REJECT. Convergent blocker: item 7 violated §22/§24 by putting
  `sign_chunk_token.build_token()` inside the runner process. Additional
  findings: KN-A-10 checklist row missing, builder actor not in spawn-prompt
  edit set, health check prompt-only not machine-checked, `read_review_scope`
  buried in item 1, schema conflict semantics underspecified, 5.1b verify
  surface too narrow. All fixed below.

## Context

Phase 5.0 delivered 5 chunks (5a-5e) that built the chunk-close gate
infrastructure: `cross_family_review.py`, `chunk_sequence_gate.py`,
`sign_chunk_token.py`, `chunk_close_banner.py`, the 4-actor spawn
prompts, `persistent_referee_stub.py`, and OPERATING-RULES §20-§24.
All 5 chunks passed cross-family review (ACCEPT).

The first real cross-family re-fire exposed KN-A-10: the referee polled
the wrong STEER.md path for 42+ wakes while the real queue piled up.
Phase 5.1 tightens the orchestration layer to prevent this.

## Deliverables (10 items, 2 chunks)

### Chunk 5.1a — Path discovery + health checks (KN-A-10 fix)

| # | Deliverable | Type | Details |
|---|-------------|------|---------|
| 1 | `tools/setup_review_scope.py` | New script | Creates `.adversarial-sprint/review-scope.json` with absolute paths. **Operator-run** (not first-actor) to prevent wrong-worktree creation. Required keys: `schema`, `worktree`, `branch`, `steer_md_path`, `evidence_dir`, `token_dir`, `tier2_panel`, `build_agent_family`, `tau_threshold`, `poll_interval_seconds`, `created_at`, `created_by`. Validates `tier2_panel` model IDs against `MODEL_FAMILY_MAP`. **Conflict semantics**: refuses if file exists and any of `{worktree, steer_md_path, evidence_dir, token_dir}` differs from existing. Non-path keys (tau_threshold, poll_interval) may be updated without refusal. |
| 2 | `tools/read_review_scope.py` | New helper | All actors import to load review-scope.json. Exits with error code 2 if missing. Returns dict. CLI: `python3 tools/read_review_scope.py` prints JSON to stdout. Importable: `from read_review_scope import load_scope; scope = load_scope()` raises `FileNotFoundError` if missing. |
| 3 | Spawn prompt step-0 (all 4 actors) | Edit 3 spawn prompts + OPERATING-RULES §25 | All 3 spawn prompts (referee, grok-validator, gemini-validator) get a new first step: "Read review-scope.json for all paths. Do NOT derive from context." Builder reads review-scope.json per §25 (documented in OPERATING-RULES, not a spawn prompt — the builder is this session, not a spawned actor). |
| 4 | First-wake health check | Edit spawn prompts | Referee posts `REFEREE READY: steer=<path> branch=<branch> tier2=<models>`. Validators post `VALIDATOR READY: validator=<model> steer=<path> session_id=<id>`. Operator verifies path match. |
| 5 | Validator post-write verification | Edit spawn prompts | Envelope MUST be >= 200 bytes before posting `VALIDATE COMPLETE`. `session_id=unknown` is never acceptable. If envelope is too small, post `REFUSED:` instead. |
| 6 | OPERATING-RULES §25 | Edit `tools/OPERATING-RULES.md` | "All actors discover shared paths from review-scope.json, not from context." Applies to all 4 actors including the builder. |
| 7 | Machine-checked path enforcement | Edit `tools/persistent_referee_stub.py` | Referee stub loads paths via `read_review_scope.load_scope()`, refuses start if review-scope.json missing, logs scope path on `REFEREE READY`. This is the durable enforcement layer — prompt edits (items 3-5) are necessary but not sufficient; KN-A-10 failed because actors followed ambiguous prompts correctly. |
| 8 | KN-A-10 verify step | Verify | Confirm KN-A-10 entry in `phase-4.5/KNOWN-ISSUES.md` is accurate after implementation (already on disk from commit `a8845c9`; verify status reflects fix landed). |

**Chunk 5.1a tests:**
- `tests/test_setup_review_scope.py` — creates review-scope.json, refuses on path-key conflict, allows non-path-key update, validates tier2_panel against MODEL_FAMILY_MAP, rejects relative paths
- `tests/test_read_review_scope.py` — loads review-scope.json, exits code 2 if missing, CLI prints valid JSON

**Chunk 5.1a verify check:** `python3 -m pytest tests/test_setup_review_scope.py tests/test_read_review_scope.py -v` + `python3 -m py_compile tools/setup_review_scope.py tools/read_review_scope.py tools/persistent_referee_stub.py`

### Chunk 5.1b — Reviewer distinctness + verify-only close flow

| # | Deliverable | Type | Details |
|---|-------------|------|---------|
| 9 | `cross_family_review.py` — reviewer-to-reviewer distinctness | Edit existing `check_reviewer_panel()` | Add pairwise family distinctness: refuse if any two reviewers share the same family. Existing checks (implementer-disjoint, count>=2, unknown family, placeholder SHA, ACCEPT-class verdict) remain. Explicit test case: implementer=openai, reviewers=[gemini-3.1-pro-preview, gemini-2.5-pro] → refuse on reviewer-to-reviewer collision (does NOT trip implementer-disjointness). |
| 10 | Wire verify-only close flow into `per_chunk.py` | Edit existing | Add `close_chunk()` that: (1) reads `token_dir` and `evidence_dir` from `review-scope.json` via `read_review_scope.load_scope()`, (2) calls `chunk_sequence_gate.check_gate()` to verify the PRIOR chunk's token before the next chunk starts, (3) calls `chunk_close_banner.render()` for operator-eye signal reading the token from disk. **Does NOT call `sign_chunk_token.build_token()`. Does NOT hold `EVIDENCE_SIGNING_KEY`. Does NOT write `chunk-N.token.json`.** Token emission stays in `persistent_referee_stub.py` (the referee signs after §21/§17.2/§23 checks). Uses in-process imports (`chunk_sequence_gate.check_gate`, `chunk_close_banner.render`) consistent with `per_chunk.py`'s existing import style. Called in `sprint-loop.py`'s chunk loop before `commit_chunk_change` when the prior chunk's token exists on disk; if token is missing, logs a `WAITING FOR REFEREE` status and proceeds (the referee signs asynchronously). |

**Chunk 5.1b tests:**
- `tests/test_reviewer_distinctness.py` — two same-family reviewers refused (even when different from implementer family), two different-family reviewers pass, existing implementer-disjoint check still works
- `tests/test_close_chunk.py` — `close_chunk()` reads review-scope.json for paths, calls gate with prior token, renders banner from on-disk token, does NOT call `sign_chunk_token.build_token()`

**Chunk 5.1b verify check:** `python3 -m pytest tests/test_reviewer_distinctness.py tests/test_close_chunk.py -v` + `python3 -m py_compile tools/sprint_loop/per_chunk.py tools/cross_family_review.py`

## Rule application table (§18.4)

| Rule | How this plan applies it |
|------|--------------------------|
| §7 | Assert on reality: tests check file existence, JSON validity, refusal behavior — not exit codes alone |
| §14 | `setup_review_scope.py` uses standard `argparse` + `json`; `close_chunk()` uses in-process imports consistent with `per_chunk.py`'s existing style; `persistent_referee_stub.py` imports `read_review_scope` |
| §15 | Plan is committed before chunks fire; chunk commits carry the implementation |
| §17 | 2 chunks, 10 items, clear exit criteria per chunk — not an unbounded foundation program |
| §18 | Composes existing primitives (`cross_family_review`, `chunk_sequence_gate`, `chunk_close_banner`, `read_review_scope`); fixes ergonomic friction (path ambiguity, reviewer-to-reviewer distinctness) inline; builds in chunks; reviewed at the end |
| §20 | Chunk 5.1b wires `chunk_sequence_gate.check_gate` into the runner as a verify-prior-token step before the next chunk starts — the gate enforces §20 structurally. The runner verifies; it does not sign. |
| §22 | **Builder does not sign tokens, does not hold `EVIDENCE_SIGNING_KEY`, does not write `chunk-N.token.json`.** `close_chunk()` is verify-only (gate check + banner display). Token emission stays in `persistent_referee_stub.py`. No contradiction with item 10. |
| §24 | **Referee signs; runner verifies.** The 4-actor topology is preserved: builder → orchestrator → Tier-2 → referee (signs). The runner's `close_chunk()` reads the referee's signed token from disk; it does not produce it. |
| §25 (new) | All 4 actors (including builder) read review-scope.json for paths — the fix for KN-A-10 |

## Trust boundary diagram (clarifies §22/§24 compliance)

```
Builder (this session)          Referee (separate session)
  │                               │
  ├─ builds chunk                 ├─ polls STEER.md
  ├─ commits chunk                ├─ fires/audits Tier-2 envelopes
  ├─ posts REVIEW REQUEST         ├─ checks §21/§17.2/§23
  │                               ├─ signs chunk-N.token.json  ← signing lives here
  │                               └─ posts REVIEW COMPLETE
  │                               │
  ├─ close_chunk():               │
  │   ├─ read review-scope.json   │
  │   ├─ gate.check_gate(prior)   │  ← verify-only, no signing
  │   ├─ banner.render(token)     │  ← reads referee's token from disk
  │   └─ commit_chunk_change()    │
  └─ next chunk                   │
```

## What this plan does NOT do

- Does not fix the gemini validator's underlying `droid exec` failure mode (empty envelopes). The spawn prompt tightening (item 5) catches it at the posting layer, but the root cause needs investigation in the validator session itself (design doc §5).
- Does not add cross-actor liveness watchdog (design doc §5). The health check catches path drift on first wake but not a referee that goes silent mid-sprint.
- Does not add TTL enforcement for REVIEW REQUEST lines (design doc §5). The path fix prevents the scenario that made TTLs expire.
- Does not add automated `READY` line verification against review-scope.json (a `check_review_scope_health.py` script). Item 7 (machine-checked path enforcement in the referee stub) is the durable layer; automated READY-line checking is a follow-on.
