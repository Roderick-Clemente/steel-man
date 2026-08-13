# PLAN — layout refactor D1 (v2)

Derived from `CLEANUP-PLAN.md` (machine-local operator brief) per
OPERATING-RULES §18. This document is the committed plan the D1
chunks fire against; the brief itself is gitignored and does not
travel. Reviewer verdict on this file gates the drafting of chunk
specs; chunk-spec verdict gates code; code verdict + signed token
gates the next chunk.

**Revision history.** v1 was committed at `b1ef52e` and received
`VERDICT: REJECT` from both Tier-2 reviewers (grok-4.5 session
`9d6d9aaf`, gemini-3.1-pro-preview session `05e750b9`; referee
token at commit `0ea80f0`, jaccard=0.20, session_ids_distinct=true).
v2 folds in their findings: (a) Chunk 1 route inventory is now a
grounded grep, not a claim; (b) `SCRIPTS_ROOT`/`LOCKS_ROOT`
constants added; (c) Chunk 4 exit check is real, not dry-run;
(d) `plan-lint.py` regex + `pytest.ini` norecursedirs + CI workflow
+ `test_envelope_manifest.py` named on Chunk 2; (e) `phase-1/locks/`
rehomed to code side, `phase-1/fixtures/` to `tests/fixtures/phase-1/`;
(f) §7 wording aligned with §24; (g) success criterion 2 uses
`git merge-base` range, not byte-identity.

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
- The builder does NOT hold `EVIDENCE_SIGNING_KEY` (the referee's
  key), does NOT write to `phase-4.5/tokens/` (or its D1
  replacement), and does NOT sign chunk-close tokens. Per §24,
  the builder MAY act as orchestrator and fire Tier-2 validators
  via `bash tools/run-with-model.sh droid exec --model <id> ...`
  when (i) the reviewer model IDs are operator-selected (not
  chosen by the builder) and (ii) the builder holds no signing
  key in its env. The persistent referee audits and signs; the
  builder never signs.
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
| `tools/sprint_loop/config.py`              | home of the new path-root constants     |
| `tools/chunk_sequence_gate.py`             | already composes verify; will route via constant |
| `tools/cross_family_review.py`             | envelope path checks; route via constant |
| `tools/sign_chunk_token.py`                | canonical JSON + HMAC; route via constant |
| `tools/persistent_referee_stub.py`         | token dir target; route via constant    |
| `tools/sprint-loop.py`                     | evidence output dir default; route via constant |
| `tools/sprint_loop/per_chunk.py`           | 7 hardcoded `os.path.join` sites → route via constant |
| `tools/orchestrate-review.py`              | hardcoded `local_backend.py` path → route via constant |
| `tools/sprint_loop/chunk_close_banner.py`  | banner text mentions token dir; route via constant |
| `tools/plan-lint.py`                       | path-prefix regex (lines 903, 1151) needs `evidence`/`planning` |
| `tests/test_repo_layout.py`                | allowlist updated in chunk 2 for the new taxonomy |
| `tests/test_sprint_loop.py`                | assertions on `default_locks_dir`/`default_evidence_dir` (lines 414, 419) |
| `tools/wiki-link-audit.py`                 | exit-check surface for chunk 4          |
| `git mv`                                   | preserves history for path moves        |
| `.gitignore`                               | scratch-run pattern updated in chunk 2  |
| `pytest.ini`                               | `norecursedirs` updated in chunk 2       |
| `.github/workflows/adversarial-sprint-ci.yml` | hardcoded phase paths updated in chunk 2 |

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
  - `evidence/phase-1/` ← `phase-1/build-evidence/`
  - `evidence/phase-2/` ← `phase-2/build-evidence/`, `phase-2/reviews/`
  - `evidence/phase-3/` ← `phase-3/build-evidence/`, `phase-3/reviews/`
  - `evidence/phase-3.1/` ← `phase-3.1/build-evidence/`
  - `evidence/phase-3.2/` ← `phase-3.2/build-evidence/`, `phase-3.2/reviews/`, `phase-3.2/evidence/` **schema JSONs only** (`bundle_schema_v1.json`, `security_allowlist.json`); the `.py` files under this dir are code and move to `tools/`
  - `evidence/phase-4/` ← `phase-4/*envelope.json`, `phase-4/demo/` evidence, `phase-4/h-ci/`, `phase-4/h3/`
  - `evidence/phase-4.5/` ← `phase-4.5/build-evidence/`, `phase-4.5/tokens/`
