# PLAN — layout refactor D1

Derived from `CLEANUP-PLAN.md` (machine-local operator brief) per
OPERATING-RULES §18. This document is the committed plan the D1
chunks fire against; the brief itself is gitignored and does not
travel. Reviewer verdict on this file gates the drafting of chunk
specs; chunk-spec verdict gates code; code verdict + signed token
gates the next chunk.

Branch: `factory/layout-refactor`. `main` is FROZEN — no merges, no
pushes to main, no force-push anywhere. Operator merges after review.

## 1. Deliverable scope

**D1: split the phase dirs by the operator-aligned taxonomy.**

Move `phase-0 … phase-5` content out of the phase silos and into
three functional trees at the repo top level:

    tools/ tests/ skills/ templates/   CODE — runner, gates, adapters, harnesses
    planning/                          PLANNING — PRD-adjacent record
    evidence/                          EVIDENCE — envelopes, manifests, run
                                       trees, chunk tokens, one root

D2 (evidence consolidation) and D3 (wiki freshness) are **not** in
scope for this PLAN. Per §17 capacity envelope, D1 alone is a
successful night; D2 opens only after D1 closes with a verified
token; D3 opens only after D2 closes or is cleanly BLOCKED.

## 2. Non-goals / hard fences

- `main` is frozen. All D1 work lands on `factory/layout-refactor`.
- Evidence bytes are immutable per §21: committed envelopes,
  manifests, `MANIFEST.md`, `raw`/`stream` files are **never**
  edited, even to fix a stale citation. Stale citations get a
  redirects file, not a rewrite.
- No touching: `~/work/adversarial-sprint-referee`, the quantum-bank
  pilot repos, `~/.factory`, machine-local `referee-config.json`.
  Path updates in machine-local config are a named follow-on for
  the operator, not part of the run.
- The builder does NOT hold `EVIDENCE_SIGNING_KEY`, does NOT write
  to `phase-4.5/tokens/` (or its D1 replacement), and does NOT fire
  reviewers it selected itself (§22). Chunk-close is via the
  referee's signed token + `tools/chunk_sequence_gate.py` verify.
- Top-level `build-evidence/`, `pilots/`, `templates/`, `skills/`,
  `tests/`, `tools/`, `telemetry/`, `droid-wiki/` are decided KEEPs
  and stay put in D1.
- Run ids and artifact NAMES (`r-drs-role-split-1`, `MANIFEST.md`,
  envelope filenames) are preserved verbatim. Only directory
  **prefixes** change.

## 3. Existing primitives being composed (§18.1)

The plan is a flow chart of existing calls with thin orchestration
glue, not a fresh build. Named primitives:

| Primitive                                  | Role in D1                              |
|--------------------------------------------|-----------------------------------------|
| `tools/sprint_loop/config.py`              | home of the new path-root constant(s)   |
| `tools/chunk_sequence_gate.py`             | already composes verify; will route via constant |
| `tools/cross_family_review.py`             | envelope path checks; route via constant |
| `tools/sign_chunk_token.py`                | canonical JSON + HMAC; route via constant |
| `tools/persistent_referee_stub.py`         | token dir target; route via constant    |
| `tools/sprint-loop.py`                     | evidence output dir default; route via constant |
| `tools/sprint_loop/chunk_close_banner.py`  | banner text mentions token dir; route via constant |
| `tests/test_repo_layout.py`                | allowlist updated in chunk 2 for the new taxonomy |
| `tools/wiki-link-audit.py`                 | exit-check surface for chunk 4          |
| `git mv`                                   | preserves history for path moves        |
| `.gitignore`                               | scratch-run pattern updated in chunk 2  |

The three legitimate overlaps from the brief are handled by rule,
not by co-location:

1. **Planning cites evidence by path.** Living planning docs get
   new paths; committed evidence bytes referring to old paths stay
   as-is (§21) and are covered by `planning/PATH-REDIRECTS.md`.
2. **Code writes evidence at runtime.** `evidence/` becomes the
   path-constant's target; the coupling is one constant, not
   scattered strings.
3. **Evidence reused as test fixtures.** Burned envelopes serving
   as fixtures live on the code side (`tests/fixtures`,
   `tools/fixtures`) with provenance noted; the original evidence
   stays immutable in `evidence/`. Runtime prompts (currently
   `phase-4.5/prompts/`, `phase-5/prompts/`) are planning-authored
   but code-consumed: they land in `planning/` and are referenced
   via the constant.

