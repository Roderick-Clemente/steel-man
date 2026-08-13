# CHUNK-2-SPEC — git mv phase dirs to taxonomy homes + flip constants + fix linters

**Parent PLAN:** `planning/layout-refactor/PLAN.md` v3 (`ed98cd3`)
**Branch:** `factory/layout-refactor`
**Chunk ID:** `chunk-D1-2`
**Predecessor:** `chunk-D1-1` (must have verified signed token)
**Successor gate:** `tools/chunk_sequence_gate.py --prior-token evidence/phase-4.5/tokens/chunk-D1-2.token.json --next-chunk-id chunk-D1-3`

## 1. Problem statement (§13)

Phase dir content is functionally three different things (evidence,
planning, code) stored in one silo. This chunk moves each subtree to
its taxonomy home, flips the Chunk-1 constants to the new roots
(segment-preserving), updates the layout allowlist, updates
`.gitignore`'s scratch pattern, updates `pytest.ini`'s
`norecursedirs`, updates `plan-lint.py`'s path-prefix regex, and
updates the CI workflow's hardcoded paths. Evidence bytes are
immutable — `git mv` preserves the bytes, no edits.

## 2. Surface touched

### 2.1 `git mv` operations (per PLAN §4 taxonomy)

All moves are `git mv` (not rm+add) so history follows. The
executor must move every tracked file; the allowlist test (§4.2)
refuses if any `phase-N/` directory is still tracked at top level.

**Evidence moves** (→ `evidence/<phase>/`):
- `phase-0/evidence/` → `evidence/phase-0/`
- `phase-1/build-evidence/` → `evidence/phase-1/`
- `phase-2/build-evidence/`, `phase-2/reviews/` (envelope JSONs only) → `evidence/phase-2/`
- `phase-3/build-evidence/`, `phase-3/reviews/` (envelope JSONs only) → `evidence/phase-3/`
- `phase-3.1/build-evidence/` → `evidence/phase-3.1/`
- `phase-3.2/build-evidence/`, `phase-3.2/reviews/` (envelope JSONs only — **`review-prompt.md` is planning, NOT evidence**), `phase-3.2/evidence/` (schema JSONs `bundle_schema_v1.json`, `security_allowlist.json` only — the `.py` files are code) → `evidence/phase-3.2/`
- `phase-4/*envelope.json`, `phase-4/h-ci/`, `phase-4/h3/` → `evidence/phase-4/` (the `demo/` dir contains only `.md` files — it is planning, NOT evidence)
- `phase-4.5/build-evidence/`, `phase-4.5/tokens/` → `evidence/phase-4.5/`

**Planning moves** (→ `planning/<phase>/`):
- `phase-0/GO-NO-GO.md`, `phase-0/README.md` → `planning/phase-0/`
- `phase-1/KNOWN-ISSUES.md`, `phase-1/README.md`, `phase-1/RUN-LEDGER.md`, `phase-1/open-questions.md`, `phase-1/valid-red.md`, `phase-1/prompts/` → `planning/phase-1/`
- `phase-2/APPROVAL.md`, `phase-2/KNOWN-ISSUES.md`, `phase-2/README.md`, `phase-2/findings.md`, `phase-2/plan-v1.md` → `planning/phase-2/`
- `phase-3/KICKOFF.md`, `phase-3/KNOWN-ISSUES.md`, `phase-3/README.md`, `phase-3/RUN-COMMANDS.md`, `phase-3/prompts/` → `planning/phase-3/`
- `phase-3.1/RESULTS.md`, `phase-3.1/RUN-PROMPT.md`, `phase-3.1/SPIKE.md`, `phase-3.1/prompts/` → `planning/phase-3.1/`
- `phase-3.2/ASSUMPTIONS.md`, `phase-3.2/BUILD-NOTES.md`, `phase-3.2/EXPLORER-PROMPT.md`, `phase-3.2/RECOMMENDATION.md`, `phase-3.2/RUN-PROMPT.md`, `phase-3.2/SPIKE.md`, `phase-3.2/wiki-refresh-on-merge.md`, **`phase-3.2/reviews/review-prompt.md`** → `planning/phase-3.2/`
- `phase-3.3/SPIKE.md` → `planning/phase-3.3/`
- `phase-4/track-*.md`, `phase-4/post-v3-*prompt.md`, `phase-4/track-execution-review-prompt.md`, **`phase-4/demo/*.md`** → `planning/phase-4/`
- All `phase-4.5/*.md`, `phase-4.5/prompts/`, `phase-4.5/adversarial_review/` → `planning/phase-4.5/`
- `phase-5/DESIGN-*.md`, `phase-5/POSTMORTEM-REFEREE-SEAT.md`, `phase-5/TASK-DESIGN-REVIEW-PHASE.md`, `phase-5/prompts/` → `planning/phase-5/`

