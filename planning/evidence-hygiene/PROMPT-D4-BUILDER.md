# Builder prompt: chunk-D4-1 (final cleanup before wiki pass)

You are the builder. Seat: builder. Repo:
`/Users/factory/work/adversarial-sprint-dev` (or your local clone of
`git@github.com:Roderick-Clemente/adversarial-sprint-dev.git`).

Branch from latest `main` (chunk-D3-1 is merged — merge commit `5bef37a`):
`factory/d4-final-cleanup`.

Read first: `planning/evidence-hygiene/CHUNK-D4-SPEC.md`. That spec
is your authority — there is no separate `CHUNK-D4-1-SPEC.md` gate
(see CHUNK-D4-SPEC §5 and dossier §5: process is lighter than D1/D2,
one reviewer, no referee token — same shape as chunk-D3-1's).

## What you're doing

Two mechanical, fenced relocations:

1. **Pilot research** — `pilots/ai-discovery/` (4 files, 24 KB) →
   `planning/pilots/ai-discovery/`. `pilots/` becomes empty; remove
   it. Three editable citations in
   `droid-wiki/findings/first-h1-evidence.md` get rewritten to the
   new path.

2. **Deferred 13 entries** — every file under each of 13 entries in
   `evidence/reviews/<entry>/...` (20 files, ~1.24 MB
   / 1,244,990 bytes per the D2 inventory) →
   `evidence/reviews/archive/<entry>/...`. The D2
   inventory at
   `evidence/reviews/d2-1-builder/pre-move-sha256.json`
   gets a destinations-only update.

Both moves are pure renames. You do not edit any evidence byte.
Sister files (`ARCHIVE-INDEX.md`, `PATH-REDIRECTS.md`) get
content-only edits in the chunk's diff.

## Why this is one chunk, not two

The dossier `planning/evidence-hygiene/` was named for evidence
cleanup; `chunk-D3-1` opened it. `chunk-D4-1` finishes the
cleanup-by-relocation work that chunk-D3-1 deferred. The pilot
move is on the same commit because:

- It completes the D1 PLAN §keep-list intention (`pilots/` for
  *working* pilot slices) — leaving a research-notes directory at top
  level re-invites drift. The pilot-research files are PRD-adjacent
  record per D1 PLAN §4 ("design docs, **postmortems**") and belong
  in `planning/`.
- It is small, mechanical, and shares the lighter one-reviewer
  gating and the no-referee-token discipline.

If a reviewer rejects the chunk on the pilots-half alone — say,
because someone argues `pilots/` should stay for *future* pilot slices —
the executor splits: the deferred-13 archive lands in chunk-D4-1a,
the pilot move repeats as `chunk-D4-1b` on a fresh branch. The
operator decides at that point.

## Steps

### 1. Verify the inventory surface

`python3 -c "import json; inv=json.load(open('evidence/reviews/d2-1-builder/pre-move-sha256.json')); print('relocated:', len(inv['relocated'])); print('totals:', inv['source_file_count'], inv['source_bytes'])"`

Expected: `relocated: 34`, `totals: 34 1410544`. If different, STOP
and report. The 20 rows you'll touch are those whose
`destination` starts with `evidence/reviews/`
and whose `<entry>/<file>` path appears in the §2.2 table of CHUNK-D4-SPEC.

`for f in $(<list of 20 file paths>); do test -f "$f" || { echo "missing: $f"; exit 1; }; done`

### 2. Snapshot pre-move SHAs

```
python3 - <<'EOF' > /tmp/d4-pre-sha256.txt
import hashlib, json, io
inv = json.load(open('evidence/reviews/d2-1-builder/pre-move-sha256.json'))
for r in inv['relocated']:  # all 34; matches the inventory
    p = r['destination']
    with open(p, 'rb') as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    print(f"{sha}  {p}  expected={r['sha256']}")
EOF
diff <(awk '{print $1, $2}' /tmp/d4-pre-sha256.txt | sort) \
     <(python3 -c "import json; inv=json.load(open('evidence/reviews/d2-1-builder/pre-move-sha256.json')); [print(r['sha256'], r['destination']) for r in inv['relocated']]" | sort) \
&& echo PRE-MOVE-SHA-MATCH
```

The `PRE-MOVE-SHA-MATCH` line must print. If it does not, STOP —
the on-disk bytes do not match what the inventory says they should
be. That's a defect outside this chunk's scope.

```
python3 - <<'EOF' > /tmp/d4-pre-sha256-deferred.txt
# Same shape, restricted to the 20 rows we'll move
import hashlib, json
inv = json.load(open('evidence/reviews/d2-1-builder/pre-move-sha256.json'))
DEFERRED = {"r-drs-role-split-2","review-convention-gemini-stderr.log","review-convention-gemini.json","review-convention-grok-stderr.log","review-convention-grok.json","review-gemini-round2.json","review-gemini-stderr.log","review-gemini.json","review-grok-round2.json","review-grok-round3.json","review-grok.json","rung3-droid-exec-stderr.txt","rung3-extract-tool-calls.sh"}
for r in inv['relocated']:
    if r['destination'].split('evidence/reviews/')[1].split('/')[0] in DEFERRED:
        with open(r['destination'],'rb') as fh:
            sha = hashlib.sha256(fh.read()).hexdigest()
        print(f"{sha}  {r['destination']}")
EOF
# Verify it has 20 lines
wc -l /tmp/d4-pre-sha256-deferred.txt  # expected 20
```

Keep `/tmp/d4-pre-sha256-deferred.txt` to the chunk's build-evidence
bundle (`evidence/reviews/r-chunk-d4-1-builder-<ts>/`).

### 3. Run the chunk-D3-1 exclusion scan (no exclusions changed)

Re-confirm the chunk-D3-1 three-form scan still holds for the 13
entries before moving them. The scan source files are:
`evidence/LEDGER.md`, `tests/`, `tools/`. Bare entry name + the
two `phase-4.5/build-evidence/<entry>` forms.

For each of the 13 entry names, run:
```
for e in r-drs-role-split-2 review-convention-gemini-stderr.log review-convention-gemini.json review-convention-grok-stderr.log review-convention-grok.json review-gemini-round2.json review-gemini-stderr.log review-gemini.json review-grok-round2.json review-grok-round3.json review-grok.json rung3-droid-exec-stderr.txt rung3-extract-tool-calls.sh; do
  grep -rl -- "$e\|phase-4.5/build-evidence/$e\|evidence/reviews/$e" evidence/LEDGER.md tests/ tools/ 2>/dev/null
done | sort -u
```

Expected: empty output. If anything shows up, STOP — the entry
became referenced since chunk-D3-1, and the implication is out of
this chunk's scope.

### 4. Pilot-research files: citation rewrites + git mv

Three `droid-wiki/findings/first-h1-evidence.md` lines change:

- Line 3: `Evidence in pilots/ai-discovery/.` →
  `Evidence in planning/pilots/ai-discovery/.`
- Line 15: `Captures in pilots/ai-discovery/validator-outputs/.` →
  `Captures in planning/pilots/ai-discovery/validator-outputs/.`
- Line 56: `pilots/ai-discovery/ — the primary artifacts this page reads`
  → `planning/pilots/ai-discovery/ — the primary artifacts this page reads`

Sanity-check the relative link at line 56 first — it reads as a
relative link in markdown. The dossier-moves the linked file by one
prefix; the relative path `../../pilots/ai-discovery/` will work if
the markdown renderer treats the file's URL relative to the
repo-root, but plain GitHub will resolve relative links in markdown
relative to the *file's location*. If line 56's link is
`./pilots/ai-discovery/`, then after the move it must become
`./planning/pilots/ai-discovery/` *relative to first-h1-evidence.md's
new neighbors*, OR a repo-rooted link. Verify by reading the exact
`[]()` syntax on line 56 before editing; record the form in the
build bundle.

```
git mv pilots/ai-discovery/README.md planning/pilots/ai-discovery/README.md
git mv pilots/ai-discovery/validator-outputs/grok-ai-discovery-review.md planning/pilots/ai-discovery/validator-outputs/grok-ai-discovery-review.md
git mv pilots/ai-discovery/validator-outputs/kimi-nits-and-charset.md planning/pilots/ai-discovery/validator-outputs/kimi-nits-and-charset.md
git mv pilots/ai-discovery/validator-outputs/sitemap-unit4-validation.md planning/pilots/ai-discovery/validator-outputs/sitemap-unit4-validation.md
rmdir pilots/ai-discovery/validator-outputs
rmdir pilots/ai-discovery
rmdir pilots
# `rmdir` is the safe-empty-directory form; if non-empty STOP.
```

### 5. Archive the 13 entries: 20 git mvs

```
ARCHIVE="evidence/phase-4.5/build-evidence"
for e in r-drs-role-split-2 review-convention-gemini-stderr.log review-convention-gemini.json review-convention-grok-stderr.log review-convention-grok.json review-gemini-round2.json review-gemini-stderr.log review-gemini.json review-grok-round2.json review-grok-round3.json review-grok.json rung3-droid-exec-stderr.txt rung3-extract-tool-calls.sh; do
  if [ -d "$ARCHIVE/$e" ]; then
    git mv "$ARCHIVE/$e" "$ARCHIVE/archive/$e"
  else
    git mv "$ARCHIVE/$e" "$ARCHIVE/archive/$e"
  fi
done
ls "$ARCHIVE/archive/" | wc -l   # expected 27 (14 + 13)
```

### 6. Update the D2 inventory: destinations-only edit

```
python3 - <<'EOF'
import json, sys
INV = "evidence/reviews/d2-1-builder/pre-move-sha256.json"
inv = json.load(open(INV))
for r in inv["relocated"]:
    d = r["destination"]
    PREFIX = "evidence/reviews/"
    if d.startswith(PREFIX):
        rest = d[len(PREFIX):]
        # only rewrite for the 13 deferred entries
        DEFERRED = {"r-drs-role-split-2","review-convention-gemini-stderr.log","review-convention-gemini.json","review-convention-grok-stderr.log","review-convention-grok.json","review-gemini-round2.json","review-gemini-stderr.log","review-gemini.json","review-grok-round2.json","review-grok-round3.json","review-grok.json","rung3-droid-exec-stderr.txt","rung3-extract-tool-calls.sh"}
        entry = rest.split("/")[0]
        if entry in DEFERRED:
            r["destination"] = PREFIX + "archive/" + rest
# Re-assert immutables
assert inv["source_file_count"] == 34
assert inv["source_bytes"] == 1_410_544
assert len(inv["relocated"]) == 34
# Confirm every source still starts with build-evidence/ (pre-D2)
assert all(r["source"].startswith("build-evidence/") for r in inv["relocated"])
json.dump(inv, open(INV,"w"), indent=2)
print("inventory rewrite complete")
EOF
```

The 20 rows for the 13 deferred entries now point to
`evidence/reviews/archive/<entry>/<file>`. The 14
rows for the other entries are unchanged. `source_file_count`,
`source_bytes`, every `source`, every `bytes`, every `sha256`, the
`canonical_d1_tree` array, and the `tokens` array are all
byte-identical to the pre-chunk state.

### 7. Update `ARCHIVE-INDEX.md`

Replace the "Deferred entries (kept flat in this chunk)" heading +
its 13-row table + the bullet under Notes that points at the future
chunk. The updated index has:

- "Archived entries" — 27 rows, no `Source` / `Reason` columns: just
  `<entry>` with the reason copied from the existing index for the
  new 13 (reasons: `bootstrap probe` for review-convention-*, "BURNED,
  multiple stream/stderr shape" for r-drs-role-split-2, `bootstrap
  probe` for rung3-*).
- "Notes" section updated to remove the deferred-block paragraph and
  add a one-line *archive rule* note pointing at the D2 inventory.

The diff that lands in `ARCHIVE-INDEX.md` is the smallest possible:
do not re-analyse the 14 archived entries from chunk-D3-1; copy their
rows forward verbatim.

### 8. Add the `PATH-REDIRECTS.md` row

Append one row to the prefix table:

```
| `pilots/` → `planning/pilots/` | 4 |
```

Do not re-tabulate the existing rows; do not renumber.

### 9. Verify

Self-checks before commit. Each must exit successful:

```
python3 -m pytest -q
# expected: 241 passed, 3 skipped, 0 failed

python3 tools/wiki-link-audit.py
# expected: zero dead `pilots/ai-discovery/` (the three living-doc
# citations were rewritten), zero dead `phase-N/` from this chunk's
# diff surface (the chunk added no `phase-N/` paths).

python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D4-SPEC.md
# expected: PASS

# Verify all 24 file moves are pure 0/0 renames (4 pilots + 20 archive)
git diff --find-renames --numstat HEAD~1 HEAD
# expected: 20 rows of "0\t0\t..." for archive; 4 rows of "0\t0\t..."
# for pilots; non-zero numstat only on the four content edits
# (ARCHIVE-INDEX.md, PATH-REDIRECTS.md, D2 inventory JSON, the wiki
# citation file).

# Verify SHA-256 byte-identity for the 20 archive files:
python3 - <<'EOF'
import hashlib, json
inv = json.load(open('evidence/reviews/d2-1-builder/pre-move-sha256.json'))
mismatches = 0
for r in inv["relocated"]:
    p = r["destination"]
    with open(p, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    if sha != r["sha256"]:
        mismatches += 1
        print("MISMATCH:", p, "got", sha, "want", r["sha256"])
print(f"mismatches: {mismatches}")  # expected: 0
EOF

# Verify git log --follow reaches immediate-post-D2 commit for
# representatives from each category
git log --follow evidence/reviews/archive/drs-role-split-2/gemini-2.5-pro.stream.json | grep -q 4965f1e && echo OK-1
git log --follow evidence/reviews/archive/review-convention-gemini.json | grep -q 4965f1e && echo OK-2
git log --follow evidence/reviews/archive/rung3-extract-tool-calls.sh | grep -q 4965f1e && echo OK-3
# expected: OK-1 OK-2 OK-3 all print
```

Capture every command and its output in the build-evidence bundle.

### 10. Build-evidence bundle

```
mkdir -p evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)
# Move the snapshotted files into the bundle
mv /tmp/d4-pre-sha256.txt       evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)/pre-move-sha256-all-34.txt
mv /tmp/d4-pre-sha256-deferred.txt   evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)/pre-move-sha256-deferred-20.txt
# Save this prompt and the spec; save executor + verifier envelopes when they fire
cp PROMPT-D4-BUILDER.md        evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)/PROMPT-D4-BUILDER.md
cp CHUNK-D4-SPEC.md            evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)/CHUNK-D4-SPEC.md
# Run the §9 verifies and capture outputs:
python3 -m pytest -q    > evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)/pytest.txt 2>&1
python3 tools/wiki-link-audit.py > evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)/wiki-link-audit.txt 2>&1
python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D4-SPEC.md > evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)/plan-lint.txt 2>&1
git diff --find-renames --numstat HEAD~1 HEAD   > evidence/reviews/r-chunk-d4-1-builder-$(date +%Y%m%d-%H%M)/diff-numstat.txt 2>&1
```

The bundle must exist BEFORE commit. The verifier (§11) inspects
it; an empty bundle is grounds for REJECT.

### 11. Fire the verifier

After the moves and content edits, fire the dossier's verifier via
the project standard:

```
$EDITOR evidence/reviews/r-chunk-d4-1-review-$(date +%Y%m%d-%H%M)/PROMPT-REVIEWER-D4.md
# Write a reviewer prompt that asks for the same checks chunk-D3-1's
# verifier used (kimi-k3 + minimax-m3 cross-family OR single-reviewer
# dossier §5 form), with diff --summary + numstat + SHA-recompute +
# pytest result as scope.

