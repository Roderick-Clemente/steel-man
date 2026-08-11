# Phase 5.1 — Build Plan (v6 — fixes inter-file coordination defects)

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
- **v3** (commit `8bd3cf0`): resolves the crypto contradiction with option
  (d) — structural verification only. Runner never touches any key. REJECT:
  items 10/12 referenced a top-level `verdict` field that the canonical
  token schema does not carry (verdicts are per-reviewer). Also missing:
  commit_sha expected-source, first-chunk bootstrap, subprocess style.
- **v4** (commit `a885aad`): fixes the token schema contract. Structural
  predicate operates on `reviewers[*].verdict`. Uses `_run_step` subprocess.
  Adds CLI→JSON mapping, deletes residual relative-path instructions.
  REJECT (grok v4 review): close-loop has hard gate and no await (BLOCKER A);
  prior_* naming contradictory (BLOCKER B); stub emits 1 reviewer but gate
  requires ≥2 (BLOCKER C); §20 rule text not updated for structural split.
  Genesis skip-with-banner rejected by operator prompt: "a skip path is a
  bypass path."
- **v5** (commit `f80fc75`): addresses all v4 findings. Full close-loop
  sequencing, stub upgraded to Tier-2 panel, referee-signed genesis token,
  §20 rule text amendment, cross-check note. REJECT (grok v5): token
  filename mismatch across artifacts (BLOCKER 1); genesis envelope-gated
  deadlock (BLOCKER 2); stub envelope_sha256 construction underspecified
  (BLOCKER 3); structural-only reimplements panel checks instead of
  composing (BLOCKER 4). Gemini ACCEPT.
- **v6** (this revision): addresses all 4 grok v5 blockers. Per-finding:
  - [grok-v5-blocker-1] Canonical filename: `chunk-{chunk_id}.token.json`
    everywhere. Stub output path updated. Token-name unit test added.
  - [grok-v5-blocker-2] Genesis exempt from envelope-presence check.
    Genesis token reviewers carry `envelope_sha256` = SHA-256 of empty
    string (`e3b0c4...`). Referee signs genesis without envelope validation.
  - [grok-v5-blocker-3] Stub `envelope_sha256` = `hashlib.sha256(b"").hexdigest()`
    for each Tier-2 reviewer. Stub-fixture test: stub-minted tokens pass
    `--structural-only` gate.
  - [grok-v5-blocker-4] `chunk_sequence_gate.py --structural-only` imports
    and calls `cross_family_review.check_reviewer_panel()` for panel
    validation. No duplicated logic. §18 composition preserved.
  - [grok-blocker] Structural predicate now mirrors `cross_family_review.py`
    `check_reviewer_panel()` exactly: `len(reviewers) >= 2`, all reviewer
    families distinct from implementer family (read from review-scope.json
    `build_agent_family`) AND pairwise distinct from each other, every
    `reviewers[i].verdict` in ACCEPT_CLASS. No majority, no threshold, no
    any-ACCEPT.
  - [grok-sub-defect-1] `chunk_commit_sha` expected source: token N's
    `chunk_commit_sha` field read from the token file, compared against the
    actual commit SHA stored in runner chunk state. Explicitly NOT
    `git rev-parse HEAD` at gate time.
  - [grok-sub-defect-2] Genesis: operator-run setup writes a referee-signed
    genesis token (`chunk-genesis.token.json`) at sprint initialization,
    same `chunk-token/v1` schema. NO skip-with-banner path. A skip path is
    a bypass path.
  - [grok-sub-defect-3] §20 trade-off paragraph added as distinct section.
  - [gemini-nit-a] Composition style resolved: `_run_step` subprocess chosen.
    Rationale: `per_chunk.py`'s docstring exceptions (`invoke_droid`,
    `LocalBackend`) are both stateful in-process objects. Gate and banner
    are stateless CLI scripts with existing argparse interfaces — they fit
    the subprocess pattern without weakening the §14 discipline.
  - [gemini-nit-b] `sys.path.insert(0, <tools dir>)` specified in test row.
  - [gemini-nit-c] CLI mapping via MODEL_FAMILY_MAP with fail-closed refusal
    on unknown family (§17.2).
  - [ref-v4-blocker-A] Close-loop sequencing specified end-to-end: commit →
    post REVIEW REQUEST → await token (poll with timeout → HUMAN_DECISION)
    → structural close_chunk → start next.
  - [ref-v4-blocker-B] Naming disambiguated with 2-chunk timeline. Function
    is `close_chunk(chunk_id, commit_sha)` — verifies the token for the
    chunk just closed, not "prior" in the N-1 sense.
  - [ref-v4-blocker-C] Stub upgraded: `persistent_referee_stub.py` emits the
    Tier-2 panel from review-scope.json as reviewers (≥2, all ACCEPT-class)
    instead of a single `referee-stub` reviewer.
  - [ref-v4-high] §20 rule text amendment added to 5.1b deliverables.
  - [ref-v4-medium-1] Item 8: update KN-A-10 status to IN-PROGRESS with
    plan pointer, not just grep-for-existence.
  - [ref-v4-medium-2] Spawn prompt verify greps added to 5.1a.

