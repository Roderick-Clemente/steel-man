# PLAN — layout refactor D1 (v3)

Derived from `CLEANUP-PLAN.md` (machine-local operator brief) per
OPERATING-RULES §18. This document is the committed plan the D1
chunks fire against; the brief itself is gitignored and does not
travel. Reviewer verdict on this file gates the drafting of chunk
specs; chunk-spec verdict gates code; code verdict + signed token
gates the next chunk.

**Revision history.**
- v1 (`b1ef52e`): REJECT from both Tier-2 (grok-4.5, gemini-3.1;
  referee token `0ea80f0`). Findings: Chunk 1 inventory was a
  factual lie (claimed only `fire-design-review.sh` bypassed the
  constant; reality was ~17 sites); Chunk 4 `--dry-run` exit check
  structurally cannot catch broken script paths; `phase-1/locks/`
  and `phase-1/fixtures/` misclassified; `plan-lint.py` regex rejects
  new prefixes; §7 overclaim; success criterion byte-identity.
- v2 (`6ef1f28`): REJECT from kimi-k3 (session `3ab14956`, 56493
  tokens; referee pending). ACCEPT-WITH-NITS from minimax-m3
  (session `9bd35feb`, 14700 tokens). kimi-k3 found v2 still missed
  4 functional sites, Chunk 4 exit check structurally cannot exit 0,
  evidence-target layout contradictory, `phase-3.1/locks/` unmapped,
  prompt templates swept into evidence.
- v3 (this revision): folds in kimi-k3's REJECT findings: (a) Chunk 1
  inventory now includes `local_backend.py:76`, `backends.py:125`,
  `fire-design-review.sh:155`, CI `yml:192`; (b) Chunk 4 exit check
  replaced with direct real script invocations against a valid-RED
  fixture + path-existence test (no full-runner invocation); (c)
  evidence-target shape is segment-preserving
  (`evidence/phase-4.5/build-evidence/r-...`) — constant flip, test
  expectations, redirects example, gitignore all agree; (d)
  `phase-3.1/locks/` mapped to `tools/phase-3.1-locks/`; (e)
  `phase-3.2/reviews/review-prompt.md` classified as planning (not
  evidence); (f) `tools/sprint_loop/prompts/` on Chunk 3 allowlist;
  (g) Chunk 3 allowlist widened to all moved planning docs; (h) line
  numbers fixed (`config.py:157/162`), arithmetic corrected (198),
  vacuous/decorative rows dropped.

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
  **prefixes** change. **Leaf directory names are preserved under
  `evidence/phase-N/`** (e.g. `build-evidence/` stays as a segment,
  so `phase-4.5/build-evidence/r-001/` →
  `evidence/phase-4.5/build-evidence/r-001/`).

## 3. Existing primitives being composed (§18.1)

The plan is a flow chart of existing calls with thin orchestration
glue, not a fresh build. Named primitives:

| Primitive                                  | Role in D1                              |
|--------------------------------------------|-----------------------------------------|
| `tools/sprint_loop/config.py`              | home of the new path-root constants     |
| `tools/chunk_sequence_gate.py`             | already composes verify; caller passes token path |
| `tools/sign_chunk_token.py`                | canonical JSON + HMAC; caller passes token path |
| `tools/sprint_loop/per_chunk.py`           | 7 hardcoded `os.path.join` sites → route via constant |
| `tools/sprint_loop/backends.py`            | 1 hardcoded fallback `os.path.join` → route via constant |
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
   `phase-4.5/prompts/`, `phase-5/prompts/`, and
   `phase-3.2/reviews/review-prompt.md`) are planning-authored
   but code-consumed: they live in `planning/` and are referenced
   via the constant.

## 4. Target taxonomy — concrete leaf placement

GROK-style choice per the brief (prefer minimal citation churn).
**Rule: leaf directory names are preserved under
`evidence/phase-N/`** — the `build-evidence/`, `tokens/`,
`reviews/` segments stay as-is, only the `phase-N/` prefix moves
under `evidence/` or `planning/`.