**Code moves** (→ `tools/phase-N-<subdir>/`):
- `phase-1/hooks/` → `tools/phase-1-hooks/`
- `phase-1/scripts/` → `tools/phase-1-scripts/`
- `phase-1/probes/` → `tools/phase-1-probes/`
- `phase-1/locks/` → `tools/phase-1-locks/`
- `phase-3.1/locks/` → `tools/phase-3.1-locks/`
- `phase-3/gen-telemetry.py` → `tools/phase-3-gen/`
- `phase-3.1/gen-telemetry.py` → `tools/phase-3.1-gen/`
- `phase-3.2/evidence/*.py` (`local_backend.py`, `consumer.py`, `token_accounting.py`) → `tools/phase-3.2-evidence/`
- `phase-4/gen-findings.py`, `phase-4/reconstruct-telemetry.py` → `tools/phase-4-gen/`
- `phase-5/scripts/` → `tools/phase-5-scripts/`

**Test fixture moves** (→ `tests/fixtures/phase-1/`):
- `phase-1/fixtures/` → `tests/fixtures/phase-1/` (test fixtures, NOT evidence)

### 2.2 Flip the Chunk-1 constants

`tools/sprint_loop/config.py`: flip the constants to the new
taxonomy paths (segment-preserving):
- `EVIDENCE_ROOT` → `"evidence"`
- `PLANNING_ROOT` → `"planning"`
- `TOKENS_ROOT` → `os.path.join(EVIDENCE_ROOT, "phase-4.5", "tokens")` (relative to framework_root)
- `PROMPTS_ROOT` → `os.path.join(PLANNING_ROOT, "phase-4.5", "prompts")`
- `SCRIPTS_ROOT` → `os.path.join(framework_root, "tools", "phase-1-scripts")`
- `LOCKS_ROOT` → `os.path.join(framework_root, "tools", "phase-1-locks")`
- `EVIDENCE_CODE_ROOT` → `os.path.join(framework_root, "tools", "phase-3.2-evidence")`
- `default_evidence_dir` composes `EVIDENCE_ROOT / "phase-4.5" / "build-evidence" / run_id` (segment-preserving)

`tools/sprint_loop/paths.sh`: flip the shell constants to match.

### 2.3 Linter / config / CI fixes

- `tools/plan-lint.py:903`: add `evidence` and `planning` to the
  valid-prefix regex
  `r"^(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry|evidence|planning)/[\w/.-]+$"`.
  Line 1151's regex is unanchored
  (`(?:...)/[\w/.]+\.\w+`); add `evidence` and `planning` there too.
- `pytest.ini`: `norecursedirs` loses `phase-0`…`phase-4.5`; gains
  `evidence` and `tools/phase-5-scripts` (because
  `test_envelope_manifest.py` is a self-runner outside `tests/`).
- `tests/test_repo_layout.py`: ALLOWED_TOP_LEVEL loses `phase-0`,
  `phase-1`, `phase-2`, `phase-3`, `phase-3.1`, `phase-3.2`,
  `phase-3.3`, `phase-4`, `phase-4.5`, `phase-5`; gains `evidence`.
- `.gitignore`: keep the existing `phase-*/build-evidence/r-*/`
  pattern and add `evidence/*/build-evidence/r-*/` as the new
  scratch pattern (segment-preserving). Comment names the transition.