## The crypto resolution (option d — structural verification)

The v2 blocker: `chunk_sequence_gate.check_gate()` and
`chunk_close_banner.render()` both call `sign_chunk_token.verify_token()`
which needs `EVIDENCE_SIGNING_KEY` for HMAC-SHA256 verification. The plan
said "runner doesn't hold the key" AND "runner verifies the token" —
mutually exclusive with symmetric crypto.

**Resolution**: the runner's `close_chunk()` does NOT call
`sign_chunk_token.verify_token()` at all. It performs structural
verification only. The panel validation (checks 2-5 below) is delegated
to `cross_family_review.check_reviewer_panel()` — the gate imports and
calls the existing pure function rather than duplicating its logic (§18
composition: one source of truth for "what counts as a valid panel").
The gate adds only existence + commit_sha checks on top:

1. Token file exists at `{token_dir}/chunk-{chunk_id}.token.json`
   (hard refuse if missing — §20 gate). **Canonical filename**: all
   token files follow `chunk-{chunk_id}.token.json` (cross-checked:
   existing `phase-4.5/tokens/chunk-5{a-e}.token.json` matches). The
   stub's output path (`persistent_referee_stub.py` line
   `token_dir / f"{req['chunk']}.token.json"`) is updated to
   `token_dir / f"chunk-{req['chunk']}.token.json"` in item 7.
2-5. `check_reviewer_panel()` is called with the token's reviewers,
   the implementer family (from `--implementer-family`), and the
   reviewer verdicts/envelope SHAs from the token JSON. All existing
   checks apply: `len(reviewers) >= 2`, implementer-disjoint, pairwise
   family distinctness (item 9 addition), unknown family, placeholder
   SHA, ACCEPT-class verdict. The function returns a refusal list;
   non-empty list → hard refuse (exit 6).
6. Token's `chunk_commit_sha` matches `--expected-sha` (the actual
   commit SHA from runner chunk state — explicitly NOT
   `git rev-parse HEAD` at gate time).

**Implementation via §18.4 friction fix**: add `--structural-only` flag to
`chunk_sequence_gate.py` (skips HMAC, does the 6 checks above) and
`--no-verify` flag to `chunk_close_banner.py` (reads token, displays
verdict, no HMAC check). Runner uses these flags; referee uses full path.
The `--structural-only` flag accepts `--expected-sha <sha>` (the actual
commit SHA from runner state) and `--implementer-family <family>` (from
review-scope.json) as explicit arguments. Existing `--prior-token` and
`--next-chunk-id` args remain (cross-checked against
`tools/chunk_sequence_gate.py` argparse).

## §20 trade-off (structural vs cryptographic)

Runner-side §20 under option (d) is a **structural predicate**, not
cryptographic attestation. The runner checks: token exists, reviewer panel
is cross-family and all-ACCEPT, and `chunk_commit_sha` matches the actual
commit. Anyone who can write a plausible token JSON to `token_dir` can
satisfy the runner gate. The cryptographic weight lives in the referee's
HMAC token issuance — the referee holds `EVIDENCE_SIGNING_KEY` and signs
only after §21/§17.2/§23 checks pass. The operational defense is that
only the referee writes to `token_dir`. Operators reading the runner code
should not mistake the structural gate for cryptographic verification.
§20 rule text (in `tools/OPERATING-RULES.md`) will be amended in 5.1b to
state this split explicitly.