- **`evidence/<phase>/`** — envelopes, manifests, run trees, tokens.
  - `evidence/phase-0/` ← `phase-0/evidence/`
  - `evidence/phase-1/` ← `phase-1/build-evidence/`
  - `evidence/phase-2/` ← `phase-2/build-evidence/`, `phase-2/reviews/` (envelope JSONs only; `review-prompt.md` if any is planning)
  - `evidence/phase-3/` ← `phase-3/build-evidence/`, `phase-3/reviews/` (envelope JSONs only)
  - `evidence/phase-3.1/` ← `phase-3.1/build-evidence/`
  - `evidence/phase-3.2/` ← `phase-3.2/build-evidence/`, `phase-3.2/reviews/` (envelope JSONs only — **`review-prompt.md` is planning, not evidence; it moves to `planning/phase-3.2/reviews/`**), `phase-3.2/evidence/` **schema JSONs only** (`bundle_schema_v1.json`, `security_allowlist.json`); the `.py` files under this dir are code and move to `tools/`
  - `evidence/phase-4/` ← `phase-4/*envelope.json`, `phase-4/h-ci/`, `phase-4/h3/` (the `demo/` dir contains only `.md` files — it is planning, not evidence)
  - `evidence/phase-4.5/` ← `phase-4.5/build-evidence/`, `phase-4.5/tokens/`
- **`planning/<phase>/`** — PRD-adjacent record: RUN-PROMPTs,
  PLANs, KNOWN-ISSUES, RESULTS, design docs, postmortems, READMEs,
  and **runtime prompt templates** (planning-authored, code-consumed
  via constant).
  - `planning/phase-0/` ← `phase-0/GO-NO-GO.md`, `phase-0/README.md`
  - `planning/phase-1/` ← `phase-1/KNOWN-ISSUES.md`, `phase-1/README.md`, `phase-1/RUN-LEDGER.md`, `phase-1/open-questions.md`, `phase-1/valid-red.md`, `phase-1/prompts/`
  - `planning/phase-2/` ← `phase-2/APPROVAL.md`, `phase-2/KNOWN-ISSUES.md`, `phase-2/README.md`, `phase-2/findings.md`, `phase-2/plan-v1.md`
  - `planning/phase-3/` ← `phase-3/KICKOFF.md`, `phase-3/KNOWN-ISSUES.md`, `phase-3/README.md`, `phase-3/RUN-COMMANDS.md`, `phase-3/prompts/`
  - `planning/phase-3.1/` ← `phase-3.1/RESULTS.md`, `phase-3.1/RUN-PROMPT.md`, `phase-3.1/SPIKE.md`, `phase-3.1/prompts/`
  - `planning/phase-3.2/` ← `phase-3.2/ASSUMPTIONS.md`, `phase-3.2/BUILD-NOTES.md`, `phase-3.2/EXPLORER-PROMPT.md`, `phase-3.2/RECOMMENDATION.md`, `phase-3.2/RUN-PROMPT.md`, `phase-3.2/SPIKE.md`, `phase-3.2/wiki-refresh-on-merge.md`, **`phase-3.2/reviews/review-prompt.md`** (prompt template, code-consumed via constant)
  - `planning/phase-3.3/` ← `phase-3.3/SPIKE.md`
  - `planning/phase-4/` ← `phase-4/track-*.md`, `phase-4/post-v3-*prompt.md`, `phase-4/track-execution-review-prompt.md`, **`phase-4/demo/*.md`** (demo scripts are planning, not evidence)
  - `planning/phase-4.5/` ← all `phase-4.5/*.md`, `phase-4.5/prompts/`, `phase-4.5/adversarial_review/` (panel-prompt + panel-findings markdown are planning; committed envelope JSONs under `build-evidence/` are evidence)
  - `planning/phase-5/` ← `phase-5/DESIGN-*.md`, `phase-5/POSTMORTEM-REFEREE-SEAT.md`, `phase-5/TASK-DESIGN-REVIEW-PHASE.md`, `phase-5/prompts/`
