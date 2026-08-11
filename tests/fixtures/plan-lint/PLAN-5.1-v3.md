# Phase 5.1 — Build Plan (v3 — resolves HMAC verify-key contradiction)

Companion to `PHASE-5.1-AGENTIC-ORCHESTRATION-TIGHTENING.md` (design doc).
This plan is committed BEFORE the chunks fire (OPERATING-RULES §18.2).

## Revision history

- **v1** (commit `1777a93`): original 7-item, 2-chunk plan. REJECT: item 7
  violated §22/§24 by putting `sign_chunk_token.build_token()` inside the
  runner process.
- **v2** (commit `8dfaf4f`): fixed signing violation (runner verify-only).
  REJECT: HMAC-SHA256 is symmetric — runner can't verify the referee's
  token without holding `EVIDENCE_SIGNING_KEY`, contradicting §22. Also
  missing: STEER.md init, nested-invocation fallback, hard §20 gate.
- **v3** (this revision): resolves the crypto contradiction with option (d)
  — **structural verification only**. The runner does NOT call
  `sign_chunk_token.verify_token()` and never touches any key. It checks
  token existence, verdict, and commit_sha. HMAC verification stays with
  the referee. Adds `--structural-only` flag to `chunk_sequence_gate.py`
  and `--no-verify` flag to `chunk_close_banner.py` (§18.4 friction fix
  in existing primitives). Makes §20 a hard gate (no soft-proceed).
  Adds STEER.md init, nested-invocation fallback, builder-side scope
  refusal, and all other v2 findings.

## The crypto resolution (option d — structural verification)

The v2 blocker: `chunk_sequence_gate.check_gate()` and
`chunk_close_banner.render()` both call `sign_chunk_token.verify_token()`
which needs `EVIDENCE_SIGNING_KEY` for HMAC-SHA256 verification. The plan
said "runner doesn't hold the key" AND "runner verifies the token" —
mutually exclusive with symmetric crypto.

**Resolution**: the runner's `close_chunk()` does NOT call
`sign_chunk_token.verify_token()` at all. It performs structural
verification only:
1. Token file exists at `{token_dir}/chunk-{N}.token.json` (hard refuse
   if missing — §20 gate)
2. Token JSON has `verdict` in ACCEPT-CLASS (hard refuse if not)
3. Token's `chunk_commit_sha` matches the expected commit (hard refuse
   if mismatch)

The HMAC cryptographic verification stays with the referee, which has the
key and verifies the prior token before signing the next one. The runner
trusts the referee's signing process and checks that the artifact exists
with the right content.

**Implementation via §18.4 friction fix**: add `--structural-only` flag to
`chunk_sequence_gate.py` (skips HMAC, does existence + verdict + commit_sha)
and `--no-verify` flag to `chunk_close_banner.py` (reads token, displays
verdict, no HMAC check). Runner uses these flags; referee uses full path.

**Why not (a) daemon, (b) asymmetric, (c) shared-key**:
- (a) Tier-3 daemon (DESIGN-DAEMON-SIGNER.md) is scope creep for a
  path-discovery phase.
- (b) Ed25519 rewrite invalidates all existing tokens; large blast radius.
- (c) Sharing the HMAC key with the runner weakens §22 — holding the key
  means you can sign, even if code only verifies.
- (d) is the smallest change that resolves the contradiction without
  scope creep, crypto rewrite, or §22 weakening. Stronger runner-side
  crypto verification (daemon/asymmetric) can be pursued in a future
  phase if desired.

## Context

Phase 5.0 delivered 5 chunks (5a-5e) that built the chunk-close gate
infrastructure: `cross_family_review.py`, `chunk_sequence_gate.py`,
`sign_chunk_token.py`, `chunk_close_banner.py`, the 4-actor spawn
prompts, `persistent_referee_stub.py`, and OPERATING-RULES §20-§24.
All 5 chunks passed cross-family review (ACCEPT).

The first real cross-family re-fire exposed KN-A-10: the referee polled
the wrong STEER.md path for 42+ wakes while the real queue piled up.
Phase 5.1 tightens the orchestration layer to prevent this.

## Deliverables (12 items, 2 chunks)

### Chunk 5.1a — Path discovery + health checks (KN-A-10 fix)

