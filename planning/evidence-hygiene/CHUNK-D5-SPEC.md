# CHUNK-D5-SPEC — tooling-process codification

**Parent dossier:** `planning/evidence-hygiene/`
**Predecessors:** `chunk-D4-1` (squash-merged into `main` via PR #7,
merge commit `fdfbbc2` on `origin/main`; the chunk's own commit is
`0663444` on `origin/factory/d4-final-cleanup`, retrievable via
`git show 0663444`). Chunk-D4-1 spec at
`planning/evidence-hygiene/CHUNK-D4-SPEC.md`; review verdict at
`evidence/reviews/chunk-d4-1-review/SUMMARY.md`
(retrievable at `git show 0663444:evidence/reviews/chunk-d4-1-review/SUMMARY.md`).

**Branch:** `factory/d5-tooling-docs`
**Chunk ID:** `chunk-D5-1` (initial) → `chunk-D5-1b` (this follow-on)
**Process:** audit-script-only per `planning/evidence-hygiene/PLAN.md §2`
(1 reviewer; default `kimi-k3` — operator may swap to `minimax-m3` at
execution time). No referee token. Same shape as chunk-D4-1 per its
review SUMMARY ("Per `planning/evidence-hygiene/PLAN.md §5`: lighter
one-reviewer gating"). Reviewer fires via `tools/run-review.sh` (this
chunk's surface §2.2); bundle layout per `tools/conventions/review-bundle.md`
(this chunk's surface §2.1).

**Revision history.** The wrapper's signature has evolved through
three landed increments; this spec captures the **current** state at
the chunk-D5-1b evolution. Earlier increments remain retrievable
via their commits:

- `chunk-D5-1` @ `5848a35` — initial 2-arg wrapper, cwd-output semantics.
- `chunk-D5-1a` @ `77a316c` — self-anchored via `${BASH_SOURCE[0]}`.
- `chunk-D5-1b` (this follow-on) — sprint-keyed, round-auto-derived,
  no cwd writes.

## 1. Problem statement (§13)

`chunk-D3-1` and `chunk-D4-1` write review bundles at
`evidence/reviews/chunk-d3-1-review/`
and `…/r-chunk-d4-1-review-20260815-1423/`. Both bundles share the
shape `round{N}/review-{model}-envelope.json` + `SUMMARY.md`. Their
SUMMARY.md files cite "per `planning/evidence-hygiene/PLAN.md §5`"
and "lighter one-reviewer gating" — but the cited PLAN.md **does
not yet exist** as a tracked file (verified at the spec-write step
via `git ls-tree HEAD planning/evidence-hygiene/` — only
`ARCHIVE-INDEX.md`, `CHUNK-D4-SPEC.md`, `PROMPT-D4-BUILDER.md` are
present). Four gaps prevent a future `factory/d-N-...` planner from
operating without re-deriving these conventions:

1. No convention doc for the `r-chunk-N-review-<ts>/` bundle shape —
   envelope key set, SUMMARY.md section order, 27-digit SHA convention.
2. No composing wrapper for "fire one reviewer, capture envelope +
   stderr-log" — operators currently hand-type the `droid exec`
   invocation + shell redirect on every chunk.
3. `tools/README.md` has no section telling a future planner *which
   script to invoke when* — `cross_family_review.py` vs
   `orchestrate-review.py` vs `run-with-model.sh` vs the new
   `run-review.sh`.
4. The dossier-level PLAN.md that chunk-D3-1 / chunk-D4-1 reviews
   inherited §5 language from is not on disk; the "lighter
   one-reviewer gating" rule is canonical precedent but no file
   asserts it.

This chunk finishes the codification: four surfaces, ≤100 new LOC
across the repo.

## 2. Surface touched

### 2.1 `tools/conventions/review-bundle.md` — NEW FILE (~55 LOC)

Canonical convention for `evidence/reviews/r-chunk-N-review-<ts>/`
directories. Plagiarism is fine — the **exemplars** cited here are
the canonical artifacts whose bytes this chunk's doc formalises:

- `evidence/reviews/chunk-d3-1-review/SUMMARY.md`
  — judgment-call precedent (2-round: REJECT → ACCEPT-WITH-NITS).
- `evidence/reviews/chunk-d4-1-review/SUMMARY.md`
  — audit-script-only precedent (single round, dual cross-family
  ACCEPT-WITH-NITS).

Must cover:

- **Directory layout** — `round{N}/review-{model}-envelope.json` +
  matching `review-{model}-stderr.log` + optional
  `verifier-prompt.md`; `SUMMARY.md` at the bundle root.
- **Envelope shape** — top-level keys verbatim from `droid exec
  --output-format json`: `result` (markdown body), `session_id` (droid
  UUID), `usage` (token accounting), `duration_ms`. The 27-character
  SHA prefix referenced by `tools/cross_family_review.py` =
  `hashlib.sha256(open(json_path,'rb').read()).hexdigest()[:27]`
  (consistent with the `PLACEHOLDER_LEADING_RUN_MIN` 50-char
  fingerprint used at full-length by the same gate).
- **SUMMARY.md section order** — header (commit under review, branch,
  parent reference) → round-by-round tables → findings (TAML-shaped)
  → verdict paragraph.
- **Model family taxonomy** — citation pinch pointing at
  `tools/sprint_loop/config.py:MODEL_FAMILY_MAP` so a future droid
  re-derives family from the canonical map, not from the doc.
- **Exemplars table** — both canonical paths with one-line "what
  this exemplar teaches".

### 2.2 `tools/run-review.sh` — NEW EXECUTABLE (~25 LOC code-only)

```
DROID_MODEL_ID=<modelId> bash tools/run-review.sh \
    <modelId> <prompt-file> <sprint-name>
```

Compositional wrapper around `tools/run-with-model.sh` that adds
the `review-<model>-envelope.json` + `review-<model>-stderr.log`
capture convention AND enforces a sprint-keyed canonical output
directory. Refuses:

- **exit 2** — missing/empty positional args (`$#` != 3, or
  any of `$1`/`$2`/`$3` empty).
- **exit 3** — sprint-keyed canonical dir cannot be created via
  `mkdir -p`.

`$DROID_MODEL_ID` is **not** re-checked at this layer — `run-with-model.sh`
owns that gate (§17.1 single source of truth). `--mission` refusal
during the inner invocation continues to come from
`run-with-model.sh` (exit 3 propagate).

**Output directory derivation (chunk-D5-1b):**

```
# Tool's actual derivation uses ${BASH_SOURCE[0]} via `dirname` —
# more robust across non-git checkouts than `git rev-parse` and
# avoids a git-binary dependency for the wrapper. Spec text
# mirrors the code's semantics (chunk-D5 kimi-k3 finding 4):
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
SPRINT_DIR="${REPO_ROOT}/evidence/reviews/${SPRINT}"
ROUND=1
for n in 1 2 3 4 5 6 7 8 9 10; do
  if [ ! -d "${SPRINT_DIR}/round${n}" ]; then ROUND="round${n}"; break; fi
done
mkdir -p "${SPRINT_DIR}/${ROUND}"
```

Side effects: writes `review-<model>-envelope.json` +
`review-<model>-stderr.log` under
`${REPO_ROOT}/evidence/reviews/${SPRINT_NAME}/round{N}/`. Never
the cwd (cwd-scattering was the **nonsense** the previous
semantics produced). The round number is auto-derived from the
existing `round{N}/` directories under the sprint — `round1/`
is the default for a fresh sprint; the second invocation
(if round1 was REJECT) automatically lands in `round2/`. The
loop scans up to `round10/` (REJECT-rate higher than that
suggests the spec itself is wrong, not the reviewers; it
becomes a STOP per §4 below). The latter (`stderr.log`) is
**empty on success** — a non-empty log is a defect signal
captured in the chunk's SUMMARY process notes.

### 2.3 `tools/README.md` — APPEND NEW SECTION (~25 LOC)

Insert before "## Closing note": `## When to use which review tool`.

Three paragraphs (matching the user's prompt):

1. **Composition primitives** — `run-with-model.sh` (refusal layer),
   `cross_family_review.py` (dual-ACCEPT cross-family gate),
   `orchestrate-review.py` (cross-family reviewer pipeline).
2. **Operator-facing wrappers** — `run-review.sh` (single-reviewer
   fire + envelope/stderr capture; this chunk).
3. **When to use which** — cross-family gate (spec-level) →
   `cross_family_review.py`; judgment-call (2 reviewers) →
   `cross_family_review.py`; audit-script-only (1 reviewer) →
   `run-review.sh`.

Each script: one line "what it does" + one line "when to use it".
Listing: `cross_family_review.py`, `orchestrate-review.py`,
`run-with-model.sh`, `run-review.sh`.

### 2.4 `planning/evidence-hygiene/PLAN.md` — NEW FILE (~30 LOC)

Closes the citation gap (§1). Two sections, no §3–§6 academic
scaffolding (chunk-D5 is one chunk, not a multi-chunk programme —
contrast D2's `planning/evidence-consolidation/PLAN.md`'s four
sections, which existed because D2 was multi-chunk in design):

- **§1 Source of truth for the process tiers** (3-4 lines) — names
  `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`,
  `tools/cross_family_review.py`, `tools/orchestrate-review.py`,
  `tools/run-with-model.sh` as the primitives; points at §2 for the
  tier selection itself.
- **§2 Review tier spectrum** — table verbatim from the user's
  prompt plus a sixth column `Precedent` listing the verifiable
  SHA. Column headers are exact, examples verbatim, plus a
  `Precedent` column appended. Tier inferences:

  | Tier             | Trigger                                                                                              | Reviewers                | Token    | Cost       | Precedent                                                                          |
  |------------------|------------------------------------------------------------------------------------------------------|--------------------------|----------|-----------|------------------------------------------------------------------------------------|
  | `audit-script-only` | Spec is "run these N scripts and report whether they pass"; no judgement calls                 | 1 (any family)           | none     | ~5-8 min  | `chunk-D4-1` @ `0663444` (single round, dual cross-family ACCEPT-WITH-NITS)         |
  | `judgment-call`    | Spec involves an exclusion-set decision, label, reframing, or any choice with two defensible answers | 2 (cross-family)         | optional | ~15 min   | `chunk-D3-1` @ `58c11d3` (round-2 fix; round-1 REJECT was at `685e379`)            |
  | `spec-level`       | Spec itself changes (dossier edit, sweep-rule, taxonomy change)                                  | full panel (≥2 families) | required | ~30 min   | `chunk-D1-*` / `chunk-D2-1` @ `42aa9ca` (referee tokens issued)                    |

  Cite via `git show <sha>` for any tier's example.

## 3. Exit criteria

The chunk is complete only when **all** hold, measured on disk and
in git:

1. `tools/conventions/review-bundle.md` exists, and §1 splits into
   "1.Historical (frozen)" — the existing `evidence/reviews/`
   paths including the two canonical exemplars — and "1.Current
   (sprint-keyed)" — the canonical
   `${REPO_ROOT}/evidence/reviews/<sprint-name>/round{N}/` shape
   for new chunks. §6 ("Exemplars") is unchanged and points at the
   historical paths as canonical-format references. Both legacy
   citations `r-chunk-d3-1-review-20260814-2152` and
   `r-chunk-d4-1-review-20260815-1423` remain ≥ 2 hits each
   (`grep -cE` ≥ 2) on the file.

2. `tools/run-review.sh` exists, executable bit set
   (`test -x tools/run-review.sh` returns 0), and the §2.2 (current
   shape) contract is satisfied:
   - 3 positional args required (`$#` == 3); refuses exit 2 on
     fewer args (`bash tools/run-review.sh` → exit 2),
     refuses exit 2 on any empty arg
     (`bash tools/run-review.sh "" foo bar` → exit 2,
     `bash tools/run-review.sh kimi-k3 "" foo` → exit 2,
     `bash tools/run-review.sh kimi-k3 /tmp/prompt ""` → exit 2),
     refuses exit 3 on `mkdir -p` failure of the canonical
     `evidence/reviews/<sprint-name>/round{N}/` directory.
   - The round-derive loop scans `round1..round10/` and lands in
     the lowest-numbered vacant dir.
   - `$DROID_MODEL_ID` is propagated to the inner invocation
     (`DROID_MODEL_ID="$MODEL" bash "$RUN_WITH_MODEL" …`) BUT NOT
     re-checked at the wrapper layer (single source of truth at
     `run-with-model.sh`).
   - **`cwd` writes are impossible:** every output path goes
     through `${SPRINT_DIR}/${ROUND}/`; no `${PWD}`-relative
     paths in the redirect clause. A reviewer fired with
     `./review-<model>-envelope.json` appearing in the cwd is
     a contract violation.

3. `tools/README.md` gained the §2.3 section. Every script under
   `tools/` that touches review process is listed
   (`cross_family_review.py`, `orchestrate-review.py`,
   `run-with-model.sh`, `run-review.sh`) with one-line "what it
   does" + one-line "when to use it" each.

4. `planning/evidence-hygiene/PLAN.md` exists, contains §2 with the
   3-tier table **verbatim** (§2's `Tier | Trigger | Reviewers |
   Token | Cost` column headers matching; `audit-script-only` /
   `judgment-call` / `spec-level` rows with the exact trigger
   sentences in the user's prompt), and uses `0663444` / `58c11d3` /
   `42aa9ca` as the precedent SHAs.

5. `python3 -m pytest -q` reports `241 passed, 3 skipped, 0 failed`
   (same baseline as chunk-D4-1 close — no test-tree additions).

6. `python3 tools/wiki-link-audit.py` returns no dead links
   (chunk-D4-1 baseline: zero).
   `python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5-SPEC.md`
   is green.

7. **Total non-blank LOC cap.** For chunk-D5-1b, the cap is on the
   two surfaces that changed shape:
   - `tools/conventions/review-bundle.md` ≤ 55 non-blank
     (excluding shell comments; markdown tables don't load-count).
   - `tools/run-review.sh` ≤ 30 code-only non-blank
     (excluding `#` comment lines).
   - If either file exceeds its hard ceiling, tighten the prose,
     not the contract.

One commit, subject line:

```
chunk-D5-1: codify review-bundle convention + run-review.sh wrapper
```

Branch `factory/d5-tooling-docs` is pushed to the `dev` remote only;
**no push or merge targets `main`** (operator merges after reviewer
ACCEPT-class verdict).

## 4. Forbidden

- Do not touch `tools/cross_family_review.py` or
  `tools/orchestrate-review.py`. These are the gate + pipeline;
  modification is a chunk-D-EVER (future spec-level chunk under its
  own review).
- Do not modify `tools/run-with-model.sh`'s refusal logic. The new
  wrapper composes around it; the gate stays where §17.1 placed it.
- Do not add a chunk close token, sign `chunk-D5-1.token.json`,
  hold `EVIDENCE_SIGNING_KEY`, or fire a two-family gate. This
  chunk is **audit-script-only** per `PLAN.md §2` row 1 — single
  reviewer, no token.
- Do not add tests under `tests/`. The floor checks are
  text-and-grep on disk state; the existing 241-test suite is the
  ceiling.
- Do not fix the trailing-newline nit flagged by chunk-D4-1's
  review (the `pre-move-sha256.json` EOF line). That is cosmetic
  and explicitly out of scope per the user's prompt.
- Do not push to `main`. One push to `dev` per chunk.
- **Do not move, rename, restructure, or modify committed
  evidence bytes under `evidence/reviews/...`.**
  chunk-D5-1b introduces a sprint-keyed canonical root
  (`evidence/reviews/<sprint>/round{N}/`) for **new** bundles; the
  existing historical artifacts under `phase-4.5/build-evidence/`
  (including the canonical exemplars cited in
  `tools/conventions/review-bundle.md §5`) are **frozen** at
  their current paths. Lifting the cleanup to flatten the
  existing `phase-4.5` tree out of `phase-4.5/` is queued as a
  separate roadmap item (chunk-D5a or chunk-D6) — explicitly out
  of scope here.
- Do not remove any untracked file, edit `evidence/`,
  `telemetry/runs.jsonl`, `evidence/LEDGER.md`, or any
  `evidence/phase-4.5/tokens/*` file.
- Do not exceed the ≤100 LOC four-surface cap (§3 item 7). If the
  draft would breach, tighten the doc-text, not the contract.

## 5. Review and close protocol

`tools/run-review.sh` (this chunk's surface) fires exactly once with
the default `kimi-k3` (moonshot / kimi-family). Operator may swap
to `minimax-m3` (minimax / minimax-family) at execution time
provided the family differs from the implementer's — for chunk-D5,
the implementer family is the droid session running this chunk's
executor (typically `claude-opus-5` per chunk-D4-1's review
SUMMARY; both `kimi-family` and `minimax-family` are disjoint).

Reviewer inspects §3's six checks against the disk state of the
build commit, returns ACCEPT-WITH-NITS or REJECT per
`tools/conventions/review-bundle.md` (this chunk) shape.
Per dossier §5 lighter-gating rule: operator reviews,
signs-or-skips, and merges. The build-evidence bundle lives at
`evidence/reviews/r-chunk-d5-1-review-<ts>/`
with `round1/review-kimi-k3-envelope.json` + `SUMMARY.md`. If
REJECT, executor re-fires at most once after bounded correction
(file-shape nitfix); after the second REJECT, BLOCKED.