- **`tools/<namespace>/`** — code stranded in phase dirs. **Locks
  are runtime gate input (consumed by `per_chunk.py` and the hook),
  not planning artifacts — they go to the code side.**
  - `tools/phase-1-hooks/` ← `phase-1/hooks/`
  - `tools/phase-1-scripts/` ← `phase-1/scripts/`
  - `tools/phase-1-probes/` ← `phase-1/probes/`
  - `tools/phase-1-locks/` ← `phase-1/locks/` **(code side, not planning)**
  - `tools/phase-3.1-locks/` ← `phase-3.1/locks/` **(code side — v2 missed this; 3 committed lock manifests for `test_profile_model`/`route`/`seed.py`)**
  - `tools/phase-3-gen/` ← `phase-3/gen-telemetry.py`
  - `tools/phase-3.1-gen/` ← `phase-3.1/gen-telemetry.py`
  - `tools/phase-3.2-evidence/` ← `phase-3.2/evidence/*.py` (`local_backend.py`, `consumer.py`, `token_accounting.py`); the schema JSONs stay in `evidence/phase-3.2/`
  - `tools/phase-4-gen/` ← `phase-4/gen-findings.py`, `phase-4/reconstruct-telemetry.py`
  - `tools/phase-5-scripts/` ← `phase-5/scripts/` (incl. `test_envelope_manifest.py`, `envelope-manifest.py`, `fire-design-review.sh`)
- **`tests/fixtures/phase-1/`** ← `phase-1/fixtures/` **(test fixtures, not evidence)**. `phase-1/fixtures/invalid-red/` contains only `test_*.py` files for `valid-red.py` classification.

Rationale for choosing `tools/phase-N-<subdir>/` as the leaf naming:
minimum citation churn. Existing code cites `phase-1/scripts/lock.py`;
the redirect is `tools/phase-1-scripts/lock.py` — same path tail, one
prefix flip. A flat `tools/lock.py` would collide (three phases each
have their own `gen-telemetry.py`) and would erase historical
provenance a future reader needs.

## 5. Chunk plan (§18.2 — build in chunks, §18.3 — verify at each boundary)

Every chunk is one commit that (a) moves + fixes exactly the surface
its spec names, (b) leaves the full suite green, (c) is pushed to
`origin`, (d) posts a `REVIEW REQUEST:` line to `STEER.md` with
populated envelope paths (after the builder fires Tier-2 as
orchestrator per §24), and (e) waits for a `REVIEW COMPLETE:` line
+ `tools/chunk_sequence_gate.py --check-current-head` verify before
the next chunk opens.

### Chunk 1 — path-root constants + route ALL hardcoded sites

