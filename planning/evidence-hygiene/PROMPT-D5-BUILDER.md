# Builder prompt: chunk-D5-1 (tooling-process codification)

You are the builder. Seat: builder. Repo:
`/Users/factory/work/adversarial-sprint-dev` (or your local clone of
`git@github.com:Roderick-Clemente/adversarial-sprint-dev.git`).

Branch from latest `main` (chunk-D4-1 squash-merged into `main` via
PR #7 — merge commit `fdfbbc2` on `origin/main`; the chunk's own
commit `0663444` is retrievable on `origin/factory/d4-final-cleanup`
via `git show 0663444`):
`factory/d5-tooling-docs`. Read first:
`planning/evidence-hygiene/CHUNK-D5-SPEC.md`. That spec is your
authority.

## What you're doing

Four doc/tool surfaces — a thin wrapper script and three new/modified
docs. TOTAL ≤100 new lines across the four surfaces (CHUNK-D5-SPEC
§3 item 7 is the structural ceiling). No `tests/` additions; no
`evidence/`, `tokens/`, or `LEDGER.md` edits; no scope expansion.
Verifies purely by text-and-grep against disk state.

1. **`tools/conventions/review-bundle.md`** — new canonical convention
   doc, ~55 LOC, citing both `r-chunk-d3-1-review-20260814-2152/` and
   `r-chunk-d4-1-review-20260815-1423/` as exemplars.
2. **`tools/run-review.sh`** — new executable, ~15 LOC, refuses exit 2
   on missing/empty args; composes the `droid exec` invocation
   through `tools/run-with-model.sh` and writes
   `review-<model>-envelope.json` + `review-<model>-stderr.log`.
3. **`tools/README.md`** — append `## When to use which review tool`
   section, ~25 LOC.
4. **`planning/evidence-hygiene/PLAN.md`** — new file, ~30 LOC,
   closing the citation gap chunk-D3-1 / chunk-D4-1 reviews inherited.
   `§2` carries the 3-tier review spectrum verbatim.

## Why this is one chunk

The four surfaces are a single process codification commit. Splitting
them risks regressions: `tools/run-review.sh` references
`review-bundle.md`'s conventions; `tools/README.md` lists
`tools/run-review.sh`. One bundle, one review, one commit, ~8 minutes.
Per `planning/evidence-hygiene/PLAN.md §2` row 1: audit-script-only
tier — single reviewer, no referee token, no panel.

## Steps

### 1. Verify the surface state

```
test -f planning/evidence-hygiene/CHUNK-D5-SPEC.md || { echo "spec missing"; exit 1; }
test -f planning/evidence-hygiene/PROMPT-D5-BUILDER.md && echo "this file ok"
test -f tools/conventions/review-bundle.md && echo "WARN: review-bundle.md exists pre-chunk — STOP" || echo "review-bundle.md absent (correct)"
test -x tools/run-review.sh && echo "WARN: run-review.sh exists pre-chunk — STOP" || echo "run-review.sh absent (correct)"
test -f planning/evidence-hygiene/PLAN.md && echo "WARN: PLAN.md exists pre-chunk — STOP" || echo "PLAN.md absent (correct)"
git rev-parse --abbrev-ref HEAD  # expected: factory/d5-tooling-docs (after step 2)
```

If any WARN fires, STOP — the chunk's surface is already claimed by
a prior commit. Investigate via `git log -p -- tools/conventions/`
before proceeding.

### 2. Branch from main

```
git fetch origin
git checkout -b factory/d5-tooling-docs origin/main
```

If conflicts with the current branch's working tree, `git status`
should show only `CHUNK-D5-SPEC.md` + `PROMPT-D5-BUILDER.md`
(new files, no merge required). Verify with
`git diff --stat $(git merge-base HEAD origin/main)..HEAD` — expect
zero non-spec/prose files.

### 3. Write `tools/conventions/review-bundle.md`