bash tools/run-with-model.sh droid exec --model <reviewer-id> \
  --workspace evidence/reviews/r-chunk-d4-1-review-$(date +%Y%m%d-%H%M) \
  --prompt-file PROMPT-REVIEWER-D4.md
```

Capture the model envelope JSON. Save it under
`evidence/reviews/r-chunk-d4-1-review-$(date +%Y%m%d-%H%M)/<model>.json`.

### 12. Commit

One commit. Subject exactly:

```
chunk-D4-1: archive deferred 13 entries + relocate pilots/ → planning/
```

Body:

```
* 20 evidence bytes archived under evidence/reviews/archive/
  (14 already-archived entries from chunk-D3-1 + 13 entries just archived).
  By-file SHA-256 byte-identical to D2 inventory record
  (evidence/reviews/d2-1-builder/pre-move-sha256.json).
  D2 inventory: 20 destination fields updated, all other fields
  unchanged (source, source_file_count=34, source_bytes=1410544,
  per-row sha256, canonical_d1_tree, tokens).

* pilots/ → planning/pilots/ai-discovery/ (4 files, 24 KB).
  pilots/ removed. Three editable citations in
  droid-wiki/findings/first-h1-evidence.md updated.
  New PATH-REDIRECTS.md row.

* ARCHIVE-INDEX.md refreshes the deferred-block paragraph with an
  archive-rule pointer at the D2 inventory; 27-entry archive table.