- **`planning/<phase>/`** — PRD-adjacent record: RUN-PROMPTs,
  PLANs, KNOWN-ISSUES, RESULTS, design docs, postmortems, READMEs.
  - `planning/phase-0/` ← `phase-0/GO-NO-GO.md`, `phase-0/README.md`
  - `planning/phase-1/` ← `phase-1/KNOWN-ISSUES.md`, `phase-1/README.md`, `phase-1/RUN-LEDGER.md`, `phase-1/open-questions.md`, `phase-1/valid-red.md`, `phase-1/prompts/`
  - `planning/phase-2/` ← `phase-2/APPROVAL.md`, `phase-2/KNOWN-ISSUES.md`, `phase-2/README.md`, `phase-2/findings.md`, `phase-2/plan-v1.md`
  - `planning/phase-3/` ← `phase-3/KICKOFF.md`, `phase-3/KNOWN-ISSUES.md`, `phase-3/README.md`, `phase-3/RUN-COMMANDS.md`, `phase-3/prompts/`
  - `planning/phase-3.1/` ← `phase-3.1/RESULTS.md`, `phase-3.1/RUN-PROMPT.md`, `phase-3.1/SPIKE.md`, `phase-3.1/prompts/`
  - `planning/phase-3.2/` ← `phase-3.2/ASSUMPTIONS.md`, `phase-3.2/BUILD-NOTES.md`, `phase-3.2/EXPLORER-PROMPT.md`, `phase-3.2/RECOMMENDATION.md`, `phase-3.2/RUN-PROMPT.md`, `phase-3.2/SPIKE.md`, `phase-3.2/wiki-refresh-on-merge.md`
  - `planning/phase-3.3/` ← `phase-3.3/SPIKE.md`
  - `planning/phase-4/` ← `phase-4/track-*.md`, `phase-4/post-v3-*prompt.md`, `phase-4/track-execution-review-prompt.md`, `phase-4/demo/*.md`
  - `planning/phase-4.5/` ← all `phase-4.5/*.md`, `phase-4.5/prompts/`, `phase-4.5/adversarial_review/`
  - `planning/phase-5/` ← `phase-5/DESIGN-*.md`, `phase-5/POSTMORTEM-REFEREE-SEAT.md`, `phase-5/TASK-DESIGN-REVIEW-PHASE.md`, `phase-5/prompts/`
- **`tools/<namespace>/`** — code stranded in phase dirs. **`phase-1/locks/` is runtime gate input (consumed by `per_chunk.py` and the hook), not a planning artifact — it goes to the code side.**
  - `tools/phase-1-hooks/` ← `phase-1/hooks/`
  - `tools/phase-1-scripts/` ← `phase-1/scripts/`
  - `tools/phase-1-probes/` ← `phase-1/probes/`
  - `tools/phase-1-locks/` ← `phase-1/locks/` **(code side, not planning — this is the v1 misclassification v2 corrects)**
  - `tools/phase-3-gen/` ← `phase-3/gen-telemetry.py`
  - `tools/phase-3.1-gen/` ← `phase-3.1/gen-telemetry.py`
  - `tools/phase-3.2-evidence/` ← `phase-3.2/evidence/*.py` (`local_backend.py`, `consumer.py`, `token_accounting.py`); the schema JSONs stay in `evidence/phase-3.2/`
  - `tools/phase-4-gen/` ← `phase-4/gen-findings.py`, `phase-4/reconstruct-telemetry.py`
  - `tools/phase-5-scripts/` ← `phase-5/scripts/` (incl. `test_envelope_manifest.py`, a self-runner outside `tests/`)