## Genesis token (no skip path)

A skip-with-banner path is a bypass path. Instead, the operator-run
`setup_review_scope.py` creates a genesis token request at sprint
initialization:
1. `setup_review_scope.py` writes `chunk-genesis.token.json` (unsigned)
   with `chunk_id: "genesis"`, `chunk_commit_sha: <HEAD at init>`,
   `reviewers: tier2_panel` (all with `verdict: "ACCEPT"`,
   `envelope_sha256: hashlib.sha256(b"").hexdigest()` =
   `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`),
   and a `REVIEW REQUEST: chunk=genesis ...` line to STEER.md.
   **Genesis is exempt from envelope-presence check**: the referee's
   `validate_request()` normally requires envelope paths to exist on
   disk. Genesis has no envelopes (no reviewers have run yet). The
   referee signs genesis without envelope validation — there is nothing
   to review, only the sprint initialization to attest.
2. The referee (already running) polls STEER.md, sees the genesis request,
   signs the genesis token with `EVIDENCE_SIGNING_KEY` (or
   `EVIDENCE_SIGNING_KEY_STUB` for the stub), and writes the signed
   token to `{token_dir}/chunk-genesis.token.json`.
3. The runner's first `close_chunk` call (before chunk 1 starts) verifies
   the genesis token with the same structural predicate. No special-case
   skip. The `--expected-sha` for genesis verification is the HEAD
   captured at sprint init.

## Close-loop sequencing (end-to-end)

The runner's chunk loop in `sprint-loop.py` (~line 1448, cross-checked)
currently does: `run_chunk_with_retries` → `write_checkpoint` →
`commit_chunk_change` → next iteration. There is no REVIEW REQUEST post,
no await, no gate check. The revised close flow:

```
for each chunk N (0-indexed):
  1. run_chunk_with_retries → build + verify + evidence
  2. commit_chunk_change(N) → git commit, capture HEAD as chunk_commit_sha
  3. post_review_request(N, chunk_commit_sha) → append to STEER.md:
     "REVIEW REQUEST: chunk=<N> commit=<sha> paths=<envelopes> ttl=<iso+1h>"
  4. await_token(N, timeout) → poll {token_dir}/chunk-<N>.token.json
     on poll_interval_seconds (from review-scope.json)
     - if timeout → HUMAN_DECISION (runner pauses, operator investigates)
     - if token appears → proceed to step 5
  5. close_chunk(N, chunk_commit_sha) → structural gate via _run_step:
     python3 tools/chunk_sequence_gate.py --structural-only
       --prior-token {token_dir}/chunk-<N>.token.json
       --next-chunk-id <N+1>
       --expected-sha <chunk_commit_sha>
       --implementer-family <build_agent_family from review-scope.json>
     - exit 6 → HUMAN_DECISION (gate refused; token invalid)
     - exit 0 → proceed to step 6
  6. render_banner(N) → _run_step:
     python3 tools/sprint_loop/chunk_close_banner.py --no-verify
       --token-path {token_dir}/chunk-<N>.token.json
  7. next chunk
```

**2-chunk timeline example** (disambiguates naming per [ref-v4-blocker-B]):
```
Sprint init:
  operator runs setup_review_scope.py
  → writes review-scope.json + unsigned genesis token + REVIEW REQUEST to STEER.md
  referee polls, signs chunk-genesis.token.json
  runner awaits chunk-genesis.token.json → OK

Chunk 1 (chunk_id="5.1a"):
  build → commit (sha_1=abc123) → post REVIEW REQUEST → await chunk-5.1a.token.json
  → close_chunk("5.1a", sha_1=abc123):
      gate verifies chunk-5.1a.token.json: chunk_commit_sha == abc123? YES
      → banner → start chunk 2

Chunk 2 (chunk_id="5.1b"):
  build → commit (sha_2=def456) → post REVIEW REQUEST → await chunk-5.1b.token.json
  → close_chunk("5.1b", sha_2=def456):
      gate verifies chunk-5.1b.token.json: chunk_commit_sha == def456? YES
      → banner → sprint complete
```