* Suite green: 241 passed, 3 skipped. wiki-link-audit.py: zero dead.
  plan-lint.py on CHUNK-D4-SPEC: PASS. git diff --find-renames
  shows pure 0/0 renames for all 26 relocated files.

* Predecessor: chunk-D3-1 @ main 5bef37a. One reviewer (dossier §5).
```

Branch: `factory/d4-final-cleanup`. Push to `dev` remote ONLY.

### 13. Tile for the wiki

After merge lands on main, the dossier is closed. The wiki path
sweep (§2.4's citations + the redirected `PATH-REDIRECTS.md` rows)
becomes the wiki chunk's own diff surface — separate and atomic, by
your earlier ask.

## Hard fences (do not cross)

- Do not edit, delete, or regenerate any evidence byte. All
  archive files are byte-identical to pre-move.
- Do not touch evidence/phase-4.5/tokens/, evidence/LEDGER.md, or
  any committed envelope JSON. The D2 inventory's *destination*
  fields are the sole evidence-tree edit (immutables — `source`,
  `bytes`, `sha256`, `source_file_count`, `source_bytes`,
  `canonical_d1_tree`, `tokens` — are unchanged).
- Do not modify the chunk-D3-1 spec or ARCHIVE-INDEX rows from
  chunk-D3-1 except as §7 specifies (refresh deferred-block; copy
  forward archived-blocks verbatim).
- Do not add a chunk close token, sign `chunk-D4-1.token.json`,
  hold `EVIDENCE_SIGNING_KEY`, or fire a two-family gate. This
  chunk is lighter gating per dossier.
- Do not edit the dossier name `planning/evidence-hygiene/`. If a
  reviewer argues the name should move, that is a separate operator
  decision; the executor does not rename the dossier in this chunk.
- Do not remove any untracked file. `r-f10/` residue at
  `evidence/reviews/r-f10/` is out of scope; the
  move-then-restore step is not in this chunk.
- Do not push to `main`. One push to `dev`, no force-push.