```
cat > tools/conventions/review-bundle.md <<'BUNDLE_EOF'
# tools/conventions/review-bundle.md

Canonical bundle shape for `evidence/reviews/r-chunk-N-review-<ts>/`
directories. Future chunks' verdicts and a future `wiki-link-audit`
reader expect this layout. The two canonical **exemplars** cited
below are the artefacts this document formalises; plagiarism of
the layout shape is fine.

## 1. Directory layout

```
<ts-prefix>/                          (12-digit YYYYMMDD-HHMM ASCII sort key)
├── round1/
│   ├── review-<model>-envelope.json  (droid exec --output-format json)
│   ├── review-<model>-stderr.log      (empty on success — defect signal otherwise)
│   └── verifier-prompt.md             (the reviewer's brief)
├── round2/...                         (only if round1 was REJECT)
└── SUMMARY.md                         (chunk-level verdict; always present)
```

## 2. Envelope shape — `round{N}/review-<model>-envelope.json`

Top-level keys verbatim from `droid exec --output-format json`:

| Key           | Type   | Notes                                                                  |
|---------------|--------|------------------------------------------------------------------------|
| `result`      | string | Reviewer's markdown report body (findings + verdict + evidence).       |
| `session_id`  | string | Droid UUID; stable across re-fires.                                    |
| `usage`       | object | `input_tokens`, `output_tokens`, `cache_read_input_tokens`, …         |
| `duration_ms` | int    | Wall-clock ms for the run.                                             |

The 27-character SHA prefix referenced by `tools/cross_family_review.py`
equals `hashlib.sha256(open(json_path,'rb').read()).hexdigest()[:27]`.
The same gate's full 64-char SHA appears in the chunk-close token
(`evidence/phase-4.5/tokens/<chunk>.token.json`); the first 50 chars
form a `PLACEHOLDER_LEADING_RUN_MIN` fingerprint to refuse fixture-marker
hashes (`cross_family_review.py` KN-A-5).

## 3. SUMMARY.md section order

Section order matches the canonical exemplars:

1. Header — the chunk's commit under review (`git show <sha>` +
   parent), branch, dossier reference (`planning/evidence-hygiene/PLAN.md §2`).
2. Round-by-round tables — per round: `Validator | Family | Verdict | Envelope SHA-256`.
3. Findings — TAML bullets with `severity` / `category` / `section` /
   `claim` / `evidence` / `recommended_change`.
4. Final verdict paragraph — `ACCEPT-WITH-NITS` / `REJECT` with a one-line
   process note if a round was invalidated and re-fired.

## 4. Stderr/log convention

`droid exec`'s **stderr** routes to `review-<model>-stderr.log`
next to the envelope. **On success the log is empty.** A non-empty
log is a defect signal — capture in SUMMARY process notes.

## 5. Exemplars

| Path                                                                       | What this exemplar teaches                                                                    |
|----------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `…/build-evidence/r-chunk-d3-1-review-20260814-2152/SUMMARY.md`           | judgment-call precedent: 2-round review, REJECT → ACCEPT-WITH-NITS, per-round SHAs in table.   |
| `…/build-evidence/r-chunk-d4-1-review-20260815-1423/SUMMARY.md`           | audit-script-only precedent: single round, dual cross-family ACCEPT-WITH-NITS; nits quieted.  |

A future `factory/d-N-...` chunk's verifier follows §1–§3 verbatim,
asserts the empty-on-success stderr (§4), and references the
exemplars in §5 for format precedence when conventions evolve.
BUNDLE_EOF
```

Sanity-check the written content:

```
wc -l tools/conventions/review-bundle.md  # expect ≤65
grep -cE 'r-chunk-d3-1-review-20260814-2152|r-chunk-d4-1-review-20260815-1423' tools/conventions/review-bundle.md
# expect ≥ 2 (≥ 2 floor per CHUNK-D5-SPEC §3 item 1; measured count varies)
```

### 4. Write `tools/run-review.sh`

Sprint-keyed output (chunk-D5-1b). The wrapper takes a third
positional `<sprint-name>`, derives the canonical output directory
from `${REPO_ROOT}/evidence/reviews/<sprint-name>/round{N}/`, and
auto-increments `N` from existing `round{N}/` dirs under the sprint
so REJECT retries land parallel to round1 rather than overwriting.

```
cat > tools/run-review.sh <<'WRAPPER_EOF'
#!/usr/bin/env bash
# tools/run-review.sh — fire one reviewer; steer envelope + stderr
# to a sprint-keyed canonical directory (NOT cwd, NOT phase-4.5).
#
# Composing wrapper around tools/run-with-model.sh. Refuses:
#   exit 2 — missing or empty positional args
#   exit 3 — sprint-keyed canonical dir cannot be created (mkdir -p fail)
#
# Self-anchored via ${BASH_SOURCE[0]} (chunk-D5-1a) so callers can
# run this script from any cwd.
#
# Usage: DROID_MODEL_ID=<modelId> bash tools/run-review.sh \
#        <modelId> <prompt-file> <sprint-name>
# Writes: ${REPO}/evidence/reviews/<sprint-name>/round{N}/\
#         review-<modelId>-envelope.json + review-<modelId>-stderr.log
# Exit:   0 on success; 2 on bad args; 3 on mkdir failure.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_WITH_MODEL="${SCRIPT_DIR}/run-with-model.sh"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [ "$#" -ne 3 ] || [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "run-review.sh: expected 3 non-empty args (<modelId> <prompt-file> <sprint-name>)" >&2
  exit 2
fi
MODEL="$1"; PROMPT="$2"; SPRINT="$3"
SPRINT_DIR="${REPO_ROOT}/evidence/reviews/${SPRINT}"
ROUND=1
for n in 1 2 3 4 5 6 7 8 9 10; do
  if [ ! -d "${SPRINT_DIR}/round${n}" ]; then ROUND="round${n}"; break; fi
done
mkdir -p "${SPRINT_DIR}/${ROUND}" || {
  echo "run-review.sh: could not mkdir '${SPRINT_DIR}/${ROUND}'" >&2
  exit 3
}
DROID_MODEL_ID="$MODEL" bash "$RUN_WITH_MODEL" \
  droid exec --model "$MODEL" -f "$PROMPT" --auto medium --cwd "$PWD" --output-format json \
    > "${SPRINT_DIR}/${ROUND}/review-${MODEL}-envelope.json" \
    2> "${SPRINT_DIR}/${ROUND}/review-${MODEL}-stderr.log"
WRAPPER_EOF
chmod +x tools/run-review.sh
```

Sanity-check (all must exit per spec §3 item 2):

```
test -x tools/run-review.sh && echo OK-exec
wc -l tools/run-review.sh  # expect ~40-50 raw; code-only non-blank ≤ 30
bash tools/run-review.sh                                # → exit 2
bash tools/run-review.sh "" foo bar                     # → exit 2
bash tools/run-review.sh kimi-k3 "" foo                 # → exit 2
bash tools/run-review.sh kimi-k3 /tmp/somefile ""       # → exit 2
# Confirm cwd writes are impossible:
mkdir -p /tmp/d5-cwd-check && cd /tmp/d5-cwd-check
bash /Users/factory/work/adversarial-sprint-dev/tools/run-review.sh kimi-k3 /tmp/somefile chunk-D5-1b-test
ls /tmp/d5-cwd-check 2>&1  # expect empty (no review-*.json created in cwd)
ls /Users/factory/work/adversarial-sprint-dev/evidence/reviews/chunk-D5-1b-test/round1/ 2>&1 \
  | head -5  # expect review-kimi-k3-envelope.json + review-kimi-k3-stderr.log
rm -rf /tmp/d5-cwd-check
```

### 5. Append `## When to use which review tool` to `tools/README.md`

Read the current `## Closing note` line in `tools/README.md` (line 269
per `Read tools/README.md` at spec-write time). Insert the new
section immediately *before* it — i.e., the new section becomes the
penultimate `##` heading.

```
cat > /tmp/d5-readme-section.md <<'README_EOF'

## When to use which review tool

This repo has four review-firing surfaces. Pick the right one for the chunk you're planning.

**Composition primitives.** `tools/run-with-model.sh` is the refusal layer — every `droid exec` invocation routes through it ($DROID_MODEL_ID must be set; `--mission` is gated). `tools/cross_family_review.py` is the dual-ACCEPT cross-family gate; it consumes envelope SHAs and verdicts and refuses at parse. `tools/orchestrate-review.py` is the cross-family reviewer pipeline that fires N reviewers across N families and aggregates their verdicts into a chunk-close token (`tools/sign_chunk_token.py` is the HMAC signer it composes).

**Operator-facing wrappers.** `tools/run-review.sh` is a thin composing wrapper around `run-with-model.sh` that adds the `review-<model>-envelope.json` + `review-<model>-stderr.log` capture convention. Use it for ad-hoc single-reviewer fires (e.g., chunk-D5's audit-script-only single reviewer).

**When to use which.** Spec-level chunks (taxonomy edits, dossier changes) → `tools/cross_family_review.py` + `tools/orchestrate-review.py` (full panel). Judgment-call chunks → `cross_family_review.py` (2 reviewers cross-family). Audit-script-only chunks (text-and-grep verification only) → `tools/run-review.sh` (1 reviewer, no token). Per-script detail in `tools/conventions/review-bundle.md`.
README_EOF

# Splice before "## Closing note":
python3 - <<'PY'
src = open("tools/README.md").read()
SECTION = open("/tmp/d5-readme-section.md").read()
ANCHOR = "## Closing note"
assert ANCHOR in src, "README.md anchor missing — operator STOP"
assert "## When to use which review tool" not in src, "section already present"
out = src.replace(ANCHOR, SECTION.strip() + "\n\n" + ANCHOR)
open("tools/README.md", "w").write(out)
print("splice ok")
PY
```

Sanity-check:

```
grep -cE '^## When to use which review tool|^## Closing note' tools/README.md  # expect 2
grep -nE 'cross_family_review\.py|orchestrate-review\.py|run-with-model\.sh|run-review\.sh' tools/README.md \
  | grep -E 'When to use which review tool' -A 50 | wc -l   # expect ≥ 4 distinct script mentions
```

### 6. Write `planning/evidence-hygiene/PLAN.md`

```
cat > planning/evidence-hygiene/PLAN.md <<'PLAN_EOF'
# planning/evidence-hygiene/PLAN.md

Process codification lineage for chunks in `planning/evidence-hygiene/`.
chunk-D3-1 and chunk-D4-1 review verdicts cite "per
`planning/evidence-hygiene/PLAN.md §5`" — but §5 did not yet
exist as a tracked file when those chunks landed. chunk-D5
authors this PLAN to close the citation gap. Two sections; D5
is one chunk, not a multi-chunk programme.

## 1. Source of truth for the process tiers

`tools/sprint_loop/config.py:MODEL_FAMILY_MAP` is the canonical
model-family taxonomy. `tools/cross_family_review.py` enforces
the gate. `tools/orchestrate-review.py` is the cross-family
reviewer pipeline. `tools/run-with-model.sh` is the
per-invocation refusal layer. Reviewer-firing **tier selection**
(the choice of how many reviewers to fire and how strict) is
defined in §2.

## 2. Review tier spectrum

| Tier               | Trigger                                                                                              | Reviewers                | Token    | Cost       | Precedent                                                                          |
|--------------------|------------------------------------------------------------------------------------------------------|--------------------------|----------|------------|------------------------------------------------------------------------------------|
| `audit-script-only`| Spec is "run these N scripts and report whether they pass"; no judgement calls                     | 1 (any family)           | none     | ~5-8 min   | `chunk-D4-1` @ `0663444` (single round, dual cross-family ACCEPT-WITH-NITS)         |
| `judgment-call`    | Spec involves an exclusion-set decision, label, reframing, or any choice with two defensible answers | 2 (cross-family)         | optional | ~15 min    | `chunk-D3-1` @ `58c11d3` (round-2 fix; round-1 REJECT was at `685e379`)            |
| `spec-level`       | Spec itself changes (dossier edit, sweep-rule, taxonomy change)                                     | full panel (≥2 families) | required | ~30 min    | `chunk-D1-*` / `chunk-D2-1` @ `42aa9ca` (referee tokens issued)                    |

Verify any tier's example via `git show <sha>`. §2 is the
load-bearing content for `planning/evidence-hygiene/` chunks
going forward.
PLAN_EOF
```

Sanity-check:

```
wc -l planning/evidence-hygiene/PLAN.md  # expect ≤40
grep -nE 'audit-script-only|judgment-call|spec-level' planning/evidence-hygiene/PLAN.md  # expect ≥ 4 (table 3 + body)
grep -nE '0663444|58c11d3|42aa9ca' planning/evidence-hygiene/PLAN.md  # expect 3
```

### 7. Run §3 floor checks

Each must exit 0:

```
# 4 surfaces ≤100 LOC total (spec §3 item 7)
python3 - <<'PY'
import re
files = ["tools/conventions/review-bundle.md", "tools/README.md", "tools/run-review.sh", "planning/evidence-hygiene/PLAN.md"]
loc = 0
for f in files:
    text = open(f).read()
    # Count non-blank, non-comment-for-markdown lines
    if f.endswith(".sh"):
        n = len([l for l in text.splitlines() if l.strip() and not l.strip().startswith("#")])
    else:
        n = len([l for l in text.splitlines() if l.strip()])
    print(f"{f}: {n}")
    # For README the count is the *delta*, but a precise measurement is grep-based:
    loc += n
print(f"TOTAL non-blank LOC: {loc}")
assert loc <= 100, f"BUDGET BREACH: {loc} > 100 across {len(files)} files"
print("LOC CAP OK")
PY

# §3 item 1: review-bundle.md cites both exemplars
grep -cE 'r-chunk-d3-1-review-20260814-2152' tools/conventions/review-bundle.md  # expect ≥ 2
grep -cE 'r-chunk-d4-1-review-20260815-1423' tools/conventions/review-bundle.md  # expect ≥ 2

# §3 item 2: run-review.sh chmod + refusal
test -x tools/run-review.sh                                                         # expect 0
bash tools/run-review.sh                                                            # expect exit 2
bash tools/run-review.sh "" tools/conventions/review-bundle.md                      # expect exit 2
bash tools/run-review.sh kimi-k3 /tmp/nonexistent-prompt                            # expect non-zero (run-with-model.sh)

# §3 item 3: README section lists all 4 scripts
grep -E '^## When to use which review tool$|^- `\w|^\*\*' tools/README.md | grep -A 100 'When to use which' | \
  grep -cE 'cross_family_review\.py|orchestrate-review\.py|run-with-model\.sh|run-review\.sh'   # expect ≥ 4

# §3 item 4: PLAN.md §2 3-tier table verbatim
grep -E 'audit-script-only|judgment-call|spec-level' planning/evidence-hygiene/PLAN.md | wc -l   # expect ≥ 4
grep -E '0663444|58c11d3|42aa9ca' planning/evidence-hygiene/PLAN.md | wc -l                       # expect 3

# §3 item 5/6: pytest + wiki-link-audit + plan-lint
# Capture pytest stdout to a file first; `| tail` drops the
# `passed/failed` summary line (silent-green shape — chunk-D5
# kimi-k3 finding 5). Grep the file:
python3 -m pytest -q > /tmp/pytest.out 2>&1 && grep -E 'passed|failed' /tmp/pytest.out
python3 tools/wiki-link-audit.py                 # expect clean
python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5-SPEC.md   # expect PASS
```

If any check fails, STOP per spec §3.

### 8. Build-evidence bundle

```
mkdir -p evidence/reviews/r-chunk-d5-1-builder-$(date +%Y%m%d-%H%M)
BUNDLE="evidence/reviews/r-chunk-d5-1-builder-$(date +%Y%m%d-%H%M)"
cp planning/evidence-hygiene/CHUNK-D5-SPEC.md      "$BUNDLE/CHUNK-D5-SPEC.md"
cp planning/evidence-hygiene/PROMPT-D5-BUILDER.md  "$BUNDLE/PROMPT-D5-BUILDER.md"
python3 -m pytest -q                              > "$BUNDLE/pytest.txt"                  2>&1
python3 tools/wiki-link-audit.py                  > "$BUNDLE/wiki-link-audit.txt"          2>&1
python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5-SPEC.md > "$BUNDLE/plan-lint.txt" 2>&1
git diff --stat origin/main..HEAD                 > "$BUNDLE/diff-numstat.txt"             2>&1
git diff origin/main..HEAD                        > "$BUNDLE/diff-full.txt"               2>&1
python3 - <<'PY' > "$BUNDLE/loc-cap.txt"
import re
files = ["tools/conventions/review-bundle.md", "tools/README.md", "tools/run-review.sh", "planning/evidence-hygiene/PLAN.md"]
loc = 0
for f in files:
    text = open(f).read()
    if f.endswith(".sh"):
        n = len([l for l in text.splitlines() if l.strip() and not l.strip().startswith("#")])
    else:
        n = len([l for l in text.splitlines() if l.strip()])
    print(f"{f}: {n} non-blank LOC")
    loc += n
print(f"TOTAL: {loc} (cap 100, status: {'OK' if loc <= 100 else 'BREACH'})")
PY
```

The bundle must exist BEFORE commit (verifier inspects it).

### 9. Fire the verifier (single reviewer via `tools/run-review.sh`)

```
SPRINT="r-chunk-d5-1-review-$(date +%Y%m%d-%H%M)"
# The wrapper auto-creates evidence/reviews/$SPRINT/round{N}/ ; no mkdir needed.

# Write a verifier prompt that asks for the §3 checks + the LOC cap.
cat > "/tmp/d5-verifier-prompt.md" <<'VR_EOF'
# Chunk-D5-1 audit-script-only verifier prompt

You are validating chunk-D5-1. Author spec at
`planning/evidence-hygiene/CHUNK-D5-SPEC.md`; builder prompt at
`planning/evidence-hygiene/PROMPT-D5-BUILDER.md`. Build bundle under
`evidence/reviews/<sprint>/round1/` (sprint-keyed canonical root).
You are firing via `tools/run-review.sh` (this chunk's surface §2.2);
cross-family distinctness is preserved because your model family must
not collide with the implementer's family (`OPERATING-RULES §17.2`).

Re-derive every §3 floor check from disk state. Capture every
command + exit code; cite file:line. Use exactly the envelope shape
in `tools/conventions/review-bundle.md §2` for your output: a single
markdown `result` body with sections Header / Round-by-round /
Findings (TAML) / Verdict. The trailing `VERDICT:` line is the only
field the operator parses.

Do NOT hand-paraphrase counts or paths. If a count or path disagrees,
STOP and report.
VR_EOF

# Fire via the chunk's own wrapper. The 3rd arg <sprint-name> is the
# canonical bucket; the wrapper auto-derives round1/ under it.
bash tools/run-review.sh kimi-k3 /tmp/d5-verifier-prompt.md "$SPRINT"
# Wrapper wrote envelope + stderr-log directly into
# evidence/reviews/<sprint>/round1/ — no `mv` needed.
```

If envelope `/stderr.log` is non-empty, capture it inline in SUMMARY
process notes per `tools/conventions/review-bundle.md §4`. The
canonical REVIEW paths are now
`evidence/reviews/<sprint-name>/round1/review-<model>-envelope.json`
+ `…/review-<model>-stderr.log` + `…/SUMMARY.md` — the legacy
`phase-4.5/build-evidence/` paths are kept ONLY for the historical
exemplars cited in `tools/conventions/review-bundle.md §5`.

### 10. Write `SUMMARY.md` for the bundle

```
cat > "$REV_DIR/SUMMARY.md" <<SUM_EOF
# chunk-D5-1 review — audit-script-only (single reviewer)

Commit: <fill in from `git rev-parse HEAD`> chunk-D5-1: codify review-bundle convention + run-review.sh wrapper
Branch: factory/d5-tooling-docs
Predecessor: chunk-D4-1 @ main 0663444 (audit-script-only precedent)

Per `planning/evidence-hygiene/PLAN.md §2` row 1, this chunk fires 1
reviewer. Default model `kimi-k3` (moonshot / kimi-family).

## Round 1 — single reviewer

| Validator   | Family        | Verdict              | Envelope SHA-256              |
|-------------|---------------|----------------------|-------------------------------|
| kimi-k3     | moonshot / kimi-family | <fill in>      | <fill in: 64-char hex>        |

<Re-derive each of the §3 six checks; record PASS / FAIL with one
line of evidence per check.>

## Findings

<TAML-keyed bullets per `tools/conventions/review-bundle.md §3`.>

## Verdict

<ACCEPT-WITH-NITS or REJECT>
SUM_EOF
```

### 11. Commit

```
git add tools/conventions/review-bundle.md tools/run-review.sh tools/README.md planning/evidence-hygiene/PLAN.md
git status   # confirm only those 4 + the 2 spec/prose files + the bundle (which gitignores via local rule)
git commit -m "chunk-D5-1: codify review-bundle convention + run-review.sh wrapper

* tools/conventions/review-bundle.md — canonical convention for
  evidence/reviews/r-chunk-N-review-<ts>/ bundles.
  Direct citations of r-chunk-d3-1-review-20260814-2152 and
  r-chunk-d4-1-review-20260815-1423 as exemplars.

* tools/run-review.sh — single-reviewer fire-and-capture wrapper
  (~15 LOC). Refuses exit 2 on missing/empty positional args;
  composes through tools/run-with-model.sh (which retains the
  \$DROID_MODEL_ID gate). Writes review-<model>-envelope.json +
  review-<model>-stderr.log into cwd per tools/conventions/review-bundle.md §4.

* tools/README.md — new '## When to use which review tool' section
  mapping cross_family_review.py / orchestrate-review.py /
  run-with-model.sh / run-review.sh to spec-level / judgment-call /
  audit-script-only tiers.

* planning/evidence-hygiene/PLAN.md — new dossier-level PLAN
  (closes the §5 citation gap chunk-D3-1 and chunk-D4-1 inherited).
  §2 carries the 3-tier review spectrum verbatim with SHA-anchored
  precedents (0663444 / 58c11d3 / 42aa9ca).

* Total non-blank LOC across four surfaces — see
  evidence/reviews/r-chunk-d5-1-builder-$TS/loc-cap.txt.

Model: <your-modelId> (providerLock: <provider>, apiProviderLock: <provider>)
Role: executor

Telemetry-row: telemetry/runs.jsonl:r-executor-chunk-d5-1

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>"
```

Push to `dev` remote ONLY per AGENTS.md + spec §3.

```
git push -u origin factory/d5-tooling-docs
```

## Hard fences (do not cross)

- Do not edit `tools/cross_family_review.py`, `tools/orchestrate-review.py`,
  or `tools/run-with-model.sh`. Modification of any of these is a
  chunk-D-EVER (future spec-level chunk).
- Do not add a chunk close token, sign `chunk-D5-1.token.json`, hold
  `EVIDENCE_SIGNING_KEY`, or fire a 2+ reviewer panel. §2 row 1 of
  `planning/evidence-hygiene/PLAN.md` is the contract.
- Do not add tests under `tests/`. The 241-test ceiling is invariant.
- Do not push to `main`. One push to `dev` per chunk; operator merges
  after reviewer ACCEPT-class verdict.
- Do not exceed 100 non-blank LOC across the four surfaces. If a draft
  would breach, tighten doc-text or split into chunk-D5-1 + chunk-D5-2
  (operator decides; executor does not silently resize).
- Do not fix the trailing-newline nit on
  `evidence/reviews/d2-1-builder/pre-move-sha256.json`
  flagged in chunk-D4-1's review. That is cosmetic + out of scope.
- Do not remove untracked files. `r-f10/` residue remains.