## 4. Target taxonomy — concrete leaf placement

GROK-style choice per the brief (prefer minimal citation churn):

- **`evidence/<phase>/`** — envelopes, manifests, run trees, tokens.
  - `evidence/phase-0/` ← `phase-0/evidence/`
  - `evidence/phase-1/` ← `phase-1/build-evidence/`, `phase-1/fixtures/` (evidence-shaped fixtures only; test-shaped go to `tests/fixtures/phase-1/`)
  - `evidence/phase-2/` ← `phase-2/build-evidence/`, `phase-2/reviews/`
  - `evidence/phase-3/` ← `phase-3/build-evidence/`, `phase-3/reviews/`
  - `evidence/phase-3.1/` ← `phase-3.1/build-evidence/`
  - `evidence/phase-3.2/` ← `phase-3.2/build-evidence/`, `phase-3.2/reviews/`, `phase-3.2/evidence/` (schema JSONs only; the .py files under this dir are code and move to `tools/`)
  - `evidence/phase-4/` ← `phase-4/*envelope.json`, `phase-4/demo/` evidence, `phase-4/h-ci/`, `phase-4/h3/`
  - `evidence/phase-4.5/` ← `phase-4.5/build-evidence/`, `phase-4.5/tokens/`
- **`planning/<phase>/`** — PRD-adjacent record: RUN-PROMPTs,
  PLANs, KNOWN-ISSUES, RESULTS, design docs, postmortems, READMEs.
  - `planning/phase-0/` ← `phase-0/GO-NO-GO.md`, `phase-0/README.md`
  - `planning/phase-1/` ← `phase-1/KNOWN-ISSUES.md`, `phase-1/README.md`, `phase-1/RUN-LEDGER.md`, `phase-1/open-questions.md`, `phase-1/valid-red.md`, `phase-1/prompts/`, `phase-1/locks/`
  - `planning/phase-2/` ← `phase-2/APPROVAL.md`, `phase-2/KNOWN-ISSUES.md`, `phase-2/README.md`, `phase-2/findings.md`, `phase-2/plan-v1.md`
  - `planning/phase-3/` ← `phase-3/KICKOFF.md`, `phase-3/KNOWN-ISSUES.md`, `phase-3/README.md`, `phase-3/RUN-COMMANDS.md`, `phase-3/prompts/`
  - `planning/phase-3.1/` ← `phase-3.1/RESULTS.md`, `phase-3.1/RUN-PROMPT.md`, `phase-3.1/SPIKE.md`, `phase-3.1/prompts/`, `phase-3.1/locks/`
  - `planning/phase-3.2/` ← `phase-3.2/ASSUMPTIONS.md`, `phase-3.2/BUILD-NOTES.md`, `phase-3.2/EXPLORER-PROMPT.md`, `phase-3.2/RECOMMENDATION.md`, `phase-3.2/RUN-PROMPT.md`, `phase-3.2/SPIKE.md`, `phase-3.2/wiki-refresh-on-merge.md`
  - `planning/phase-3.3/` ← `phase-3.3/SPIKE.md`
  - `planning/phase-4/` ← `phase-4/track-*.md`, `phase-4/post-v3-*prompt.md`, `phase-4/track-execution-review-prompt.md`, `phase-4/demo/*.md`
  - `planning/phase-4.5/` ← all `phase-4.5/*.md`, `phase-4.5/prompts/`, `phase-4.5/adversarial_review/`
  - `planning/phase-5/` ← `phase-5/DESIGN-*.md`, `phase-5/POSTMORTEM-REFEREE-SEAT.md`, `phase-5/TASK-DESIGN-REVIEW-PHASE.md`, `phase-5/prompts/`
- **`tools/<namespace>/`** — code stranded in phase dirs.
  - `tools/phase-1-hooks/` ← `phase-1/hooks/`
  - `tools/phase-1-scripts/` ← `phase-1/scripts/`
  - `tools/phase-1-probes/` ← `phase-1/probes/`
  - `tools/phase-3-gen/` ← `phase-3/gen-telemetry.py`
  - `tools/phase-3.1-gen/` ← `phase-3.1/gen-telemetry.py`
  - `tools/phase-3.2-evidence/` ← `phase-3.2/evidence/*.py` (the schema JSONs stay in `evidence/phase-3.2/`)
  - `tools/phase-4-gen/` ← `phase-4/gen-findings.py`, `phase-4/reconstruct-telemetry.py`
  - `tools/phase-5-scripts/` ← `phase-5/scripts/`

