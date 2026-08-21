# chunk-D5A — phase-4.5 evidence migration + 5-nit sweep (operator-paste prompt)

You are running **chunk-D5A** on `adversarial-sprint-dev`. PR #8 just landed chunk-D5-1b at commit `331a7f8`. Behind you: `a6e1e5d → 5848a35 → 77a316c → 4422ff0 → 07a8c6c → 331a7f8`.

This is an **audit-script-only tier** chunk (one kimi-k3 reviewer; per `planning/evidence-hygiene/PLAN.md §2` row 1). Operator flagged this as "quick"; verdict path is `ACCEPT-WITH-NITS` is acceptable per chunk-D4-1 precedent.

## Why one chunk, two tracks

Two mini-changes share a single branch + reviewer:

- **Track A — phase-4.5 evidence migration.** Move every artifact under `evidence/phase-4.5/build-evidence/<bundle>/round{N}/...` to the chunk-D5-1b canonical path `evidence/reviews/<sprint-name>/round{N}/...`.
- **Track B — 5-nit sweep on chunk-D5-1b.** Apply the 5 nits caught by kimi-k3 in chunk-D5-1b (full review bundle at `evidence/reviews/r-chunk-D5-1b-review-r3-20260815-1421/SUMMARY.md`).

The wiki-link update is **explicitly out of scope** for chunk-D5A (next chunk, after this lands).

## Reachable context

You will read, in this order:

1. `tools/conventions/review-bundle.md` (full file) — the codification you are inheriting.
2. `tools/run-review.sh` (the 22-LOC chip you are inheriting).
3. `tools/README.md` §"When to use which review tool" (one section).
4. `planning/evidence-hygiene/PLAN.md` — the three-review-tier roof.
5. `planning/evidence-hygiene/CHUNK-D5-SPEC.md` + `PROMPT-D5-BUILDER.md` — the chunk-D5 author's spec/builder. **You are downstream of these two; treat them as authoritative for plumbing.**
6. `planning/PATH-REDIRECTS.md` — read in full. Critically: it explicitly forbids editing rewrites in `planning/layout-refactor/**` (move-spec documents) and `planning/phase-N/**` (time-stamped run records). **Your search-replace MUST exclude these paths.** Committed evidence under `evidence/` is immutable per §5/§21 except where you are moving it.
7. `evidence/phase-4.5/build-evidence/` tree (read enumeration in next section).

If you reach a rehydration cliff at >150k tokens, re-read `tools/OPERATING-RULES.md` per the skill's loop-closing rule.

## Track A — phase-4.5 evidence migration

### A.0 — Enumerate (do not mass-move blind)

```
git ls-files evidence/phase-4.5/build-evidence/ | awk -F/ '{print $4}' | sort -u > /tmp/d5a-bundle-tops.txt
```

The current enumeration (as of `331a7f8`) shows three sub-shapes:

| Sub-shape | Example | Notes |
|---|---|---|
| top-level bundles | `r-chunk1-code-20260814-0020/`, `r-chunk-d3-1-review-20260814-2152/` | Direct under `evidence/phase-4.5/build-evidence/` |
| `archive/` subdir | `archive/r-chunk1-builder-verify-20260814/`, `archive/r-drs-role-split-2/` | Nested inside `build-evidence/archive/` |
| `legacy-duplicates/` | n/a | **Move NOT required.** Leave at origin path. |

There are also some stray files directly under `build-evidence/` (e.g. `review-convention-gemini.json`, `review-grok.json`). Inspect whether they are paired with sibling files; if a `review-<model>.json` has no sibling, treat it as belonging to the most-recent bundle context.

### A.1 — Compute sprint-name per bundle

The mapping rule:

- Strip an optional `r-` prefix.
- Strip one trailing `-\d{8}-\d{4,6}` (date + time).
- Else strip one trailing `-\d{8}` (date).
- Preserve internal `r3` / `v5` etc. (those are versioned designators, not dates).

Routine:

```sh
while read -r bundle; do
  sprint=$(printf '%s' "$bundle" \
    | sed -E 's/^r-//' \
    | sed -E 's/-[0-9]{8}-[0-9]{4,6}$//' \
    | sed -E 's/-[0-9]{8}$//')
  echo "$bundle -> $sprint"
done < /tmp/d5a-bundle-tops.txt
```

Sanity-check the output before mass-moving. Examples this should produce:

- `r-chunk1-code-20260814-0020` → `chunk1-code`
- `r-chunk1-spec-v5-20260813-2340` → `chunk1-spec-v5`
- `r-chunk-d3-1-review-20260814-2152` → `chunk-d3-1-review`
- `archive/r-chunk1-builder-verify-20260814` → `archive/chunk1-builder-verify` (the `archive/` depth is preserved)
- `archive/r-drs-role-split-2` → `archive/drs-role-split-2`