| # | Deliverable | Type | Details |
|---|-------------|------|---------|
| 1 | `tools/setup_review_scope.py` | New script | Creates `.adversarial-sprint/review-scope.json` with absolute paths. **Operator-run** (not first-actor) to prevent wrong-worktree creation. Required keys: `schema`, `worktree`, `branch`, `steer_md_path`, `evidence_dir`, `token_dir`, `tier2_panel`, `build_agent_family`, `build_agent_models`, `tau_threshold`, `poll_interval_seconds`, `created_at`, `created_by`. Validates `tier2_panel` model IDs against `MODEL_FAMILY_MAP`. **Conflict semantics**: refuses if file exists and any of `{worktree, steer_md_path, evidence_dir, token_dir}` differs from existing. Non-path keys may be updated without refusal. **STEER.md init**: initializes STEER.md with protocol header if it doesn't exist (design doc §2.2 step 3). |
| 2 | `tools/read_review_scope.py` | New helper | All actors import to load review-scope.json. Exits with error code 2 if missing. Returns dict. CLI: `python3 tools/read_review_scope.py` prints JSON to stdout. Importable: `from read_review_scope import load_scope; scope = load_scope()` raises `FileNotFoundError` if missing. |
| 3 | Spawn prompt step-0 (all 4 actors) | Edit 3 spawn prompts + OPERATING-RULES §25 | All 3 spawn prompts (referee, grok-validator, gemini-validator) get a new first step: "Read review-scope.json for all paths. Do NOT derive from context." Builder reads review-scope.json per §25 (documented in OPERATING-RULES, not a spawn prompt). **Also updates design doc §2.3** to say "operator-run" instead of "actor-run" to resolve the contradiction. |
| 4 | First-wake health check | Edit spawn prompts | Referee posts `REFEREE READY: steer=<path> branch=<branch> tier2=<models>`. Validators post `VALIDATOR READY: validator=<model> steer=<path> session_id=<id>`. Operator verifies path match. |
| 5 | Validator post-write verification + nested-invocation fallback | Edit spawn prompts | Envelope MUST be >= 200 bytes before posting `VALIDATE COMPLETE`. `session_id=unknown` is never acceptable. If envelope is too small, post `REFUSED:` instead. **Nested-invocation fallback** (design doc §3.3 fix #3): if firing `droid exec` from within the session fails, the validator performs the review directly (it IS the model) and writes the review to the envelope file itself. |
| 6 | OPERATING-RULES §25 | Edit `tools/OPERATING-RULES.md` | "All actors discover shared paths from review-scope.json, not from context." Applies to all 4 actors including the builder. |
| 7 | Machine-checked path enforcement | Edit `tools/persistent_referee_stub.py` | Referee stub loads paths via `read_review_scope.load_scope()`, refuses start if review-scope.json missing, logs scope path on `REFEREE READY`. This is the durable enforcement layer — prompt edits are necessary but not sufficient. |
| 8 | KN-A-10 verify + grok §12 note | Verify | Script-runnable: `grep -q "KN-A-10" phase-4.5/KNOWN-ISSUES.md && grep -q "Status:" phase-4.5/KNOWN-ISSUES.md` — confirms entry exists and has a status field. Also record grok-4.5 `--auto high` requirement as a §12 unexercised-path note in KNOWN-ISSUES.md (grok refused `--auto low` and `--auto medium` with "insufficient permission" during plan review). |

**Chunk 5.1a tests:**
- `tests/test_setup_review_scope.py` — creates review-scope.json, refuses on path-key conflict, allows non-path-key update, validates tier2_panel against MODEL_FAMILY_MAP, rejects relative paths, initializes STEER.md if missing
- `tests/test_read_review_scope.py` — loads review-scope.json, exits code 2 if missing, CLI prints valid JSON

**Chunk 5.1a verify check:** `python3 -m pytest tests/test_setup_review_scope.py tests/test_read_review_scope.py -v` + `python3 -m py_compile tools/setup_review_scope.py tools/read_review_scope.py tools/persistent_referee_stub.py` + `grep -q "KN-A-10" phase-4.5/KNOWN-ISSUES.md`

### Chunk 5.1b — Reviewer distinctness + structural-only close flow

| # | Deliverable | Type | Details |
|---|-------------|------|---------|
| 9 | `cross_family_review.py` — reviewer-to-reviewer distinctness | Edit existing `check_reviewer_panel()` | Add pairwise family distinctness: refuse if any two reviewers share the same family. Existing checks (implementer-disjoint, count>=2, unknown family, placeholder SHA, ACCEPT-class verdict) remain. **Refusal string distinctness**: reviewer-to-reviewer collision refusal must have a distinct reason string from implementer-disjoint refusal (e.g., "reviewer-to-reviewer family collision" vs "reviewer collides with implementer family") so the named fixture cannot pass by collapsed reason check. Explicit test case: implementer=openai, reviewers=[gemini-3.1-pro-preview, gemini-2.5-pro] → refuse on reviewer-to-reviewer collision (does NOT trip implementer-disjointness). |
| 10 | `chunk_sequence_gate.py` — add `--structural-only` flag | Edit existing | New flag: when set, `check_gate()` skips HMAC verification (`sign_chunk_token.verify_token()`) but still checks: (1) token file exists, (2) verdict in ACCEPT-CLASS, (3) `chunk_commit_sha` matches expected. Hard refuse (exit 6) on any failure — no soft-proceed. This is the runner's gate path. |
| 11 | `chunk_close_banner.py` — add `--no-verify` flag | Edit existing | New flag: when set, `render()` reads the token JSON and displays the verdict without calling `sign_chunk_token.verify_token()`. Displays a structural-verify banner (distinct emoji from HMAC-verified banner so the operator can see which mode fired). |
| 12 | Wire structural-only close flow into `per_chunk.py` | Edit existing | Add `close_chunk()` that: (1) reads `token_dir` from `review-scope.json` via `read_review_scope.load_scope()` — **refuses to start if review-scope.json missing** (symmetric with item 7 stub refusal), (2) calls `chunk_sequence_gate.check_gate()` with `--structural-only` to verify the PRIOR chunk's token, (3) calls `chunk_close_banner.render()` with `--no-verify` for operator-eye signal. **Does NOT call `sign_chunk_token.build_token()`. Does NOT call `sign_chunk_token.verify_token()`. Does NOT hold `EVIDENCE_SIGNING_KEY`. Does NOT write `chunk-N.token.json`.** Hard refuse on missing/invalid prior token — no "log WAITING and proceed" (§20 is a hard gate). Uses in-process imports consistent with `per_chunk.py`'s existing style. Called in `sprint-loop.py`'s chunk loop before `commit_chunk_change`. |

**Chunk 5.1b tests:**
- `tests/test_reviewer_distinctness.py` — two same-family reviewers refused (even when different from implementer family), two different-family reviewers pass, existing implementer-disjoint check still works, refusal strings are distinct
- `tests/test_close_chunk.py` — `close_chunk()` reads review-scope.json for paths, **refuses next chunk when prior token missing** (exit 6, not soft-proceed), **refuses next chunk when prior token verdict is REJECT**, **refuses next chunk when commit_sha mismatches**, renders structural-verify banner, does NOT call `sign_chunk_token.build_token()` or `verify_token()`

**Chunk 5.1b verify check:** `python3 -m pytest tests/test_reviewer_distinctness.py tests/test_close_chunk.py -v` + `python3 -m py_compile tools/sprint_loop/per_chunk.py tools/cross_family_review.py tools/chunk_sequence_gate.py tools/sprint_loop/chunk_close_banner.py`

## Rule application table (§18.4)

| Rule | How this plan applies it |
|------|--------------------------|
| §7 | Assert on reality: tests check file existence, JSON validity, refusal behavior — not exit codes alone |
| §12 | Grok-4.5 `--auto high` requirement recorded as unexercised-path note in KNOWN-ISSUES.md |
| §14 | `setup_review_scope.py` uses standard `argparse` + `json`; `close_chunk()` uses in-process imports; `persistent_referee_stub.py` imports `read_review_scope` |
| §15 | Plan is committed before chunks fire; chunk commits carry the implementation |
| §17 | 2 chunks, 12 items, clear exit criteria per chunk — not an unbounded foundation program |
| §18 | Composes existing primitives with friction-fix flags (`--structural-only`, `--no-verify`); fixes reviewer-to-reviewer distinctness inline; builds in chunks; reviewed at the end |
| §20 | Chunk 5.1b wires `chunk_sequence_gate --structural-only` into the runner as a **hard gate** — refuses next chunk if prior token missing, verdict not ACCEPT, or commit_sha mismatch. No soft-proceed. |
| §22 | **Builder does not sign tokens, does not hold `EVIDENCE_SIGNING_KEY`, does not call `verify_token()`, does not write `chunk-N.token.json`.** `close_chunk()` is structural-only (existence + verdict + commit_sha). Token emission AND HMAC verification stay in `persistent_referee_stub.py`. |
| §24 | **Referee signs AND verifies HMAC; runner checks structure.** The 4-actor topology is preserved. The runner never touches any key. |
| §25 (new) | All 4 actors (including builder) read review-scope.json for paths — the fix for KN-A-10 |

## Trust boundary diagram (clarifies §22/§24 compliance)

```
Builder (this session)          Referee (separate session)
  │                               │
  ├─ builds chunk                 ├─ polls STEER.md
  ├─ commits chunk                ├─ fires/audits Tier-2 envelopes
  ├─ posts REVIEW REQUEST         ├─ checks §21/§17.2/§23
  │                               ├─ verifies prior token HMAC  ← crypto lives here
  │                               ├─ signs chunk-N.token.json   ← signing lives here
  │                               └─ posts REVIEW COMPLETE
  │                               │
  ├─ close_chunk():               │
  │   ├─ read review-scope.json   │
  │   ├─ gate --structural-only   │  ← existence + verdict + commit_sha, NO key
  │   ├─ banner --no-verify       │  ← reads token, displays verdict, NO key
  │   └─ commit_chunk_change()    │
  └─ next chunk                   │
```

## What this plan does NOT do

- Does not fix the gemini validator's underlying `droid exec` failure mode (empty envelopes). The spawn prompt tightening (item 5) catches it at the posting layer, but the root cause needs investigation in the validator session itself (design doc §5).
- Does not add cross-actor liveness watchdog (design doc §5). The health check catches path drift on first wake but not a referee that goes silent mid-sprint.
- Does not add TTL enforcement for REVIEW REQUEST lines (design doc §5). The path fix prevents the scenario that made TTLs expire.
- Does not add automated `READY` line verification against review-scope.json. Item 7 (machine-checked path enforcement in the referee stub) is the durable layer; automated READY-line checking is a follow-on.
- Does not add runner-side HMAC verification (options a/b/c from v2 review). Structural verification (option d) is sufficient for Phase 5.1. Stronger runner-side crypto verification can be pursued in a future phase.