Rationale for choosing `tools/phase-N-<subdir>/` as the leaf naming:
minimum citation churn. Existing code cites `phase-1/scripts/lock.py`;
the redirect is `tools/phase-1-scripts/lock.py` — same path tail, one
prefix flip. A flat `tools/lock.py` would collide (three phases each
have their own `gen-telemetry.py`) and would erase historical
provenance a future reader needs.

## 5. Chunk plan (§18.2 — build in chunks, §18.3 — verify at each boundary)

Every chunk is one commit that (a) moves + fixes exactly the surface
its spec names, (b) leaves the full suite green (194 tests including
`tests/test_repo_layout.py`), (c) is pushed to `origin`, (d) posts a
`REVIEW REQUEST:` line to `STEER.md`, and (e) waits for a
`TOKEN SIGNED:` line + `tools/chunk_sequence_gate.py --check-current-head`
verify before the next chunk opens.

### Chunk 1 — path-root constant + route the gate code

**Problem statement (§13 shape):** the runner and gate code hardcode
the phase-dir prefixes in ~12 code sites. Moving those dirs before
the constants exist would produce a big-bang move that no reviewer
can audit. Chunk 1 introduces a single source of truth for the paths
and routes all gate code through it, with the paths still pointing
to their current homes.

**Surface touched (code only, zero moves):**

- `tools/sprint_loop/config.py`: add path-root constants
  `EVIDENCE_ROOT`, `PLANNING_ROOT`, `TOKENS_ROOT`, `PROMPTS_ROOT`,
  and helper `phase_path(kind, phase, *parts)` — kind ∈
  {"evidence","planning","tokens","prompts"}. Constants take default
  values matching TODAY's layout (`phase-4.5/tokens`,
  `phase-4.5/build-evidence`, `phase-1/scripts`, ...) so behaviour is
  unchanged.
- Route the following through the helper — no behavioural drift:
  - `tools/chunk_sequence_gate.py` (docstring + argparse help only,
    since the caller passes the token path)
  - `tools/cross_family_review.py`
  - `tools/sign_chunk_token.py`
  - `tools/persistent_referee_stub.py`
  - `tools/sprint-loop.py` (evidence output default)
  - `tools/sprint_loop/chunk_close_banner.py`

**Verify (§11 exit check):**

- `python3 -m pytest -q` → all 194 tests still green.
- Add `tests/test_layout_paths.py` with two tests:
  1. every constant resolves to a currently-existing directory; and
  2. the helper's output for `(kind="tokens", phase="phase-4.5")` +
     `chunk-5a.token.json` equals the actual on-disk path.
- Total suite grows from 194 → 196; the layout allowlist is untouched
  in this chunk.

**Ergonomic friction fixed inline (§18.4):**

- `chunk_close_banner.py` prints the token path in prose; replace with
  the helper so the banner cannot drift from the constant.
- `sprint-loop.py`'s CLI help mentions the path in two places; fold
  both to reference the constant.

### Chunk 2 — `git mv` the phase dir content to taxonomy homes

**Problem statement:** phase dir content is functionally three
different things (evidence, planning, code) stored in one silo. Move
each subtree to its taxonomy home, flip the Chunk-1 constants to the
new roots, update the layout allowlist to reflect the new top-level
shape, and update `.gitignore`'s scratch pattern.

**Surface touched:**

- `git mv` per the mapping in §4. All moves are `git mv` (not
  rm+add) so history follows. Evidence bytes are not edited.
- `tools/sprint_loop/config.py`: flip constants to `evidence/`,
  `planning/`, `evidence/<phase>/tokens/` (per §4), `planning/<phase>/prompts/`.