For `archive/`, the migration moves `evidence/phase-4.5/build-evidence/archive/<bundle>` → `evidence/reviews/archive/<sprint>`. (Yes, having a top-level `archive/` under `evidence/reviews/` after migration is acceptable; this preserves the archived-vs-active distinction. If you'd rather, sub-divide into `evidence/reviews/qbk-archive/` — your call, document the choice.)

### A.2 — Mass-move via `git mv`

For each `(bundle, sprint)` pair from A.1:

```sh
git mv "evidence/phase-4.5/build-evidence/$bundle" "evidence/reviews/$sprint"
```

Cross-cutting exception: do NOT touch `evidence/phase-4.5/build-evidence/legacy-duplicates/` (fenced as intentionally-kept per the chunk-D1 deliverables). Leave it in place.

### A.3 — Search-replace citations in `.md` files only

```sh
git grep -lE 'evidence/phase-4.5/build-evidence/' -- '*.md' ':!**/layout-refactor/**' ':!**/phase-*/**' > /tmp/d5a-citation-files.txt
```

The exclusions preserve `planning/layout-refactor/**` and `planning/phase-[0-9]*/**` per PATH-REDIRECTS.md hard-stop (§5).

For each file: open, replace `evidence/phase-4.5/build-evidence/<bundle>` with `evidence/reviews/<sprint>` where the mapping is known, OR with `evidence/reviews/` (prefix-only, no sprint) where the bundle wasn't in your enumeration. Save.

Cite the count in your commit body.

### A.4 — Audit floors (Track A specific)

```sh
python3 -m pytest -q                                # expect 241 passed, 3 skipped
python3 tools/wiki-link-audit.py                    # expect clean (audit now reads canonical paths)
python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5A-SPEC.md  # expect PASS

git ls-files | grep -E '^evidence/phase-4\.5/build-evidence/' \
  | grep -v -E '^(README|legacy-duplicates)/' \
  | head                                              # expect empty
```

A non-empty result means a `git mv` was missed. STOP, recover.

### A.5 — Untracked-residue cleanup

The chunk-D5-1b-verifier residue still on disk (operator-flagged in `evidence/reviews/r-chunk-D5-1b-review-r3-20260815-1421/SUMMARY.md`):

```
evidence/reviews/chunk-d5-1b-kimi-cwd-verify/
evidence/reviews/chunk-d5-1b-kimi-round-derive/
evidence/reviews/chunk-d5-1b-verifier-round10/
evidence/reviews/r-chunk-D5-1b-review-20260815-1142/
```

Plus the `evidence/phase-4.5/build-evidence/r-chunk-d5-1-builder-20260815-1032/` and `r-chunk-d5-1-review-20260815-1032/` (fenced in the operator summary note).

Confirm `git status --short` returns no references to these, then:

```sh
rm -rf evidence/reviews/chunk-d5-1b-kimi-cwd-verify/ \
       evidence/reviews/chunk-d5-1b-kimi-round-derive/ \
       evidence/reviews/chunk-d5-1b-verifier-round10/ \
       evidence/reviews/r-chunk-D5-1b-review-20260815-1142/
```

## Track B — 5-nit sweep on chunk-D5-1b

Each nit has a **single-file** edit unless the addendum says otherwise. Order is unimportant; commits can group nits that touch the same file.

| # | Nit text (verbatim from kimi-k3) | File | Edit |
|---|---|---|---|
| 1 | spec §3 item 1 says "§5 (Exemplars)"; Exemplars is at §6 | `planning/evidence-hygiene/CHUNK-D5-SPEC.md` | Replace "§5 (Exemplars)" with "§6 (Exemplars)" |
| 2 | commit body claims "4 citations"; actual is 2 per artifact | `planning/evidence-hygiene/PROMPT-D5-BUILDER.md` + `tools/conventions/review-bundle.md` | Replace any "appears 4 times each" with "appears ≥ 2 times each (≥ 2 floor)"; floor claim stays verbatim |
| 3 | round10-exhaustion latent (loop never reassigns `ROUND`) | `tools/run-review.sh` | Add guard **before** the round-derive loop: `if [[ -d "$SPRINT_DIR/round1" ... "$SPRINT_DIR/round10" ]]; then echo "ERROR: round-N exhaustion (spec defect)"; exit 3; fi`. ~6 LOC. |
| 4 | spec §2.2 says `git rev-parse --show-toplevel`; code uses `dirname "$SCRIPT_DIR"` | `planning/evidence-hygiene/CHUNK-D5-SPEC.md` §2.2 | Update spec text to: `REPO_ROOT="$(cd "$(dirname "$0")"/.. && pwd)"` (matches the code's actual semantics); add a one-line note "More robust across non-git checkouts" |
| 5 | pytest stdout pipe drops final-count | `planning/evidence-hygiene/PROMPT-D5-BUILDER.md` step 5 | Replace `python3 -m pytest -q \| tail` with `python3 -m pytest -q > /tmp/pytest.out 2>&1 && grep -E 'passed\|failed' /tmp/pytest.out` |

Verify each edit with `Grep` for the corrected token. LOC check after N3 fix: `tools/run-review.sh` non-blank ≤ 30.

## Branching

```
git fetch origin
git checkout -b factory/d5a-sweep-and-migrate origin/main
```

Then work on that branch.

## Commit topology

Three commits on `factory/d5a-sweep-and-migrate`:

1. **Planner commit** — `planning/evidence-hygiene/CHUNK-D5A-SPEC.md` + `planning/evidence-hygiene/PROMPT-D5A-BUILDER.md` (NEW).
   Subject: `chunk-D5A: scaffold sweep-and-migrate spec + builder prompt`.
2. **Executor commit — migration** — `git mv` of `evidence/phase-4.5/build-evidence/<bundle>` → `evidence/reviews/<sprint>`; citation search-replace edits; residue rm.
   Subject: `chunk-D5A: migrate evidence/phase-4.5 artifacts to canonical sprint-keyed path`.
3. **Executor commit — nits** — the N1..N5 edits.
   Subject: `chunk-D5A: 5-nit sweep on chunk-D5-1b spec/convention/wrapper`.

If you choose to fold migration+nits into one executor commit, that's permissible (mirror chunk-D5-1b's `07a8c6c` precedent); the planner commit stays.

Use `claude-opus-5` (anthropic) as model declaration in commit footers (cross-family guard preserved at the reviewer gate).

## Floor checks (re-verify before reviewer fires)

- ✓ `python3 -m pytest -q` → 241 passed / 3 skipped.
- ✓ `python3 tools/wiki-link-audit.py` → clean.
- ✓ `python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5A-SPEC.md` → PASS.
- ✓ `test -x tools/run-review.sh` → exit 0.
- ✓ Refusal cases (4× empty-arg) all return exit 2.
- ✓ `mkdir -p` failure case returns exit 3.
- ✓ Round-derive allocates lowest-vacant `round1..roundN`.
- ✓ **N3 fix verified:** round10-exhaustion guard returns exit 3 (testable via seeded `sprint/round{1..10}/`).
- ✓ `tools/conventions/review-bundle.md` non-blank ≤ 55.
- ✓ `tools/run-review.sh` non-blank ≤ 30.
- ✓ `git ls-files evidence/phase-4.5/build-evidence/ | grep -v 'legacy-duplicates\|^README'` returns nothing.

## Reviewer (audit-script-only)

Sprint name for the wrapper's 3rd arg: `chunk-D5A-sweep-and-migrate` (semantic key matches branch name; round-derive picks `round1` vacantly).

```
bash tools/run-review.sh kimi-k3 planning/evidence-hygiene/PROMPT-D5A-BUILDER.md chunk-D5A-sweep-and-migrate
```

If `--auto medium` returns permission-error (as in chunk-D5-1b's first fire), bypass the wrapper and invoke the inner directly:

```
bash tools/run-with-model.sh --auto high kimi-k3 planning/evidence-hygiene/PROMPT-D5A-BUILDER.md
```

Expected verdict: ACCEPT-WITH-NITS (with a small handful of nits only). Per chunk-D4-1 precedent, ACCEPT-WITH-NITS nits are roadmap material, not blocking.

## Surface artifacts

After reviewer returns:

1. Copy the verifier-prompt.md to the bundle.
2. Write `SUMMARY.md` per `tools/conventions/review-bundle.md §3` — verdict table + floor-check column + nits table (TAML).
3. Push the branch:

```
git push -u origin factory/d5a-sweep-and-migrate
```

4. Hand-off to operator: surface verdict + nits + main-PR-status (operator merges to main via PR).

## Out of scope — explicit fence

This chunk does NOT do:

- **Wiki update.** Operator's penciled-in next chunk, after D5A lands. The wiki pages need to readjust to the post-D5A data tree; the chunk's design must wait.
- **Pilot chunk** (qbank-ai-discovery via plugin). The third queued rung, after wiki update.
- **`chunk-D5-2` or any follow-on beyond the 5-nits.** nits that surface will be the next chunk's job.
- **`evidence/phase-4.5/build-evidence/legacy-duplicates/` migration.** Fenced as data-state preserved per chunk-D1 deliverables.
- **Rewrites in `planning/layout-refactor/**` or `planning/phase-[0-9]*/**`.** Forbidden per PATH-REDIRECTS.md §5.

## Operator ack points

End-of-session surfaces to operator:

1. Verdict + envelope SHA (first-27 hex + full).
2. Floor-check summary (10-line table or a single PASS/FAIL card).
3. Nits table (verbatim from reviewer).
4. Bundle location: `evidence/reviews/chunk-D5A-sweep-and-migrate/round1/{envelope.json,stderr.log,verifier-prompt.md}` + `../SUMMARY.md`.
5. Branch PR-ready: `https://github.com/Roderick-Clemente/adversarial-sprint-dev/pull/new/factory/d5a-sweep-and-migrate`.

End operator-prompt.