**Problem statement (§13 shape):** the runner and gate code hardcode
phase-dir prefixes in ~21 code sites (grounded grep below). Moving
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
| `tools/sprint_loop/per_chunk.py:279` | `os.path.join(framework_root, "phase-3.2", "evidence", "local_backend.py")` | `EVIDENCE_CODE_ROOT / "local_backend.py"` |
| `tools/sprint_loop/config.py:157` | `os.path.join(self.framework_root, "phase-1", "locks")` (`default_locks_dir`) | `LOCKS_ROOT` |
| `tools/sprint_loop/config.py:162` | `os.path.join(self.framework_root, "phase-4.5", "build-evidence", run_id)` (`default_evidence_dir`) | `EVIDENCE_ROOT / "phase-4.5" / "build-evidence" / run_id` (segment-preserving) |
| `tools/sprint_loop/backends.py:125` | `os.path.join(framework_root, "phase-4.5", "build-evidence", ...)` (fallback in `LocalBackend.validate`) | `EVIDENCE_ROOT / "phase-4.5" / "build-evidence" / ...` |
| `tools/orchestrate-review.py:78` | `os.path.join(args.framework_root, "phase-3.2", "evidence", "local_backend.py")` | `EVIDENCE_CODE_ROOT / "local_backend.py"` |
| `phase-3.2/evidence/local_backend.py:76` | `script = os.path.join(framework_root, "phase-1", "scripts", "verify-green.py")` (the FUNCTIONAL subprocess in `run_verify_green()`, not the cosmetic `:375` string) | `SCRIPTS_ROOT / "verify-green.py"` |
| `phase-3.2/evidence/local_backend.py:375` | `"verify_green": "phase-1/scripts/verify-green.py"` (path string in producer's runtime output JSON — code, not an evidence byte) | `SCRIPTS_ROOT / "verify-green.py"` |
| `tools/sprint_loop/chunk_close_banner.py:42,51,99` | banner text mentions `phase-4.5/tokens/` and `phase-4.5/build-evidence/` | `TOKENS_ROOT` / `EVIDENCE_ROOT` references |
| `tools/sprint-loop.py:1116,1118` | CLI help mentions `phase-4.5/build-evidence/` | `EVIDENCE_ROOT` reference |
| `tools/chunk_sequence_gate.py:9,119` | docstring + argparse help mention `phase-4.5/tokens/` | `TOKENS_ROOT` reference in prose |
| `tools/sign_chunk_token.py:6,135` | docstring mentions `phase-4.5/tokens/` | `TOKENS_ROOT` reference |
| `phase-5/scripts/fire-design-review.sh:87` | `RUN_DIR="phase-4.5/build-evidence/${RUN_ID}"` | compose via `paths.sh` shell mirror |
| `phase-5/scripts/fire-design-review.sh:155` | `python3 phase-5/scripts/envelope-manifest.py "$RUN_DIR"` (second hardcoded site in same file) | compose via `paths.sh` shell mirror |

**Surface touched (code only, zero moves):**

- `tools/sprint_loop/config.py`: add path-root constants
  `EVIDENCE_ROOT`, `PLANNING_ROOT`, `TOKENS_ROOT`, `PROMPTS_ROOT`,
  `SCRIPTS_ROOT`, `LOCKS_ROOT`, `EVIDENCE_CODE_ROOT` (for the
  `phase-3.2/evidence/*.py` code that moves to `tools/phase-3.2-evidence/`
  in Chunk 2), and helper `phase_path(framework_root, kind, *parts)` —
  kind ∈ {"evidence","planning","tokens","prompts","scripts","locks",
  "evidence-code"}. Constants take default values matching TODAY's
  layout so behaviour is unchanged.

  **Signature correction (supersedes this plan's earlier
  `phase_path(kind, phase, *parts)`).** There is no `phase=`
  parameter: the phase segment is already embedded in each constant
  (`TOKENS_ROOT` carries `phase-4.5`), so a `phase=` argument would
  double-count it. `framework_root` is a required leading positional
  because it lives on the `Config` dataclass, not at module level.
  CHUNK-1-SPEC §2.1 and the locked judge test
  (`tests/test_layout_paths.py::test_phase_path_helper_signature_and_composition`,
  which asserts the signature via `inspect.signature`) both govern.
- Route every site in the inventory table above through the helper.
  No behavioural drift — the constants resolve to today's paths.
- `phase-5/scripts/fire-design-review.sh`: introduce
  `tools/sprint_loop/paths.sh` (sourced) that exports the same
  constants as env vars, so the shell composes
  `RUN_DIR="${EVIDENCE_ROOT}/phase-4.5/build-evidence/${RUN_ID}"`
  and
  `ENVELOPE_MANIFEST="${TOOLS_ROOT}/phase-5-scripts/envelope-manifest.py"`
  without duplicating paths. (§18.4: fix the friction inline.)

**Verify (§11 exit check):**

- `python3 -m pytest -q` → all 194 tests still green.
- Add `tests/test_layout_paths.py` with three tests:
  1. every constant resolves to a currently-existing directory;
  2. the helper's output for `(kind="tokens", phase="phase-4.5")` +
     `chunk-5a.token.json` equals the actual on-disk path
     `phase-4.5/tokens/chunk-5a.token.json`;
  3. `per_chunk.py`'s 7 `os.path.join` sites, `backends.py:125`,
     `orchestrate-review.py:78`, and `local_backend.py:76` all
     resolve through the helper (a grep assertion: none of those
     lines still contain a literal `"phase-1"` or `"phase-3.2"` or
     `"phase-4.5"` string).
- Total suite grows from 194 → 197; the layout allowlist is untouched
  in this chunk.

### Chunk 2 — `git mv` the phase dir content to taxonomy homes + flip constants + fix linters

**Problem statement:** phase dir content is functionally three
different things (evidence, planning, code) stored in one silo. Move
each subtree to its taxonomy home, flip the Chunk-1 constants to the
new roots (segment-preserving), update the layout allowlist, update
`.gitignore`'s scratch pattern, update `pytest.ini`'s
`norecursedirs`, update `plan-lint.py`'s path-prefix regex, and
update the CI workflow's hardcoded paths.

**Surface touched:**

- `git mv` per the mapping in §4. All moves are `git mv` (not
  rm+add) so history follows. Evidence bytes are not edited.
- `tools/sprint_loop/config.py`: flip constants to:
  - `EVIDENCE_ROOT = "evidence"`
  - `PLANNING_ROOT = "planning"`
  - `TOKENS_ROOT = "evidence/phase-4.5/tokens"`
  - `PROMPTS_ROOT = "planning/phase-4.5/prompts"`
  - `SCRIPTS_ROOT = "tools/phase-1-scripts"`
  - `LOCKS_ROOT = "tools/phase-1-locks"`
  - `EVIDENCE_CODE_ROOT = "tools/phase-3.2-evidence"`
  - `default_evidence_dir` composes `EVIDENCE_ROOT / "phase-4.5" / "build-evidence" / run_id` (segment-preserving)
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
- `tests/test_sprint_loop.py:414`: update expected path from
  `/tmp/fw/phase-1/locks` → `/tmp/fw/tools/phase-1-locks`
- `tests/test_sprint_loop.py:419`: update expected path from
  `/tmp/fw/phase-4.5/build-evidence/r-001` →
  `/tmp/fw/evidence/phase-4.5/build-evidence/r-001` (segment-preserving)
- `tests/test_plan_lint.py` (~11 sites): update string-literal
  fixtures from `phase-4.5/tokens/chunk-5a.token.json` →
  `evidence/phase-4.5/tokens/chunk-5a.token.json` (test inputs, not
  evidence bytes).
- `tests/test_sprint_loop.py:701,731,1372,1398`: update
  `"lock_file": "phase-1/locks/..."` →
  `"tools/phase-1-locks/..."`.
- `phase-3.2/evidence/local_backend.py:76,375`: update the
  hardcoded `phase-1/scripts/verify-green.py` path to
  `tools/phase-1-scripts/verify-green.py` (code output, not evidence).

**Verify (§11):**

- `python3 -m pytest -q` → 197 tests green.
- `tests/test_repo_layout.py` refuses if any `phase-N/` directory
  is still tracked at top level.
- `tests/test_layout_paths.py` refuses if any constant points to a
  nonexistent path.
- `tools/plan-lint.py` accepts `planning/layout-refactor/PLAN.md`
  (regex fix is live).
- `git log --follow` on one representative file per subtree
  confirms history is preserved.

### Chunk 3 — living-doc citations + `planning/PATH-REDIRECTS.md`

**Problem statement:** ~150 md citations across PRD, OPERATING-RULES,
skills, wiki, and phase docs point at the old paths. Living docs
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
  `tools/REPRODUCE.md`
- `tools/sprint_loop/prompts/*.md` (runtime prompt templates that
  cite phase paths in their prose — v2 missed this)
- `droid-wiki/*.md` **— path tokens only**. Content freshness is D3,
  not D1.
- `planning/ROADMAP-REVIEW*.md`
- **All docs moved into `planning/<phase>/`** (READMEs, RUN-PROMPTs,
  KNOWN-ISSUES, RUN-LEDGER, design docs including
  `DESIGN-PERSISTENT-REFEREE.md`, postmortems, BUILD-NOTES, etc.) — v2's
  phrasing accidentally excluded non-README moved docs; v3 widens to
  all moved planning docs.

**Hard stop (capacity bound, per §17):** the verify step greps for
residual `phase-[0-9]` citations in the allowlisted living docs. If
residual hits are only historical narrative (e.g. "Phase 1 built
`phase-1/scripts/lock.py`" in a postmortem that documents the old
path deliberately), STOP — document them in
`planning/PATH-REDIRECTS.md` rather than rewriting. The bullet list
above is the file allowlist; if a file not on the list surfaces a
citation, it is NOT in scope for D1 (record as follow-on).

**Immutable — do NOT edit:** everything under `evidence/`,
including committed envelope JSONs, manifests, `MANIFEST.md`,
`raw`/`stream` outputs, and any file whose bytes are HMAC-signed
or SHA-quoted somewhere else.

**One rename, not a citation edit — `LEDGER.md` destination.** Chunk 2
landed the ledger at `planning/phase-4.5/LEDGER.md` as a side effect of
clearing the repo root. Wrong home: it is the sprint's general-purpose
record — SHA MAP, rulings, errata, and chunk closes spanning every phase —
not a phase-4.5 planning doc. It belongs at `evidence/LEDGER.md`,
unpartitioned at the evidence root for the same reason
`planning/ROADMAP-REVIEW.md` sits at the planning root: it spans phases.

- `git mv planning/phase-4.5/LEDGER.md evidence/LEDGER.md` — rename only,
  **zero content edits**. Append-only (§5) governs the bytes; a rename
  preserves them and `git log --follow` proves it.
- **Zero live editable citations.** A full audit
  (`grep -rn 'LEDGER\.md'`, excluding `tools/RUN-LEDGER.md`) finds exactly
  two, and neither may be edited:
  1. `evidence/phase-4.5/build-evidence/r-chunk1-builder-verify-20260814/BUILDER-HANDOFF-chunk-D1-2.md:225`
     — evidence, immutable per the block above.
  2. `tests/test_layout_paths.py:571` — a **comment**, not an assertion, so
     the rename breaks nothing; but the file is a judge locked at
     `cb00dfac` and MUST NOT be touched.
- Both are therefore redirects entries. (2) is the first case where the
  redirects file covers a stale citation inside **live code** rather than
  inside evidence, because the code is lock-frozen. Say that explicitly in
  `PATH-REDIRECTS.md` — a future reader who greps the tests and finds an
  old path needs to know it is intentional and where the file went.

**`planning/PATH-REDIRECTS.md` shape:**

- Table of old-prefix → new-prefix.
- **Matching algorithm (specified):**
  1. strip an optional absolute repo-root prefix
     (`/Users/factory/work/adversarial-sprint-dev/`) from the
     cited path;
  2. match the longest old-prefix in the table against the
     resulting relative path;
  3. apply only to path-shaped tokens (regex:
     `(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry|evidence|planning)/[\w/.-]+`);
  4. leave prose mentions ("Phase 1 built…") untouched.
- Example: `phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`
  → `evidence/phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`
  (segment-preserving).

**Verify (§11):**

- `python3 -m pytest -q` → 197 tests green.
- `grep -rn --include='*.md' 'phase-[0-9]' <allowlisted-living-docs>`
  returns only intentional historical-narrative citations, each
  accompanied by a same-line redirect note OR recorded in
  `planning/PATH-REDIRECTS.md` as a historical-narrative exception.
- `planning/PATH-REDIRECTS.md` covers every old-prefix that still
  appears in any evidence file.
- `evidence/LEDGER.md` exists, `planning/phase-4.5/LEDGER.md` does not,
  `git log --follow evidence/LEDGER.md` reaches the pre-rename history,
  and `git show --numstat HEAD -- evidence/LEDGER.md` reports the rename
  with **zero** added or deleted lines. A non-zero line count means the
  rename smuggled a content edit into an append-only file — treat as a
  failed chunk, not a nit.
- `tests/test_layout_paths.py` still hashes to `cb00dfac` and
  `tests/test_layout_paths_chunk2.py` to `48a579f8`, both matching their
  locks under `tools/phase-1-locks/tests/`.

### Chunk 4 — exit check: wiki-link-audit + full suite + REAL direct script invocations

**Problem statement:** the D1 exit criteria must be checked, not
assumed (§11). v2's "real (non-dry) fixture run" via
`python3 tools/sprint-loop.py ...` **structurally cannot exit 0**:
`sprint-loop.py`'s reconcile gate reads stdin → EOF → `SystemExit(1)`
before the chunk loop; `produce_evidence` raises `RuntimeError`
without `EVIDENCE_SIGNING_KEY`; `commit_chunk_change` would
`git checkout -b` off the branch mid-verify. v3 replaces the
full-runner invocation with **direct real invocations of the four
moved scripts against fixtures** + the path-existence test.

**Surface touched:**

- No new code moves. Chunk 4 is the exit gate.
- Chunk 4 lands a `tests/fixtures/phase-1/valid-red/test_valid_red.py`
  fixture if one does not already exist (a test that fails with a
  real `AssertionError` for a valid behavioral reason — NOT a syntax
  error or tautology, so `valid-red.py` classifies it as VALID, not
  rejected). This is the fixture the direct invocations use.

**Verify (§11 — checked, not assumed):**

1. `python3 tools/wiki-link-audit.py` → green (no dead links).
2. `python3 -m pytest -q` → 198 tests green (197 from chunks 1-3 +
   1 new path-existence test from chunk 4).
3. **Direct real script invocations** (the core exit check — proves
   the moved scripts work at their new paths, not dry-run):
   a. `python3 tools/phase-1-scripts/lock.py
      tests/fixtures/phase-1/valid-red/test_valid_red.py "test fails
      for valid reason"` → writes a lock manifest to
      `tools/phase-1-locks/test/test_valid_red.py.lock.json`; exit 0.
   b. `python3 tools/phase-1-scripts/valid-red.py --pilot-root .
      --test-file tests/fixtures/phase-1/valid-red/test_valid_red.py`
      → classifies the RED as VALID; exit 0.
   c. `python3 tools/phase-1-scripts/verify-green.py --pilot-root .
      --test-file tests/fixtures/phase-1/valid-red/test_valid_red.py`
      → recomputes the hash, runs the test, confirms it passes (the
      fixture must be fixable: it fails pre-fix, passes post-fix);
      exit 0 after a one-line fix, or exit non-zero with a clear
      hash-mismatch if the test was tampered with.
   d. `EVIDENCE_SIGNING_KEY=test-key python3
      tools/phase-3.2-evidence/local_backend.py --pilot-root .
      --test-file tests/fixtures/phase-1/valid-red/test_valid_red.py
      --framework-root . --lock-file
      tools/phase-1-locks/test/test_valid_red.py.lock.json
      --output /tmp/d1-exit-bundle.json` → produces a signed bundle
      at `/tmp/d1-exit-bundle.json`; exit 0.
   These four invocations prove the moved scripts resolve, execute,
   and produce their expected outputs. If any path is broken by the
   move, the invocation crashes with `FileNotFoundError` (python
   exit 2) or `RuntimeError` — the §7 reality-assertion the dry-run
   was structurally blind to.
4. **Path-existence test assertion:** `tests/test_layout_paths.py`
   gains a fourth test that asserts `per_chunk.py`'s constructed
   script paths (`SCRIPTS_ROOT / "lock.py"`, `SCRIPTS_ROOT /
   "valid-red.py"`, `SCRIPTS_ROOT / "verify-green.py"`,
   `EVIDENCE_CODE_ROOT / "local_backend.py"`) resolve to files that
   exist on disk. Belt-and-suspenders that does not depend on
   running the scripts.
5. Post-D1 `git log --stat` shows exactly N + 1 commits landed on
   `factory/layout-refactor` since branching from `main` (Chunk 1
   through Chunk 4 + this PLAN commit), each with a signed token
   in `evidence/phase-4.5/tokens/` whose HMAC verifies and whose
   `chunk_commit_sha` matches the chunk's HEAD.

## 6. Rule application table (§18 receipt)

| Rule           | Where it applies in D1                                                |
|----------------|-----------------------------------------------------------------------|
| §5 STOP        | any red suite after one bounded fix; any evidence-path ambiguity      |
| §7 assert      | verify via file listings, `git log --follow`, `pytest -q`, direct real script invocations, not exit codes or dry-run strings |
| §11 exit gate  | per-chunk verify block + chunk-4 exit checks (direct script invocations + path-existence test) |
| §13 executor   | this PLAN is problem+constraints; no sed lists                        |
| §14 shim       | `run-with-model.sh` + `adapters/factory.py` untouched; `paths.sh` mirrors the Python constant |
| §15 git truth  | `git log --follow` on representative moved files; chunk-4 log verify  |
| §17 envelope   | D1 is the entire capacity; D2/D3 gated; Chunk 3 has a hard stop |
| §18 compose    | §3 primitives table + chunk shape; grounded inventory table in Chunk 1 |
| §18.4 friction | banner + CLI help + `.gitignore` + `pytest.ini` + `plan-lint.py` regex + `paths.sh` shell mirror |
| §20 gate       | chunks land only after prior signed token verifies via `chunk_sequence_gate.py` |
| §21 evidence   | evidence bytes untouched; PATH-REDIRECTS.md carries the delta; test fixtures are NOT evidence bytes |
| §22 identity   | builder posts REVIEW REQUEST, fires Tier-2 as orchestrator (§24); never signs; referee audits and signs |
| §24 fire-XOR-sign | builder may fire as orchestrator; referee audits and signs only; never both at once |

## 7. Adversarial review plan (§18.5)

Cross-family panel via the referee, disjoint from the implementer.
Reviewers are operator-selected; the builder fires them as
orchestrator per §24 (no signing key held), captures raw stdout to
`phase-4.5/build-evidence/<run-id>/<artifact>/<model>.json`, posts
`VALIDATE COMPLETE:` markers, then posts `REVIEW REQUEST:` with
populated paths. Referee audits §21/§17.2/§23 and signs.

Three review points per §18.5 + operator direction:

1. **PLAN review** — this file, before any chunk code lands.
   (v1 REJECT at `0ea80f0`; v2 kimi-k3 REJECT + minimax-m3
   ACCEPT-WITH-NITS; v3 is this revision.)
2. **Chunk-spec review** — one committed `CHUNK-N-SPEC.md` per
   chunk before code lands.
3. **Chunk-close review** — landed code + green suite + push. Signed
   token gates the next chunk.

## 8. Distill hooks (§18.6 — after D1 lands)

- If path constants prove load-bearing, propose a `layout-constants`
  skill or §18-appendix on "moves land on path-constant first."
- If `PATH-REDIRECTS.md` catches stale citations audit tools miss,
  propose teaching `wiki-link-audit.py` a `--redirects` flag.
- If the plan-verdict / spec-verdict / code-verdict cadence works,
  propose a diagram in `skills/adversarial-sprint/SKILL.md`.
- If the dry-run-vs-real-run gap recurs, propose an §11-appendix:
  "dry-run is not a path-existence check; pair with direct
  invocations or a path-existence test."
- If the "inventory claim vs grounded grep" gap recurs, propose an
  §18-appendix: "a route inventory is a grep output, not a claim;
  the PLAN must paste the grep, not paraphrase its result."

## 9. Success criteria (§11 exit — checked, not assumed)

D1 closes successfully iff **all** hold:

1. Branch `factory/layout-refactor` has commits for PLAN, Chunk 1,
   Chunk 2, Chunk 3, Chunk 4 (5 landed commits minimum).

   **This is a minimum, not an enumeration.** Non-chunk commits are
   expected and do not fail this criterion: spec revisions driven by
   review findings, the planner's judge-test authoring commit (see
   criterion 4), and out-of-band ops commits such as the
   `.gitignore`/`LEDGER.md` transport fix. Any commit whose subject is
   not `chunk-D1-N: ...` is a non-chunk commit and is exempt from the
   per-chunk fences in the chunk specs; each must still be its own
   commit, outside any chunk's diff.