- **`tests/fixtures/phase-1/`** ← `phase-1/fixtures/` **(test fixtures, not evidence — this is the v1 misclassification v2 corrects)**. `phase-1/fixtures/invalid-red/` contains only `test_*.py` files for `valid-red.py` classification; they are test fixtures, not envelopes/manifests.

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
`REVIEW REQUEST:` line to `STEER.md` with populated envelope paths
(after the builder fires Tier-2 as orchestrator per §24), and (e)
waits for a `REVIEW COMPLETE:` line + `tools/chunk_sequence_gate.py
--check-current-head` verify before the next chunk opens.

### Chunk 1 — path-root constants + route ALL hardcoded sites

**Problem statement (§13 shape):** the runner and gate code hardcode
phase-dir prefixes in ~17 code sites (grounded grep below). Moving
those dirs before the constants exist would produce a big-bang move
that no reviewer can audit. Chunk 1 introduces a single source of
truth for the paths and routes every hardcoded site through it,
with the paths still pointing to their current homes.

**Grounded inventory of hardcoded sites (grep-verified, not claimed):**

| File:line | Hardcoded path | Constant that replaces it |
|-----------|----------------|--------------------------|
| `tools/sprint_loop/per_chunk.py:108` | `os.path.join(framework_root, "phase-1", "scripts", "lock.py")` | `SCRIPTS_ROOT / "lock.py"` |
| `tools/sprint_loop/per_chunk.py:112` | `os.path.join(framework_root, "phase-1", "locks")` | `LOCKS_ROOT` |
| `tools/sprint_loop/per_chunk.py:124` | `os.path.join(framework_root, "phase-1", "locks", ...)` | `LOCKS_ROOT / ...` |
| `tools/sprint_loop/per_chunk.py:136` | `os.path.join(framework_root, "phase-1", "locks", ...)` | `LOCKS_ROOT / ...` |
| `tools/sprint_loop/per_chunk.py:164` | `os.path.join(framework_root, "phase-1", "scripts", "valid-red.py")` | `SCRIPTS_ROOT / "valid-red.py"` |
| `tools/sprint_loop/per_chunk.py:213` | `os.path.join(framework_root, "phase-1", "scripts", "verify-green.py")` | `SCRIPTS_ROOT / "verify-green.py"` |
| `tools/sprint_loop/per_chunk.py:279` | `os.path.join(framework_root, "phase-3.2", "evidence", "local_backend.py")` | `EVIDENCE_CODE_ROOT / "local_backend.py"` (or `phase_path("evidence-code", "phase-3.2")`) |
| `tools/sprint_loop/config.py:150` | `os.path.join(self.framework_root, "phase-1", "locks")` (`default_locks_dir`) | `LOCKS_ROOT` |
| `tools/sprint_loop/config.py:155` | `os.path.join(self.framework_root, "phase-4.5", "build-evidence", run_id)` (`default_evidence_dir`) | `EVIDENCE_ROOT / "phase-4.5" / run_id` (flipped in Chunk 2) |
| `tools/orchestrate-review.py:78` | `os.path.join(args.framework_root, "phase-3.2", "evidence", "local_backend.py")` | same constant as per_chunk.py:279 |
| `tools/chunk_sequence_gate.py:9,119` | docstring + argparse help mention `phase-4.5/tokens/` | `TOKENS_ROOT` reference in prose |
| `tools/sign_chunk_token.py:6,135` | docstring mentions `phase-4.5/tokens/` | `TOKENS_ROOT` reference |
| `tools/sprint-loop.py:1116,1118` | CLI help mentions `phase-4.5/build-evidence/` | `EVIDENCE_ROOT` reference |
| `tools/sprint_loop/chunk_close_banner.py:42,51,99` | banner text mentions `phase-4.5/tokens/` and `phase-4.5/build-evidence/` | `TOKENS_ROOT` / `EVIDENCE_ROOT` references |
| `tools/persistent_referee_stub.py` | token dir target | `TOKENS_ROOT` |
| `phase-5/scripts/fire-design-review.sh:87` | `RUN_DIR="phase-4.5/build-evidence/${RUN_ID}"` | compose via env var sourced from a constant-emitting helper |
| `phase-3.2/evidence/local_backend.py:375` | `"verify_green": "phase-1/scripts/verify-green.py"` (a path string in the producer's runtime output JSON) | `SCRIPTS_ROOT / "verify-green.py"` (this is code output, not an evidence byte — the committed demo bundle `chunk1-bundle.json` is immutable, but the producer code that *would* emit it is code and gets the constant) |

**Surface touched (code only, zero moves):**

- `tools/sprint_loop/config.py`: add path-root constants
  `EVIDENCE_ROOT`, `PLANNING_ROOT`, `TOKENS_ROOT`, `PROMPTS_ROOT`,
  `SCRIPTS_ROOT`, `LOCKS_ROOT`, `EVIDENCE_CODE_ROOT` (for the
  `phase-3.2/evidence/*.py` code that moves to `tools/phase-3.2-evidence/`
  in Chunk 2), and helper `phase_path(kind, phase, *parts)` — kind ∈
  {"evidence","planning","tokens","prompts","scripts","locks",
  "evidence-code"}. Constants take default values matching TODAY's
  layout so behaviour is unchanged.
- Route every site in the inventory table above through the helper.
  No behavioural drift — the constants resolve to today's paths.
- `phase-5/scripts/fire-design-review.sh`: introduce a tiny
  `tools/sprint_loop/paths.sh` (sourced) that exports the same
  constants as env vars, so the shell can compose
  `RUN_DIR="${EVIDENCE_ROOT}/phase-4.5/${RUN_ID}"` without
  duplicating the path. (§18.4: fix the friction inline — a shell
  that hardcodes a path the Python constant owns is the same
  silent-scope-lie §14 warns about.)

**Verify (§11 exit check):**

- `python3 -m pytest -q` → all 194 tests still green. The
  `tests/test_sprint_loop.py` assertions on `default_locks_dir` and
  `default_evidence_dir` (lines 414, 419) keep passing because the
  constants default to today's paths.
- Add `tests/test_layout_paths.py` with three tests:
  1. every constant resolves to a currently-existing directory;
  2. the helper's output for `(kind="tokens", phase="phase-4.5")` +
     `chunk-5a.token.json` equals the actual on-disk path
     `phase-4.5/tokens/chunk-5a.token.json`;
  3. `per_chunk.py`'s 7 `os.path.join` sites and
     `orchestrate-review.py:78` all resolve through the helper (a
     grep assertion: none of those lines still contain a literal
     `"phase-1"` or `"phase-3.2"` string).
- Total suite grows from 194 → 197; the layout allowlist is untouched
  in this chunk.

**Ergonomic friction fixed inline (§18.4):**

- `chunk_close_banner.py` prints the token path in prose; replace with
  the helper so the banner cannot drift from the constant.
- `sprint-loop.py`'s CLI help mentions the path in two places; fold
  both to reference the constant.
- The shell/Python constant split (`paths.sh`) is the friction fix
  for `fire-design-review.sh` — without it, Chunk 2 would have to
  rewrite the shell path anyway, and the rewrite would own the debt.

### Chunk 2 — `git mv` the phase dir content to taxonomy homes + flip constants + fix linters

**Problem statement:** phase dir content is functionally three
different things (evidence, planning, code) stored in one silo. Move
each subtree to its taxonomy home, flip the Chunk-1 constants to the
new roots, update the layout allowlist, update `.gitignore`'s scratch
pattern, update `pytest.ini`'s `norecursedirs`, update
`plan-lint.py`'s path-prefix regex, and update the CI workflow's
hardcoded paths.

**Surface touched:**

- `git mv` per the mapping in §4. All moves are `git mv` (not
  rm+add) so history follows. Evidence bytes are not edited.
- `tools/sprint_loop/config.py`: flip constants to `evidence/`,
  `planning/`, `evidence/phase-4.5/tokens/` (per §4),
  `planning/phase-4.5/prompts/`, `tools/phase-1-scripts/`,
  `tools/phase-1-locks/`, `tools/phase-3.2-evidence/`.
- `tools/plan-lint.py:903,1151`: add `evidence` and `planning` to
  the valid-prefix regex
  `r"^(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry|evidence|planning)/[\w/.-]+$"`.
  Without this, `plan-lint.py` rejects D1's own plan and any future
  plan that cites the new paths.
- `pytest.ini`: `norecursedirs` loses `phase-0`…`phase-4.5`; gains
  `evidence` (so pytest does not crawl evidence dirs) and
  `tools/phase-5-scripts` (because `test_envelope_manifest.py` is a
  self-runner outside `tests/` and should not be collected by the
  top-level pytest run; it has its own invocation).
- `tests/test_repo_layout.py`: ALLOWED_TOP_LEVEL loses `phase-0`,
  `phase-1`, `phase-2`, `phase-3`, `phase-3.1`, `phase-3.2`,
  `phase-3.3`, `phase-4`, `phase-4.5`, `phase-5`; gains `evidence`.
  (`planning/` is already in the allowlist.)
- `.gitignore`: keep the existing `phase-*/build-evidence/r-*/`
  pattern (in case any old bytes are ever un-ignored in history
  contexts) and add `evidence/*/build-evidence/r-*/` +
  `evidence/*/r-*/` as the new scratch pattern. Comment names the
  transition and cites this PLAN.
- `.github/workflows/adversarial-sprint-ci.yml:165,169,191,245`:
  update `framework/phase-3.2/evidence/local_backend.py` →
  `framework/tools/phase-3.2-evidence/local_backend.py`;
  `pilot/phase-1/locks/` stays as-is (that's the PILOT's locks dir,
  not the framework's — the workflow runs the framework against a
  pilot checkout); line 245's prose citation of
  `phase-3.2/evidence/consumer.py` → `tools/phase-3.2-evidence/consumer.py`.
- `tests/test_sprint_loop.py:414,419`: update the expected paths
  from `/tmp/fw/phase-1/locks` → `/tmp/fw/tools/phase-1-locks` and
  `/tmp/fw/phase-4.5/build-evidence/r-001` →
  `/tmp/fw/evidence/phase-4.5/r-001` (these are assertions against
  the constant's flipped value).
- `tests/test_plan_lint.py` (~11 sites): these are string-literal
  expectations `phase-4.5/tokens/chunk-5a.token.json` used as test
  fixtures. They are NOT routed through the constant (they are test
  inputs, not code paths). Update them to
  `evidence/phase-4.5/tokens/chunk-5a.token.json` so the test
  fixtures reflect the post-move reality. (Alternative: leave them
  as old-path fixtures and add a `PATH-REDIRECTS` consult to
  `plan-lint.py` — but that is more work for no gain; the test
  fixtures are not evidence bytes, they are test inputs.)
- `tests/test_sprint_loop.py:701,731,1372,1398`: these are
  `"lock_file": "phase-1/locks/..."` test inputs. Update to
  `"tools/phase-1-locks/..."`.
- `phase-3.2/evidence/local_backend.py:375`: the
  `"verify_green": "phase-1/scripts/verify-green.py"` string in
  the producer's runtime output. This is CODE (the producer emits
  this string), not an evidence byte (the committed demo bundle
  `chunk1-bundle.json` is immutable, but the producer code that
  *would* emit it is code and gets the constant). Update to
  `tools/phase-1-scripts/verify-green.py`.

**Verify (§11):**

- `python3 -m pytest -q` → 197 tests green.
- `tests/test_repo_layout.py` refuses if any `phase-N/` directory
  is still tracked at top level.
- `tests/test_layout_paths.py` (from chunk 1) refuses if any
  constant points to a nonexistent path (the flipped constants
  must resolve to the new dirs).
- `tools/plan-lint.py --self-check` (or equivalent) does not
  reject `planning/layout-refactor/PLAN.md` for citing `evidence/`
  or `planning/` paths.
- `git log --follow` on one representative file per subtree
  confirms history is preserved.

**Ergonomic friction fixed inline:**

- `.gitignore` currently claims "evidence is never committed" then
  contradicts itself; chunk 2 leaves the corrected explanation from
  commit `205d392` intact and adds only the new scratch pattern.
- `pytest.ini`'s `norecursedirs` listing the soon-deleted
  `phase-0`…`phase-4.5` is stale the moment Chunk 2 lands; fix it
  in the same commit.

### Chunk 3 — living-doc citations + `planning/PATH-REDIRECTS.md`

**Problem statement:** ~150 md citations across PRD, OPERATING-RULES,
skills, wiki, and phase READMEs point at the old paths. Living docs
get updated; **evidence bytes are immutable** — citations inside
committed envelopes / manifests / raw / stream files stay as-is and
are covered by a redirects file.

**Surface touched (living docs — bounded by an explicit allowlist):**

- `PRD.md`
- `tools/OPERATING-RULES.md`
- `AGENTS.md`
- `skills/adversarial-sprint/SKILL.md` and
  `skills/sprint-invocation/SKILL.md`
- `README.md`
- `tools/conventions/*.md`
- `tools/README.md`, `tools/KNOWN-ISSUES.md`,
  `tools/PHASE-0.5-CLOSE.md`, `tools/RUN-LEDGER.md`,
  `tools/REPRODUCE.md` (these are framework docs that cite phase
  paths)
- `droid-wiki/*.md` **— path tokens only** (e.g.
  `phase-1/scripts/lock.py` → `tools/phase-1-scripts/lock.py`).
  Content freshness (role-split, planning/ move, README v2) is D3,
  not D1. Do not pull D3 into D1.
- `planning/ROADMAP-REVIEW*.md` (roadmap already lives here)
- `planning/<phase>/` READMEs and RUN-PROMPTs — these moved to
  `planning/<phase>/` in chunk 2; their citations get updated in
  chunk 3.

**Hard stop (capacity bound, per §17):** the verify step greps for
residual `phase-[0-9]` citations in the allowlisted living docs. If
residual hits are only historical narrative (e.g. "Phase 1 built
`phase-1/scripts/lock.py`" in a postmortem that documents the old
path deliberately), STOP — document them in
`planning/PATH-REDIRECTS.md` rather than rewriting the narrative.
The bullet list above is the file allowlist; if a file not on the
list surfaces a citation, it is NOT in scope for D1 (record as
follow-on).

**Immutable — do NOT edit:** everything under `evidence/`,
including committed envelope JSONs, manifests, `MANIFEST.md`,
`raw`/`stream` outputs, and any file whose bytes are HMAC-signed
or SHA-quoted somewhere else. Also immutable: the test fixtures in
`tests/test_plan_lint.py` that were already updated in Chunk 2
(they are test inputs, not evidence, but they are not living docs
either).

**`planning/PATH-REDIRECTS.md` shape:**

- Table of old-prefix → new-prefix.
- **Matching algorithm (specified, not hand-waved):**
  1. strip an optional absolute repo-root prefix
     (`/Users/factory/work/adversarial-sprint-dev/`) from the
     cited path;
  2. match the longest old-prefix in the table against the
     resulting relative path;
  3. apply only to path-shaped tokens (regex:
     `(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry|evidence|planning)/[\w/.-]+`);
  4. leave prose mentions ("Phase 1 built…") untouched.
- One fixture example from a real envelope path shape (e.g.
  `phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`
  →
  `evidence/phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`).

**Verify (§11):**

- `python3 -m pytest -q` → 197 tests green.
- `grep -rn --include='*.md' 'phase-[0-9]' <allowlisted-living-docs>`
  returns only intentional historical-narrative citations, each
  accompanied by a same-line "(now at `tools/...` or `evidence/...`)"
  redirect note OR recorded in `planning/PATH-REDIRECTS.md` as a
  historical-narrative exception.
- `planning/PATH-REDIRECTS.md` covers every old-prefix that still
  appears in any evidence file
  (`grep -rn --include='*.json' --include='*.raw.txt' --include='*.stream.json' 'phase-[0-9]' evidence/`
  → each hit's prefix is in the redirects table).

**Ergonomic friction fixed inline:**

- If `wiki-link-audit.py` gets a new false positive from the move,
  fix it in the same chunk under the same guard rail (§14: through
  the constant).

### Chunk 4 — exit check: wiki-link-audit + full suite + REAL (non-dry) fixture run

**Problem statement:** the D1 exit criteria must be checked, not
assumed (§11). The v1 PLAN's `run-sprint --dry-run` check
**structurally cannot catch broken script paths** — `per_chunk.py`'s
`if dry_run:` branches return synthetic manifests and skip the real
`subprocess.run` calls to `phase-1/scripts/*`. v2 replaces the
dry-run with a real fixture invocation and a path-existence test
assertion.

**Surface touched:**

- No new code moves. Chunk 4 is the exit gate.
- If any check fails, chunk 4 lands the fix; only if the fix is
  bounded (one file, one obvious defect, one commit) — otherwise
  STOP per §5 and record BLOCKED.

**Verify (§11 — checked, not assumed):**

1. `python3 tools/wiki-link-audit.py` → green (no dead links).
2. `python3 -m pytest -q` → 197 tests green.
3. **Real (non-dry) fixture run:** `python3 tools/sprint-loop.py
   --framework-root . --pilot-root . --pilot-python
   $(python3 -c 'import sys;print(sys.executable)') --chunks-file
   tests/fixtures/minimal-chunks.json` (NO `--dry-run` flag). This
   exercises the constant-routed `per_chunk.py` shell-outs to
   `tools/phase-1-scripts/{lock,valid-red,verify-green}.py` against
   a minimal fixture. If the paths are broken by the move, this
   run crashes with `FileNotFoundError` — the §7 reality-assertion
   the dry-run was structurally blind to. Chunk 4 lands the
   `tests/fixtures/minimal-chunks.json` fixture if it does not
   already exist (a 1-chunk spec that points at an existing
   `tests/fixtures/phase-1/` test file).
4. **Path-existence test assertion:** `tests/test_layout_paths.py`
   (grown in Chunk 1) gains a fourth test in Chunk 4 that asserts
   `per_chunk.py`'s constructed script paths
   (`SCRIPTS_ROOT / "lock.py"`, etc.) resolve to files that exist
   on disk. This is the belt-and-suspenders check that does not
   depend on running the full runner.
5. Post-D1 `git log --stat` shows exactly N + 1 commits landed on
   `factory/layout-refactor` since branching from `main` (Chunk 1
   through Chunk 4 + this PLAN commit), each with a signed token
   in `evidence/phase-4.5/tokens/` (post-move location) whose HMAC
   verifies and whose `chunk_commit_sha` matches the chunk's HEAD.

**Ergonomic friction fixed inline:** whatever the exit checks
surface.

## 6. Rule application table (§18 receipt)

| Rule           | Where it applies in D1                                                |
|----------------|-----------------------------------------------------------------------|
| §5 STOP        | any red suite after one bounded fix; any evidence-path ambiguity      |
| §7 assert      | verify via file listings, `git log --follow`, `pytest -q`, real (non-dry) fixture run, not exit codes or dry-run strings |
| §11 exit gate  | per-chunk verify block (above) + chunk-4 exit checks (real run + path-existence test) |
| §13 executor   | this PLAN is problem+constraints; no sed lists                        |
| §14 shim       | `run-with-model.sh` + `adapters/factory.py` untouched by D1; any script that spawns droid stays through them; `paths.sh` mirrors the Python constant so the shell does not own a path the Python constant owns |
| §15 git truth  | `git log --follow` on representative moved files; chunk-4 log verify  |
| §17 envelope   | D1 is the entire capacity; D2/D3 gated on D1 close; Chunk 3 has a hard stop on residual citations |
| §18 compose    | §3 primitives table + chunk shape; grounded inventory table in Chunk 1 |
| §18.4 friction | banner + CLI help + `.gitignore` + `pytest.ini` + `plan-lint.py` regex + `paths.sh` shell mirror + audit tool false-positives handled inline |
| §20 gate       | chunks land only after prior signed token verifies via `chunk_sequence_gate.py` |
| §21 evidence   | evidence bytes untouched; PATH-REDIRECTS.md carries the delta; test fixtures are NOT evidence bytes (updated in Chunk 2 as test inputs) |
| §22 identity   | builder posts REVIEW REQUEST, fires Tier-2 as orchestrator (§24) when models are operator-selected and no signing key held; never signs; referee audits and signs |
| §24 fire-XOR-sign | builder may fire as orchestrator; referee audits and signs only; never both at once for the same chunk |

## 7. Adversarial review plan (§18.5)

Cross-family panel via the referee, disjoint from the implementer
(`factory/droid`, anthropic family). Reviewers are operator-selected
(`grok-4.5`, `gemini-3.1-pro-preview`); the builder fires them as
orchestrator per §24 (no signing key held by the builder), captures
raw stdout to
`phase-4.5/build-evidence/<run-id>/<artifact>/<model>.json`, posts
`VALIDATE COMPLETE:` markers, then posts `REVIEW REQUEST:` with
populated paths. Referee audits §21/§17.2/§23 and signs.

Three review points per §18.5 + operator direction:

1. **PLAN review** — this file, before any chunk code lands.
   Reviewer verdict gates chunk-spec drafting. (v1 REJECT at
   `0ea80f0`; v2 is this revision.)
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
- If the dry-run-vs-real-run gap (Chunk 4 v1→v2 fix) is a
  recurring shape, propose an §11-appendix on "dry-run is not a
  path-existence check; pair it with a real run or a path-existence
  test."

## 9. Success criteria (§11 exit — checked, not assumed)

D1 closes successfully iff **all** hold:

1. Branch `factory/layout-refactor` has commits for PLAN,
   Chunk 1, Chunk 2, Chunk 3, Chunk 4 (5 landed commits minimum).
2. **No commits landed on `main` during the run**, verified via
   `git merge-base --is-ancestor <branch-point> main && git rev-list
   <branch-point>..main --count` returns 0 (not byte-identity to a
   pinned SHA — `main` may have moved before the freeze, the
   criterion is "no movement during the run").
3. Top-level `phase-0` … `phase-5` directories no longer exist;
   `evidence/` and `planning/<phase>/` do; `tools/phase-N-*/`
   subdirs exist for the moved code.
4. `python3 -m pytest -q` reports 197 tests, all green (194
   pre-existing + 3 new from Chunk 1 + 1 new from Chunk 4).
5. `tests/test_repo_layout.py` allowlist has been updated and passes.
6. `tools/wiki-link-audit.py` returns green.
7. `tools/plan-lint.py` accepts `planning/layout-refactor/PLAN.md`
   (regex fix in Chunk 2 is live).
8. `planning/PATH-REDIRECTS.md` exists and covers every old-prefix
   still cited inside `evidence/`.
9. Each chunk has a `evidence/phase-4.5/tokens/chunk-D1-N.token.json`
   (post-move path) whose HMAC verifies under
   `EVIDENCE_SIGNING_KEY` and whose `chunk_commit_sha` matches the
   chunk's HEAD at the time it landed.
10. **Real (non-dry) fixture run** (Chunk 4 verify step 3) exits 0
    without `FileNotFoundError` on any moved script path.

If any bullet fails after one bounded fix attempt, the deliverable
STOPs, `BLOCKED:` is posted to `STEER.md`, and a
BLOCKED-with-evidence note is committed on the branch. An incomplete
night with clean tokens beats a complete night without.