`close_chunk(chunk_id, commit_sha)` verifies the token for the chunk just
closed (chunk N), not the chunk before it (N-1). The `commit_sha` is the
git HEAD captured after `commit_chunk_change(N)`. The token's
`chunk_commit_sha` must match this SHA.

## Context

Phase 5.0 delivered 5 chunks (5a-5e) that built the chunk-close gate
infrastructure: `cross_family_review.py`, `chunk_sequence_gate.py`,
`sign_chunk_token.py`, `chunk_close_banner.py`, the 4-actor spawn
prompts, `persistent_referee_stub.py`, and OPERATING-RULES §20-§24.
All 5 chunks passed cross-family review (ACCEPT).

The first real cross-family re-fire exposed KN-A-10: the referee polled
the wrong STEER.md path for 42+ wakes while the real queue piled up.
Phase 5.1 tightens the orchestration layer to prevent this.

## Deliverables (14 items, 2 chunks)

### Chunk 5.1a — Path discovery + health checks (KN-A-10 fix)

| # | Deliverable | Type | Details |
|---|-------------|------|---------|
| 1 | `tools/setup_review_scope.py` | New script | Creates `.adversarial-sprint/review-scope.json` with absolute paths. **Operator-run** (not first-actor) to prevent wrong-worktree creation. Required keys: `schema`, `worktree`, `branch`, `steer_md_path`, `evidence_dir`, `token_dir`, `tier2_panel`, `build_agent_family`, `build_agent_models`, `tau_threshold`, `poll_interval_seconds`, `created_at`, `created_by`. **CLI → JSON mapping**: `--tier2 grok-4.5,gemini-3.1-pro-preview` (comma-separated model IDs) maps to `tier2_panel: [{model_id, provider, family}]` via `MODEL_FAMILY_MAP` lookup inside the script. **Fail-closed**: refuses on unknown family (model ID not in `MODEL_FAMILY_MAP`) per §17.2. **Conflict semantics**: refuses if file exists and any of `{worktree, steer_md_path, evidence_dir, token_dir}` differs from existing. Non-path keys may be updated without refusal. **STEER.md init**: initializes STEER.md with protocol header if it doesn't exist (design doc §2.2 step 3). **Genesis token**: writes unsigned `chunk-genesis.token.json` and posts `REVIEW REQUEST: chunk=genesis` to STEER.md for the referee to sign. |
| 2 | `tools/read_review_scope.py` | New helper | All actors import to load review-scope.json. Exits with error code 2 if missing. Returns dict. CLI: `python3 tools/read_review_scope.py` prints JSON to stdout. Importable: `from read_review_scope import load_scope; scope = load_scope()` raises `FileNotFoundError` if missing. |
| 3 | Spawn prompt step-0 (all 4 actors) | Edit 3 spawn prompts + OPERATING-RULES §25 | All 3 spawn prompts (referee, grok-validator, gemini-validator) get a new first step: "Read review-scope.json for all paths. Do NOT derive from context." **Delete the old relative-path instructions** (`<repo>/.adversarial-sprint/STEER.md`, `mkdir -p .adversarial-sprint`) from the spawn prompts — leaving both re-opens KN-A-10 via prompt contradiction. Builder reads review-scope.json per §25 (documented in OPERATING-RULES, not a spawn prompt). **Also updates design doc §2.3** to say "operator-run" instead of "actor-run" to resolve the contradiction. |
| 4 | First-wake health check | Edit spawn prompts | Referee posts `REFEREE READY: steer=<path> branch=<branch> tier2=<models>`. Validators post `VALIDATOR READY: validator=<model> steer=<path> session_id=<id>`. Operator verifies path match. |
| 5 | Validator post-write verification + nested-invocation fallback | Edit spawn prompts | Envelope MUST be >= 200 bytes before posting `VALIDATE COMPLETE`. `session_id=unknown` is never acceptable. If envelope is too small, post `REFUSED:` instead. **Nested-invocation fallback** (design doc §3.3 fix #3): if firing `droid exec` from within the session fails, the validator performs the review directly (it IS the model) and writes the review to the envelope file itself. |
| 6 | OPERATING-RULES §25 | Edit `tools/OPERATING-RULES.md` | "All actors discover shared paths from review-scope.json, not from context." Applies to all 4 actors including the builder. |
| 7 | Machine-checked path enforcement + stub panel upgrade | Edit `tools/persistent_referee_stub.py` | Referee stub loads paths via `read_review_scope.load_scope()`, refuses start if review-scope.json missing, logs scope path on `REFEREE READY`. **Stub panel upgrade** ([ref-v4-blocker-C]): `build_signed_token()` emits the Tier-2 panel from review-scope.json as reviewers (≥2, all `ACCEPT-WITH-NITS`, with real `family`/`model_id`/`provider` from `MODEL_FAMILY_MAP`) instead of a single `referee-stub` reviewer. **Envelope_sha256 construction** ([grok-v5-blocker-3]): each reviewer's `envelope_sha256` = `hashlib.sha256(b"").hexdigest()` (SHA-256 of empty string = `e3b0c4...`) since the stub doesn't fire real reviewers. This is a valid SHA-256 that passes `cross_family_review.envelope_is_placeholder()` (not a homogeneous leading-character pattern). **Filename fix** ([grok-v5-blocker-1]): stub output path updated from `token_dir / f"{req['chunk']}.token.json"` to `token_dir / f"chunk-{req['chunk']}.token.json"` to match the canonical pattern. **Genesis exemption**: `process_request()` skips `validate_request()` envelope-path check when `chunk_id == "genesis"`. **Note**: HMAC verification and token signing belong to the production referee (`EVIDENCE_SIGNING_KEY_REFEREE`), not only the stub (`EVIDENCE_SIGNING_KEY_STUB`). |
| 8 | KN-A-10 status update + grok §12 note | Verify + edit | Update KN-A-10 status from `OPEN` to `IN-PROGRESS` with plan pointer (`PLAN-5.1.md v5`). Script-runnable verify: `grep -q "IN-PROGRESS" phase-4.5/KNOWN-ISSUES.md`. Also record grok-4.5 `--auto high` requirement as a §12 unexercised-path note in KNOWN-ISSUES.md (grok refused `--auto low` and `--auto medium` with "insufficient permission" during plan review). |

**Chunk 5.1a tests:**
- `tests/test_setup_review_scope.py` — creates review-scope.json, refuses on path-key conflict, allows non-path-key update, validates tier2_panel against MODEL_FAMILY_MAP with fail-closed on unknown family, rejects relative paths, initializes STEER.md if missing, writes genesis token request
- `tests/test_read_review_scope.py` — loads review-scope.json, exits code 2 if missing, CLI prints valid JSON

**Chunk 5.1a verify check:** `python3 -m pytest tests/test_setup_review_scope.py tests/test_read_review_scope.py -v` + `python3 -m py_compile tools/setup_review_scope.py tools/read_review_scope.py tools/persistent_referee_stub.py` + `grep -q "IN-PROGRESS" phase-4.5/KNOWN-ISSUES.md` + `! grep -rn "mkdir -p .adversarial-sprint" phase-4.5/prompts/` + `! grep -rn "\.adversarial-sprint/STEER\.md" phase-4.5/prompts/ | grep -v review-scope`

### Chunk 5.1b — Reviewer distinctness + structural-only close flow

| # | Deliverable | Type | Details |
|---|-------------|------|---------|
| 9 | `cross_family_review.py` — reviewer-to-reviewer distinctness | Edit existing `check_reviewer_panel()` | Add pairwise family distinctness: refuse if any two reviewers share the same family. Existing checks (implementer-disjoint, count>=2, unknown family, placeholder SHA, ACCEPT-class verdict) remain. **Refusal string distinctness**: reviewer-to-reviewer collision refusal must have a distinct reason string from implementer-disjoint refusal (e.g., "reviewer-to-reviewer family collision" vs "reviewer collides with implementer family"). Explicit test case: implementer=openai, reviewers=[gemini-3.1-pro-preview, gemini-2.5-pro] → refuse on reviewer-to-reviewer collision (does NOT trip implementer-disjointness). |
| 10 | `chunk_sequence_gate.py` — add `--structural-only` flag | Edit existing | New flag + args: `--structural-only` (skip HMAC), `--expected-sha <sha>` (actual commit SHA from runner state, NOT HEAD), `--implementer-family <family>` (from review-scope.json). When `--structural-only` is set, `check_gate()` skips `sign_chunk_token.verify_token()` and does: (1) token file exists at `--prior-token` path, (2) **imports and calls `cross_family_review.check_reviewer_panel()`** with the token's reviewers, implementer family from `--implementer-family`, reviewer verdicts and envelope SHAs from the token JSON — all existing checks apply (count≥2, implementer-disjoint, pairwise distinct, unknown family, placeholder SHA, ACCEPT-class). Non-empty refusal list → exit 6. (3) Token's `chunk_commit_sha` matches `--expected-sha`. Hard refuse (exit 6) on any failure. **No duplicated panel logic** — the gate delegates to `check_reviewer_panel()` (§18 composition: one source of truth). Existing args `--prior-token`, `--next-chunk-id`, `--signing-key-env` remain. No skip path. |
| 11 | `chunk_close_banner.py` — add `--no-verify` flag | Edit existing | New flag: when set, `render()` reads the token JSON and displays the verdict without calling `sign_chunk_token.verify_token()`. Adds a textual `mode=structural` tag to the banner output (does NOT invent a new emoji — keeps the existing ✅/⛔ contract from `chunk_close_banner.py` docstring). Existing `--token-path`, `--signing-key-env` args remain (cross-checked). |
| 12 | Wire close flow into `per_chunk.py` + `sprint-loop.py` | Edit existing | Add `close_chunk(chunk_id, commit_sha)` and `await_token(chunk_id, timeout)`: (1) `await_token` polls `{token_dir}/chunk-{chunk_id}.token.json` on `poll_interval_seconds` from review-scope.json; timeout → `HUMAN_DECISION`. (2) `close_chunk` reads `token_dir` and `build_agent_family` from review-scope.json via `read_review_scope.load_scope()` — refuses if missing. (3) Calls `chunk_sequence_gate` via `_run_step`: `python3 tools/chunk_sequence_gate.py --structural-only --prior-token {path} --next-chunk-id {next} --expected-sha {commit_sha} --implementer-family {family}`. (4) Calls `chunk_close_banner` via `_run_step`: `python3 tools/sprint_loop/chunk_close_banner.py --no-verify --token-path {path}`. (5) Exit 6 from gate → `HUMAN_DECISION`. **Does NOT call `sign_chunk_token.build_token()` or `verify_token()`. Does NOT hold `EVIDENCE_SIGNING_KEY`. Does NOT write tokens.** Uses `_run_step` subprocess (chosen over amending docstring: gate/banner are stateless CLI scripts matching the existing subprocess pattern; the two docstring exceptions are stateful in-process objects — amending for stateless scripts would weaken the §14 discipline). Called in `sprint-loop.py`'s chunk loop: after `commit_chunk_change(N)`, post REVIEW REQUEST, await token, then `close_chunk(N, sha_N)`. |
| 13 | OPERATING-RULES §20 amendment | Edit `tools/OPERATING-RULES.md` | Amend §20 to state: runner-side chunk-close verification is structural (existence + panel + commit_sha); HMAC attestation lives in the referee's signing path. The runner never holds `EVIDENCE_SIGNING_KEY`. The structural gate is a necessary-but-not-sufficient condition; the referee's HMAC is the cryptographic attestation. |
| 14 | `post_review_request` helper | New function in `per_chunk.py` | Appends `REVIEW REQUEST: chunk=<id> commit=<sha> paths=<envelopes> ttl=<iso+1h>` to STEER.md (path from review-scope.json). Called after `commit_chunk_change`, before `await_token`. Uses `read_review_scope.load_scope()` for `steer_md_path`. |

**Chunk 5.1b tests:**
- `tests/test_reviewer_distinctness.py` — two same-family reviewers refused (even when different from implementer family), two different-family reviewers pass, existing implementer-disjoint check still works, refusal strings are distinct
- `tests/test_close_chunk.py` (with `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))` for imports) — `close_chunk()` reads review-scope.json for paths, **refuses when token missing** (exit 6, not soft-proceed), **refuses when any `reviewers[i].verdict` is REJECT** (checks per-reviewer), **refuses when `len(reviewers) < 2`**, **refuses when reviewer family collides with implementer family**, **refuses when two reviewers share same family**, **refuses when `chunk_commit_sha` mismatches `commit_sha` arg**, renders structural-verify banner with `mode=structural` tag, does NOT call `sign_chunk_token.build_token()` or `verify_token()`. `await_token` returns path on file appearance, raises `HUMAN_DECISION` on timeout. **Stub-fixture test**: stub-minted token (with `envelope_sha256 = sha256(b"")`) passes `--structural-only` gate. **Token-name test**: token file is named `chunk-{chunk_id}.token.json` (not `{chunk_id}.token.json`).

**Chunk 5.1b verify check:** `python3 -m pytest tests/test_reviewer_distinctness.py tests/test_close_chunk.py -v` + `python3 -m py_compile tools/sprint_loop/per_chunk.py tools/cross_family_review.py tools/chunk_sequence_gate.py tools/sprint_loop/chunk_close_banner.py`

## Rule application table (§18.4)

| Rule | How this plan applies it |
|------|--------------------------|
| §7 | Assert on reality: tests check file existence, JSON validity, refusal behavior — not exit codes alone |
| §12 | Grok-4.5 `--auto high` requirement recorded as unexercised-path note in KNOWN-ISSUES.md |
| §14 | `setup_review_scope.py` uses `argparse` + `json` with MODEL_FAMILY_MAP CLI mapping (fail-closed on unknown); `close_chunk()` uses `_run_step` subprocess against `tools/chunk_sequence_gate.py` and `tools/sprint_loop/chunk_close_banner.py` (stateless CLI scripts matching existing subprocess pattern); `persistent_referee_stub.py` imports `read_review_scope` |
| §15 | Plan is committed before chunks fire; chunk commits carry the implementation |
| §17 | 2 chunks, 14 items, clear exit criteria per chunk — not an unbounded foundation program |
| §18 | Composes existing primitives: `--structural-only` flag calls `cross_family_review.check_reviewer_panel()` (no duplicated panel logic); `--no-verify` flag on banner; `_run_step` subprocess for stateless CLI scripts; stub upgraded to emit Tier-2 panel from review-scope.json. One source of truth for panel validation. |
| §20 | Chunk 5.1b wires `chunk_sequence_gate --structural-only` as a **hard gate** with full close-loop sequencing (commit → REVIEW REQUEST → await → structural gate → banner → next). No soft-proceed, no skip path. **Runner-side §20 is structural, not cryptographic** — HMAC attestation lives in the referee. §20 rule text amended (item 13). Genesis token required — no bypass. |
| §22 | **Builder does not sign tokens, does not hold `EVIDENCE_SIGNING_KEY`, does not call `verify_token()`, does not write `chunk-N.token.json`.** `close_chunk()` is structural-only. Token emission AND HMAC verification stay in the referee (production: `EVIDENCE_SIGNING_KEY_REFEREE`; stub: `EVIDENCE_SIGNING_KEY_STUB`). |
| §24 | **Referee signs AND verifies HMAC; runner checks structure.** The 4-actor topology is preserved. The runner never touches any key. |
| §25 (new) | All 4 actors (including builder) read review-scope.json for paths — the fix for KN-A-10 |

## Trust boundary diagram (clarifies §22/§24 compliance)

```
Builder (this session)          Referee (separate session)
  │                               │
  ├─ setup: await genesis token   ├─ polls STEER.md
  ├─ chunk N:                     ├─ fires/audits Tier-2 envelopes
  │   build → commit (sha_N)      ├─ checks §21/§17.2/§23
  │   post REVIEW REQUEST         ├─ verifies prior token HMAC  ← crypto lives here
  │   await chunk-N.token.json    ├─ signs chunk-N.token.json   ← signing lives here
  │   close_chunk(N, sha_N):      └─ posts REVIEW COMPLETE
  │     gate --structural-only    │
  │       --expected-sha sha_N    │  ← existence + reviewers[].verdict
  │       --implementer-family F  │    + family distinctness + commit_sha, NO key
  │     banner --no-verify        │  ← reads token, mode=structural, NO key
  │   → start chunk N+1           │
  └─ sprint complete              │
```

## Cross-check note (wire-format ↔ plan-predicate verification)

Each claim verified against the named live artifact:

| Claim | Artifact checked | Result |
|-------|-----------------|--------|
| Token has no top-level `verdict`; verdicts are `reviewers[i].verdict` | `phase-4.5/tokens/chunk-5a.token.json` | ✅ Confirmed: `reviewers[0].verdict: "ACCEPT-WITH-NITS"`, `reviewers[1].verdict: "ACCEPT"`, no root `verdict` |
| `ACCEPT_CLASS = {"ACCEPT", "ACCEPT-WITH-NITS"}` | `tools/sign_chunk_token.py` | ✅ Confirmed: `ACCEPT_CLASS: frozenset[str] = frozenset({"ACCEPT", "ACCEPT-WITH-NITS"})` |
| `build_token()` signature: `chunk_id, chunk_commit_sha, reviewers, signed_by, signing_key_env` | `tools/sign_chunk_token.py` | ✅ Confirmed |
| Token schema: `chunk-token/v1`, fields `chunk_id, chunk_commit_sha, reviewers[.{envelope_sha256,family,model_id,provider,verdict}], schema, signature, signed_at, signed_by` | `phase-4.5/tokens/chunk-5a.token.json` + `tools/sign_chunk_token.py build_token()` | ✅ Confirmed (note: `provider` is `""` in live tokens — referee-side gap) |
| `check_reviewer_panel()` checks: implementer-disjoint, count≥2, unknown family, placeholder SHA, ACCEPT-class | `tools/cross_family_review.py` | ✅ Confirmed |
| `chunk_sequence_gate` CLI: `--prior-token`, `--next-chunk-id`, `--signing-key-env`, `--check-current-head`, `--repo` | `tools/chunk_sequence_gate.py` argparse | ✅ Confirmed |
| `chunk_close_banner` CLI: `--token-path`, `--signing-key-env`, `--plan-review-rendered`, `--validation-gate-executed` | `tools/sprint_loop/chunk_close_banner.py` argparse | ✅ Confirmed |
| `MODEL_FAMILY_MAP`: `grok-4.5: (xai, grok-family)`, `gemini-3.1-pro-preview: (google, gemini-family)`, `gemini-2.5-pro: (google, gemini-family)` | `tools/sprint_loop/config.py` | ✅ Confirmed — item 9 fixture valid |
| `per_chunk.py` docstring: "every external call is subprocess.run" with exceptions `invoke_droid`, `LocalBackend` | `tools/sprint_loop/per_chunk.py` | ✅ Confirmed — `_run_step` subprocess chosen for close flow |
| Stub emits 1 reviewer with `family: "referee-stub"`, `verdict: "ACCEPT-WITH-NITS"` | `tools/persistent_referee_stub.py` `build_signed_token()` | ✅ Confirmed — item 7 upgrades to Tier-2 panel |
| Stub CLI: `--steer`, `--token-dir`, `--reviewer-label`, `--interval`, `--once`, `--poll` | `tools/persistent_referee_stub.py` argparse | ✅ Confirmed |
| `sprint-loop.py` chunk loop: `run_chunk_with_retries` → `write_checkpoint` → `commit_chunk_change` → next, no gate | `tools/sprint-loop.py` ~line 1448 | ✅ Confirmed — item 12 adds close flow |
| Banner emoji contract: 🤺👀✅⛔ (four-tone) | `tools/sprint_loop/chunk_close_banner.py` docstring | ✅ Confirmed — item 11 uses `mode=structural` text tag, no new emoji |

## What this plan does NOT do

- Does not fix the gemini validator's underlying `droid exec` failure mode (empty envelopes). The spawn prompt tightening (item 5) catches it at the posting layer, but the root cause needs investigation in the validator session itself (design doc §5).
- Does not add cross-actor liveness watchdog (design doc §5). The health check catches path drift on first wake but not a referee that goes silent mid-sprint. The `await_token` timeout → HUMAN_DECISION is a backstop, not a watchdog.
- Does not add TTL enforcement for REVIEW REQUEST lines (design doc §5). The path fix prevents the scenario that made TTLs expire. The `await_token` timeout handles the case where the referee is slow.
- Does not add automated `READY` line verification against review-scope.json. Item 7 (machine-checked path enforcement in the referee stub) is the durable layer; automated READY-line checking is a follow-on.
- Does not add runner-side HMAC verification (options a/b/c from v2 review). Structural verification (option d) is sufficient for Phase 5.1. Stronger runner-side crypto verification can be pursued in a future phase.