2. **No commits landed on `main` during the run**, verified via
   `git merge-base --is-ancestor <branch-point> main && git rev-list
   <branch-point>..main --count` returns 0.
3. Top-level `phase-0` … `phase-5` directories no longer exist;
   `evidence/` and `planning/<phase>/` do; `tools/phase-N-*/`
   subdirs exist for the moved code.
4. `python3 -m pytest -q` reports 198 tests, all green (194
   pre-existing + 3 from `tests/test_layout_paths.py` + 1 new from
   Chunk 4).

   **Attribution correction.** The 3 tests are Chunk 1's *judge*, but
   they land in a **planner** commit before `chunk-D1-1` opens, not in
   the Chunk 1 commit — per framework invariant #3 the executor of a
   chunk must not author the tests that grade it. The total is
   unchanged at 198. Between the planner's commit and Chunk 1's close
   the suite is a **valid RED at 3 failed / 194 passed**; that RED is
   the expected state, not a regression, and Chunk 1's exit is those
   3 flipping green with no others broken.
5. `tests/test_repo_layout.py` allowlist updated and passes.
6. `tools/wiki-link-audit.py` returns green.
7. `tools/plan-lint.py` accepts `planning/layout-refactor/PLAN.md`.
8. `planning/PATH-REDIRECTS.md` exists and covers every old-prefix
   still cited inside `evidence/`.
9. Each chunk has a `evidence/phase-4.5/tokens/chunk-D1-N.token.json`
   whose HMAC verifies and whose `chunk_commit_sha` matches the
   chunk's HEAD.
10. **Direct real script invocations** (Chunk 4 verify step 3) all
    exit 0 without `FileNotFoundError` on any moved script path.

If any bullet fails after one bounded fix attempt, the deliverable
STOPs, `BLOCKED:` is posted to `STEER.md`, and a BLOCKED-with-evidence
note is committed on the branch. An incomplete night with clean
tokens beats a complete night without.