- Any code or shell that bypasses the constant (grepped now: only
  `phase-5/scripts/fire-design-review.sh`'s `RUN_DIR="phase-4.5/build-evidence/${RUN_ID}"`)
  gets rewritten to compose the constant. `fire-design-review.sh`
  moves to `tools/phase-5-scripts/` in the same chunk and picks up
  the constant via a small env-driven shim.
- `tests/test_repo_layout.py`: ALLOWED_TOP_LEVEL loses `phase-0`,
  `phase-1`, `phase-2`, `phase-3`, `phase-3.1`, `phase-3.2`,
  `phase-3.3`, `phase-4`, `phase-4.5`, `phase-5`; gains `evidence`.
  (`planning/` is already in the allowlist.)
- `.gitignore`: keep the existing `phase-*/build-evidence/r-*/`
  pattern (in case any old bytes are ever un-ignored in history
  contexts) and add `evidence/*/build-evidence/r-*/` + `evidence/*/r-*/`
  as the new scratch pattern. Comment names the transition and cites
  this PLAN.
- Any tests referencing hardcoded phase paths get updated to compose
  the constant (grepped: `tests/test_sprint_loop.py` line 419, 1401;
  `tests/test_plan_lint.py` ~11 sites for `phase-4.5/tokens/*` — those
  are string-literal expectations against the constant's default and
  keep whatever value the constant now returns).

**Verify (§11):**

- `python3 -m pytest -q` → 196 tests green.
- `tests/test_repo_layout.py` refuses if any phase-N/ directory is
  still tracked at top level.
- `tests/test_layout_paths.py` (from chunk 1) refuses if any constant
  points to a nonexistent path.
- `git log --follow` on one representative file per subtree confirms
  history is preserved.

**Ergonomic friction fixed inline:**

- `.gitignore` currently claims "evidence is never committed" then
  contradicts itself; chunk 2 leaves the corrected explanation from
  commit `205d392` intact and adds only the new scratch pattern.

### Chunk 3 — living-doc citations + `planning/PATH-REDIRECTS.md`

**Problem statement:** ~150 md citations across PRD, OPERATING-RULES,
skills, wiki, and phase READMEs point at the old paths. Living docs
get updated; **evidence bytes are immutable** — citations inside
committed envelopes / manifests / raw / stream files stay as-is and
are covered by a redirects file.

**Surface touched:**

- `planning/PATH-REDIRECTS.md`: new file. Table of old-prefix →
  new-prefix. Two audiences: (a) a human reader following a stale
  citation in an envelope, (b) `tools/wiki-link-audit.py` if we teach
  it to consult the redirects file (stretch — not required for D1).
- **Living docs** (updates in place):
  - `PRD.md`
  - `tools/OPERATING-RULES.md`
  - `AGENTS.md`
  - `skills/adversarial-sprint/SKILL.md` and
    `skills/sprint-invocation/SKILL.md`
  - `README.md`
  - `tools/conventions/*.md`
  - `droid-wiki/*.md` (only the citations changed; freshness pass is
    D3, not D1)
  - `planning/ROADMAP-REVIEW*.md` (roadmap already lives here)
  - phase READMEs and RUN-PROMPTs — these moved to
    `planning/<phase>/` in chunk 2; their citations get updated in
    chunk 3.
- **Immutable — do NOT edit:** everything under `evidence/`,
  including committed envelope JSONs, manifests, `MANIFEST.md`,
  `raw`/`stream` outputs, and any file whose bytes are HMAC-signed
  or SHA-quoted somewhere else.

**Verify (§11):**

- `python3 -m pytest -q` → 196 tests green.
- `grep -rn --include='*.md' 'phase-[0-9]' planning/ tools/ skills/ droid-wiki/ README.md PRD.md AGENTS.md` returns only intentional citations (each accompanied by a same-line "→ evidence/..." redirect or is a historical narrative that documents the old path deliberately).
- `planning/PATH-REDIRECTS.md` covers every old-prefix that still
  appears in any evidence file (`grep -rn --include='*.json' --include='*.raw.txt' --include='*.stream.json' 'phase-[0-9]' evidence/`
  → each hit's prefix is in the redirects table).

**Ergonomic friction fixed inline:**

- If `wiki-link-audit.py` gets a new false positive from the move,
  fix it in the same chunk under the same guard rail (§14: through
  the constant).

### Chunk 4 — exit check: wiki-link-audit + full suite + run-sprint dry-run

**Problem statement:** the D1 exit criteria must be checked, not
assumed (§11). Chunk 4 runs the three exit checks the brief names.

**Surface touched:**

- No new code moves. Chunk 4 is the exit gate.
- If any check fails, chunk 4 lands the fix; only if the fix is
  bounded (one file, one obvious defect, one commit) — otherwise
  STOP per §5 and record BLOCKED.

**Verify (§11):**

- `python3 tools/wiki-link-audit.py` → green (no dead links).
- `python3 -m pytest -q` → 196 tests green.
- `python3 tools/sprint-loop.py --dry-run --non-interactive
  --framework-root . --pilot-root . --pilot-python
  $(python3 -c 'import sys;print(sys.executable)') --chunks-file
  tests/fixtures/minimal-chunks.json` (or the closest existing
  fixture; chunk 4 lands the fixture if it does not exist) → exit 0.
  This exercises the constant-routed evidence-dir default without
  firing any real reviewer.
- Post-D1 `git log --stat` shows exactly N + 1 commits landed on
  `factory/layout-refactor` since branching from `main` (Chunk 1
  through Chunk 4 + this PLAN commit), each with a signed token in
  `evidence/phase-4.5/tokens/` (post-move location).

**Ergonomic friction fixed inline:** whatever the exit checks
surface.

## 6. Rule application table (§18 receipt)

| Rule           | Where it applies in D1                                                |
|----------------|-----------------------------------------------------------------------|
| §5 STOP        | any red suite after one bounded fix; any evidence-path ambiguity      |
| §7 assert      | verify via file listings, `git log --follow`, `pytest -q`, not exit codes |
| §11 exit gate  | per-chunk verify block (above) + chunk-4 exit checks                  |
| §13 executor   | this PLAN is problem+constraints; no sed lists                        |
| §14 shim       | `run-with-model.sh` + `adapters/factory.py` untouched by D1; any script that spawns droid stays through them |
| §15 git truth  | `git log --follow` on representative moved files; chunk-4 log verify  |
| §17 envelope   | D1 is the entire capacity; D2/D3 gated on D1 close                    |
| §18 compose    | §3 primitives table + chunk shape                                     |
| §18.4 friction | banner + CLI help + `.gitignore` + audit tool false-positives handled inline |
| §20 gate       | chunks land only after prior signed token verifies via `chunk_sequence_gate.py` |
| §21 evidence   | evidence bytes untouched; PATH-REDIRECTS.md carries the delta         |
| §22 identity   | builder posts REVIEW REQUEST, does not fire reviewers or write tokens |

## 7. Adversarial review plan (§18.5)

Cross-family panel via the referee, disjoint from the implementer
(`factory/droid`, anthropic family). Reviewers requested via
`STEER.md` — the builder never selects or fires them itself.

Three review points per §18.5 + operator direction:

1. **PLAN review** — this file, before any chunk code lands.
   Reviewer verdict gates chunk-spec drafting.
2. **Chunk-spec review** — one committed `CHUNK-N-SPEC.md` per
   chunk before code lands. Reviewer verdict gates the code.
3. **Chunk-close review** — landed code + green suite + push. Signed
   token issued after cross-family ACCEPT gates the next chunk.

## 8. Distill hooks (§18.6 — after D1 lands)

Candidates to distill into rules or skills once D1 closes:

- If path constants prove load-bearing here, propose a
  `layout-constants` skill or an §18-appendix on "moves land on
  path-constant first, not string-literal search-and-replace."
- If `PATH-REDIRECTS.md` catches a stale citation an audit tool
  would have missed, propose teaching `wiki-link-audit.py` to
  consult the redirects table and add a `--redirects` flag.
- If the operator-visible chunk cadence (plan-verdict, spec-verdict,
  code-verdict) works, propose a diagram in
  `skills/adversarial-sprint/SKILL.md` making the three verdict
  gates explicit.

## 9. Success criteria (§11 exit — checked, not assumed)

D1 closes successfully iff **all** hold:

1. Branch `factory/layout-refactor` has commits for PLAN,
   Chunk 1, Chunk 2, Chunk 3, Chunk 4 (5 landed commits minimum).
2. `main` is byte-identical to `5dcf67c` throughout D1.
3. Top-level `phase-0` … `phase-5` directories no longer exist;
   `evidence/` and `planning/<phase>/` do; `tools/phase-N-*/`
   subdirs exist for the moved code.
4. `python3 -m pytest -q` reports 196 tests, all green (194
   pre-existing + 2 new from Chunk 1).
5. `tests/test_repo_layout.py` allowlist has been updated and passes.
6. `tools/wiki-link-audit.py` returns green.
7. `planning/PATH-REDIRECTS.md` exists and covers every old-prefix
   still cited inside `evidence/`.
8. Each chunk has a `evidence/phase-4.5/tokens/chunk-D1-N.token.json`
   (post-move path) whose HMAC verifies under
   `EVIDENCE_SIGNING_KEY` and whose `chunk_commit_sha` matches the
   chunk's HEAD at the time it landed.

If any bullet fails after one bounded fix attempt, the deliverable
STOPs, `BLOCKED:` is posted to `STEER.md`, and a
BLOCKED-with-evidence note is committed on the branch. An incomplete
night with clean tokens beats a complete night without.
