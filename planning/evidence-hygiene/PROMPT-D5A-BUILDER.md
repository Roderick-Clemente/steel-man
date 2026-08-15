# Builder prompt — chunk-D5A (phase-4.5 evidence migration + 5-nit sweep)

You are the builder. Seat: builder. Repo:
`/Users/factory/work/adversarial-sprint-dev`. Branch from latest
`main` (`331a7f8` is the predecessor commit landed via PR #8 for
chunk-D5-1b). Read first: `planning/evidence-hygiene/CHUNK-D5A-SPEC.md`
(this chunk's spec is your authority). Also read:

1. `tools/conventions/review-bundle.md` (full file).
2. `tools/run-review.sh` (the 22-LOC chip you are inheriting).
3. `tools/README.md` §"When to use which review tool".
4. `planning/evidence-hygiene/PLAN.md` — the three-review-tier
   roof.
5. `planning/PATH-REDIRECTS.md` — critical for the §5 hard-stop
   on `planning/layout-refactor/**` and `planning/phase-N/**`.
6. `evidence/reviews/r-chunk-D5-1b-review-r3-20260815-1421/SUMMARY.md`
   (kimi-k3 review bundle; the 5 nits you are applying in Track B).

This is an **audit-script-only** tier chunk per
`planning/evidence-hygiene/PLAN.md §2` row 1; 1 reviewer (default
`kimi-k3`); no referee token.

## Steps

### 1. Branch

```
git fetch origin
git checkout -b factory/d5a-sweep-and-migrate origin/main
```

Expect clean checkout. Verify `git ls-files --error-unmatch
CHUNK-D5A-SPEC.md`, `PROMPT-D5A-BUILDER.md` returns
non-zero (these are NEW).

### 2. Track A.0 — Enumerate bundled dirs

```
git ls-files evidence/phase-4.5/build-evidence/ | awk -F/ '{print $4}' | sort -u > /tmp/d5a-bundle-tops.txt
```

Top-level + nested `archive/` sub-shape. Compute the sprint-name per
the operator-prompt A.1 routine:

```sh
while read -r bundle; do
  sprint=$(printf '%s' "$bundle" \
    | sed -E 's/^r-//' \
    | sed -E 's/-[0-9]{8}-[0-9]{4,6}$//' \
    | sed -E 's/-[0-9]{8}$//')
  echo "$bundle -> $sprint"
done < /tmp/d5a-bundle-tops.txt
```

Sanity-check the output against the §2.1 mapping table in the spec.
The 6 `archive/r-phase45-*` bundles all reduce to `phase45`:
hand-disambiguate by appending `-v2`/`-v3`/…/`-v6` in enumeration
order. Document in SUMMARY as a discretionary decision (§19 ship-
recommendation rule).

### 3. Track A.2 — Mass-move via `git mv`

For each `(bundle, sprint)` pair, run `git mv`:

```sh
while read -r bundle; do
  [ "$bundle" = "legacy-duplicates" ] && continue
  [ "$bundle" = "archive" ] && continue     # handle archive subdir separately below
  # ... continue with mapping ...
done < /tmp/d5a-bundle-tops.txt
```

For `archive/`, descend one level and `git mv` every nested
sprint. Cross-cutting exception: do NOT move
`evidence/phase-4.5/build-evidence/legacy-duplicates/`.

Top-level orphan singletons: `git mv` to `evidence/reviews/_orphans/`:

```
mkdir -p evidence/reviews/_orphans
git mv evidence/phase-4.5/build-evidence/review-gemini-envelope.json  evidence/reviews/_orphans/review-gemini-envelope.json
git mv evidence/phase-4.5/build-evidence/rung3-droid-exec-output.json evidence/reviews/_orphans/rung3-droid-exec-output.json
```

### 4. Track A.3 — Citation search-replace

For each `.md` file in the spec §2.2 in-scope list, perform:

```python
# Pseudocode — implement with explicit string replace.
for citation in citations_to_replace:
    # citation = ("evidence/phase-4.5/build-evidence/<bundle>", "evidence/reviews/<sprint>")
    if file_contains(file, citation[0]):
        replace(file, citation[0], citation[1])
```

After every rewrite, sanity-check `git grep -lF "<replaced string>" -- file`
returns zero on the in-scope file.

### 5. Track A.5 — Residue removal

```sh
rm -rf evidence/reviews/chunk-d5-1b-kimi-cwd-verify/ \
       evidence/reviews/chunk-d5-1b-kimi-round-derive/ \
       evidence/reviews/chunk-d5-1b-verifier-round10/ \
       evidence/reviews/r-chunk-D5-1b-review-20260815-1142/
```

Do NOT remove `evidence/reviews/chunk-d5-1b-verifier-cwd-check/`
(same family-pattern but not in the operator-authorized list);
surface as a nit.

### 6. Track B — 5 nits

For each nit (ops-paste prompt Track-B table), perform the single-
file edit. Verify each with Grep for the corrected token.

### 7. Floor checks

```sh
# Captures that don't lose the summary line via tail-pipe
python3 -m pytest -q > /tmp/pytest.out 2>&1 && grep -E 'passed|failed' /tmp/pytest.out
# expect: 241 passed, 3 skipped

python3 tools/wiki-link-audit.py
# expect: clean

python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5A-SPEC.md
# expect: PASS
```

Reject cases (refusals):

```sh
bash tools/run-review.sh                                              # exit 2
bash tools/run-review.sh "" foo bar                                   # exit 2
bash tools/run-review.sh kimi-k3 "" bar                               # exit 2
bash tools/run-review.sh kimi-k3 /tmp/some-prompt ""                  # exit 2
```

Round10-exhaustion guard (N3 fix verification):

```sh
SPRINT="round-exhaust-test"
SPRINT_DIR="evidence/reviews/${SPRINT}"
mkdir -p "${SPRINT_DIR}"/round{1..10}
# Now the wrapper's guard must catch this and exit 3.
bash tools/run-review.sh kimi-k3 /tmp/dummy "${SPRINT}"
# expect: exit 3 with stderr "ERROR: round-N exhaustion (spec defect)"
rm -rf "${SPRINT_DIR}"
```

Round-derive allocates lowest vacant:

```sh
SPRINT="chunk-d5a-derive-test"
SPRINT_DIR="evidence/reviews/${SPRINT}"
mkdir -p "${SPRINT_DIR}/round1"
# Expect next invocation lands in round2/ (no fire; just mkdir inspection).
# After firing, expect "${SPRINT_DIR}/round2/" to exist for the envelope.
rm -rf "${SPRINT_DIR}"
```

LOC ceiling:

```sh
# review-bundle.md non-blank ≤ 55
# run-review.sh non-blank code-only ≤ 30
awk 'NF && !/^#/' tools/conventions/review-bundle.md | wc -l   # ≤ 55
awk 'NF && !/^#/' tools/run-review.sh | wc -l                  # ≤ 30
```

### 8. Bundle artifacts (verifier)

```
BUNDLE="evidence/reviews/chunk-D5A-sweep-and-migrate"
mkdir -p "$BUNDLE/round1"
cat > "$BUNDLE/round1/verifier-prompt.md" <<'VR_EOF'
# chunk-D5A audit-script-only verifier prompt
[ short spec extract — see SUMMARY.md ]
VR_EOF

cat > "$BUNDLE/SUMMARY.md" <<'SUM_EOF'
# chunk-D5A review — audit-script-only
[ header / round table / process notes / discretionary-decisions / nits / verdict ]
SUM_EOF
```

### 9. Commit topology (3 commits)

1. **Planner commit** — `CHUNK-D5A-SPEC.md` + `PROMPT-D5A-BUILDER.md`.
   Subject: `chunk-D5A: scaffold sweep-and-migrate spec + builder prompt`.
2. **Migration commit** — `git mv` (bundles + orphans), residue rm,
   citation edits. Subject: `chunk-D5A: migrate phase-4.5 evidence to
   canonical sprint-keyed path + bucket orphan singletons`.
3. **Nit sweep commit** — N1..N5 edits.
   Subject: `chunk-D5A: 5-nit sweep on chunk-D5-1b spec/convention/wrapper`.

Cross-family guard preserved at the reviewer gate (fire via
`tools/run-review.sh` with `kimi-k3` — moonshot / kimi-family —
disjoint from the implementing family).

### 10. Push

```
git push -u origin factory/d5a-sweep-and-migrate
```

## Hard fences (do not cross)

- Do not modify `cross_family_review.py`, `orchestrate-review.py`,
  `run-with-model.sh`, `sign_chunk_token.py`, `plan-lint.py`,
  `wiki-link-audit.py`. Frozen per `OPERATING-RULES §17` /
  chunk-D5 §4.
- Do not sign `chunk-D5A.token.json` or hold
  `EVIDENCE_SIGNING_KEY`. Audit-script-only tier per `PLAN.md §2`.
- Do not add tests under `tests/`. 241/3 ceiling is invariant.
- Do not push to `main`.
- Do not delete any untracked file except the 4 listed above.
- Do not edit `planning/layout-refactor/**`, `planning/phase-N/**`,
  `evidence/LEDGER.md`, or `droid-wiki/by-the-numbers.md` /
  `lore.md` (PATH-REDIRECTS §5 + operator-prompt A.3).
- Do not move `evidence/phase-4.5/build-evidence/legacy-duplicates/`
  (chunk-D1 fenced).
- Per `OPERATING-RULES §19`, ship the discretionary decisions: archive
  retention at `evidence/reviews/archive/`, phase45 chronological
  disambiguation via `-v2/-v6` suffixes, orphan singletons to
  `evidence/reviews/_orphans/`. Surface WHYs in SUMMARY.