- `.github/workflows/adversarial-sprint-ci.yml`:
  - `:165` `framework/phase-3.2/evidence/local_backend.py` →
    `framework/tools/phase-3.2-evidence/local_backend.py`
  - `:169,191` `pilot/phase-1/locks/` stays as-is (pilot's locks,
    not framework's)
  - `:192` `framework/phase-3.2/reviews/review-prompt.md` →
    `framework/planning/phase-3.2/reviews/review-prompt.md`
  - `:245` prose citation of `phase-3.2/evidence/consumer.py` →
    `tools/phase-3.2-evidence/consumer.py`

### 2.4 Test fixture + code updates (NOT evidence bytes)

- `tests/test_sprint_loop.py:414`: expected path
  `/tmp/fw/phase-1/locks` → `/tmp/fw/tools/phase-1-locks`
- `tests/test_sprint_loop.py:419`: expected path
  `/tmp/fw/phase-4.5/build-evidence/r-001` →
  `/tmp/fw/evidence/phase-4.5/build-evidence/r-001` (segment-preserving)
- `tests/test_plan_lint.py` (~11 sites): string-literal fixtures
  `phase-4.5/tokens/chunk-5a.token.json` →
  `evidence/phase-4.5/tokens/chunk-5a.token.json` (test inputs,
  not evidence bytes).
- `tests/test_sprint_loop.py:701,731,1372,1398`:
  `"lock_file": "phase-1/locks/..."` →
  `"tools/phase-1-locks/..."`.
- `phase-3.2/evidence/local_backend.py:76,375` (now at
  `tools/phase-3.2-evidence/local_backend.py`): update the
  hardcoded `phase-1/scripts/verify-green.py` path to
  `tools/phase-1-scripts/verify-green.py` (code output, not
  evidence).

## 3. What the executor MUST do

1. `git mv` every tracked file per §2.1. Use `git mv` (not rm+add)
   so history follows.
2. Flip the constants in `config.py` and `paths.sh` per §2.2.
3. Fix the linters / config / CI per §2.3.
4. Update the test fixtures + code per §2.4.
5. Run the full suite and confirm 197 tests green.
6. Run `git log --follow` on one representative file per subtree
   to confirm history is preserved.
7. Commit with message `chunk-2: git mv phase dirs to taxonomy homes + flip constants + fix linters`.
8. Push to `origin/factory/layout-refactor`.

## 4. Verify (§11 exit checks)

### 4.1 Full suite green

`python3 -m pytest -q` → 197 tests, all green.

### 4.2 Layout allowlist refuses residual phase dirs

`tests/test_repo_layout.py` refuses if any `phase-N/` directory is
still tracked at top level. The allowlist has lost `phase-0`…
`phase-5` and gained `evidence`.

### 4.3 Constants resolve to new paths

`tests/test_layout_paths.py` (from Chunk 1) refuses if any constant
points to a nonexistent path. The flipped constants must resolve
to the new dirs.

### 4.4 plan-lint accepts the new prefixes

`tools/plan-lint.py` accepts `planning/layout-refactor/PLAN.md`
(regex fix is live; the PLAN cites `evidence/` and `planning/`
paths).

### 4.5 History preserved

`git log --follow <one-file-per-subtree>` shows the file's history
crossing the move boundary without a break.

## 5. What NOT to do (fences)

- **Do NOT edit evidence bytes.** `git mv` preserves bytes; no
  edits to committed envelopes, manifests, `MANIFEST.md`, raw/stream
  files.
- **Do NOT touch `main`.** All work on `factory/layout-refactor`.
- **Do NOT hold `EVIDENCE_SIGNING_KEY` or write tokens.** Referee
  signs.
- **Do NOT touch `~/work/adversarial-sprint-referee`, quantum-bank
  repos, `~/.factory`, or `referee-config.json`.**
- **Do NOT update living-doc citations.** That is Chunk 3's job.
  The `PATH-REDIRECTS.md` file is Chunk 3's surface.
- **Do NOT run the exit-check scripts.** That is Chunk 4's job.

## 6. Rule application

| Rule | Where |
|------|-------|
| §7 | §4 exit checks assert on reality (allowlist, constant resolution, git log --follow) |
| §11 | §4 exit checks are real pytest assertions |
| §13 | this spec states the problem + constraints; the executor chooses the order of `git mv` operations |
| §15 | `git log --follow` verifies history is preserved (§4.5) |
| §18.2 | one chunk, one commit |
| §18.3 | per-chunk verify block (§4) |
| §21 | evidence bytes untouched (git mv preserves bytes) |

## 7. Chunk-close protocol

Same as CHUNK-1-SPEC §8, with `chunk=chunk-D1-2`.
