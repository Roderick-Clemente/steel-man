# Chunk-D4-1 cross-family verifier prompt

You are validating chunk-D4-1, a structural cleanup chunk. The full author spec is
`planning/evidence-hygiene/CHUNK-D4-SPEC.md`; the builder prompt is
`planning/evidence-hygiene/PROMPT-D4-BUILDER.md`; the build-evidence bundle sits at
`evidence/phase-4.5/build-evidence/r-chunk-d4-1-builder-20260815-0916/`. You are reviewing the
single build commit `0663444 chunk-D4-1: archive deferred 13 entries + relocate pilots/ → planning/`
on top of `fee5b37` (which is itself already on `main`).

## Diff scope

```
M  droid-wiki/findings/first-h1-evidence.md            (3 inline-code citation rewrites)
R100  4 files: pilots/ai-discovery/... → planning/pilots/ai-discovery/...
R100 20 files: evidence/phase-4.5/build-evidence/<entry>/<file> →
              evidence/phase-4.5/build-evidence/archive/<entry>/<file>
M  evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json  (42 lines; 20 dest fields)
M  planning/PATH-REDIRECTS.md                           (heading + 1 new row)
M  planning/evidence-hygiene/ARCHIVE-INDEX.md           (title + 12 new rows + 1 archive-rule note)
A  10 evidence/phase-4.5/build-evidence/r-chunk-d4-1-builder-20260815-0916/* files
```

Total non-rename content delta is approximately 60 changed lines. All renames reported by the
builder are `0 0` numstat. Spec's stated renames are 24 (4 pilots + 20 archive); plus 22 archive
entries existed at 685e379 / 58c11d3 (chunk-D3-1 baseline) and the 13 newly-added here bring the
archive to 27 entries.

## Authoritative spec numbers

These are grounded in `evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json`
and the SHA-256 pre-move snapshot at
`evidence/phase-4.5/build-evidence/r-chunk-d4-1-builder-20260815-0916/pre-move-sha256-deferred-20.txt`.
Do NOT hand-paraphrase. If your numbers disagree, STOP and report.

| Quantity | Truth | Source |
|---|---|---|
| Total inventory rows | 34 | `len(inv['relocated'])` |
| Total inventory bytes | 1,410,544 | `inv['source_bytes']` |
| Deferred entries (newly moved into archive/) | 13 | enumeration against PROMPT-D4-BUILDER §1.b |
| Deferred files relocated (rows whose destination has `/archive/` after this chunk) | 20 | re-read post-commit inventory |
| Pilot files relocated | 4 | `git mv` plan in CHUNK-D4-SPEC §2.1 |
| D2 inventory source <-> destination mappings changed by chunk-D4-1 | 20 (destination only) | `git diff -- pre-move-sha256.json` |
| Total droid-wiki inline-code citations rewrote | 3 (lines 3, 15, 56 of `first-h1-evidence.md`) | direct file read |
| Archive entries after the chunk | 27 (= 14 from chunk-D3-1 + 13 from chunk-D4-1) | `ls evidence/phase-4.5/build-evidence/archive/` |
| `pilots/` top-level | absent post-commit | `ls pilots/` should fail |
| `planning/pilots/` exists | true after mkdir | direct path check |
| pytest | 241 passed, 3 skipped | builder-reported, confirmed in build bundle |
| wiki-link-audit | clean (61 pages, dead=0, anchor=0, abs=0, escaping=0, skeleton=0) | builder-reported |

## Floor checks (must reproduce from a fresh starting point)

Per `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`:

- `grok-4.5 = ("xai", "grok-family")`
- `gemini-3.1-pro-preview = ("google", "gemini-family")`
- `kimi-k3 = ("moonshot", "kimi-family")`
- `minimax-m3 = ("minimax", "minimax-family")`

The chunk-D4-1 build was authored by this agent (here, the reviewer). You are running in a SEPARATE
session with a SEPARATE model family. Author ≠ verifier is preserved because the orchestrator routes
your call through `tools/run-with-model.sh droid exec --model <your-model-id>` and you have no shared
context window with the builder. If you suspect you are sharing a model family with the builder's
session identifier `0663444`, STOP and report — that is a `tools/orchestrate-review.py` step-4
parse-fail condition (KNOWN-ISSUES KN-14).

## Verification protocol

For each numbered check below, run the EXACT command, capture exit code + truncated stdout, and mark
PASS/FAIL/N-A with one sentence of evidence. Cite the file and line when relevant.

### Check 1 — `pilots/` is gone from top level

```sh
git ls-tree HEAD pilots/   # expected empty
ls pilots 2>&1            # expected: No such file or directory
```

### Check 2 — All 4 pilots are at `planning/pilots/ai-discovery/...`

```sh
git ls-tree HEAD planning/pilots/   # expected: ai-discovery subtree
git ls-tree HEAD planning/pilots/ai-discovery/  # expected: README.md, validator-outputs/
git ls-tree -r HEAD planning/pilots/ai-discovery/validator-outputs/  # expected: 3 files
```

### Check 3 — All 20 archive `git mv`s are pure renames (`0 0` numstat)

```sh
git diff --find-renames --numstat fee5b37..HEAD -- evidence/phase-4.5/build-evidence/ | grep -v '^\s*0\s*0\s'  # expected empty
```

### Check 4 — `archive/` directory contains 27 entries (14 D3-1 + 13 D4-1)

```sh
ls -1 evidence/phase-4.5/build-evidence/archive/ | wc -l   # expected: 27
ls -1 evidence/phase-4.5/build-evidence/archive/  # confirm 13 newly-added: r-drs-role-split-2, 4 review-convention-{gemini,grok}.{json,stderr.log}, review-gemini-{round2.json,stderr.log,json}, review-grok-{round2,round3}.json (note: review-grok.json is also one of the 20), rung3-{droid-exec-stderr.txt,extract-tool-calls.sh}
```

### Check 5 — Post-move SHA-256 byte-identity for the 20 newly-archived files

```sh
python3 -c "
import json, hashlib
inv = json.load(open('evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json'))
mm = 0
n = 0
for r in inv['relocated']:
    if '/archive/' not in r['destination']:
        continue
    sha = hashlib.sha256(open(r['destination'], 'rb').read()).hexdigest()
    if sha != r['sha256']:
        mm += 1
    n += 1
print(f'checked={n} mismatches={mm}')
"
```

Expected output: `checked=20 mismatches=0`.

### Check 6 — D2 inventory immutables preserved

```sh
python3 -c "
import json
inv = json.load(open('evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json'))
print(f'source_file_count={inv[\"source_file_count\"]}')   # expected: 34
print(f'source_bytes={inv[\"source_bytes\"]}')             # expected: 1410544
print(f'canonical_d1_tree={len(inv[\"canonical_d1_tree\"])}')  # expected: 6
print(f'tokens={len(inv[\"tokens\"])}')                   # expected: 12
print(f'rows={len(inv[\"relocated\"])}')                   # expected: 34
print(f'archive_rows={sum(1 for r in inv[\"relocated\"] if \"/archive/\" in r[\"destination\"])}')  # expected: 20
"
```

### Check 7 — D2 inventory `git diff` lines is destination-only (21 inserted, 21 deleted = 42 changed lines)

```sh
git diff --numstat fee5b37..HEAD -- evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json
```

Expected: a single `21 21` line. Confirm the 20 destination lines change and ZERO other lines
(source, bytes, sha256, canonical_d1_tree, tokens).

### Check 8 — `droid-wiki/findings/first-h1-evidence.md` rewrites

```sh
grep -nE 'pilots/ai-discovery|planning/pilots/ai-discovery' droid-wiki/findings/first-h1-evidence.md
```

Expected: 3 lines contain `planning/pilots/ai-discovery`, all 3 with the planning/ prefix. ZERO lines
containing the old `pilots/ai-discovery` form (without `planning/`).

### Check 9 — `planning/PATH-REDIRECTS.md` row appended

```sh
grep -nE 'pilots/|planning/pilots' planning/PATH-REDIRECTS.md
```

Expected: a new row appended with `pilots/` → `planning/pilots/`, count column `4`. Confirm heading
notes the new row count.

### Check 10 — `ARCHIVE-INDEX.md` reflects 27 entries

```sh
grep -cE '^\| r-' planning/evidence-hygiene/ARCHIVE-INDEX.md   # expected: 27 (table rows)
grep -nE 'chunk-D3-1|chunk-D4-1' planning/evidence-hygiene/ARCHIVE-INDEX.md  # confirm both chunks cited
```

### Check 11 — Suite + linters green

```sh
python3 -m pytest --tb=no -q   # expected: 241 passed, 3 skipped
python3 tools/wiki-link-audit.py   # expected: clean (61 pages, 0 issues)
python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D4-SPEC.md   # expected PASS
```

### Check 12 — Three-form exclusion scan re-run (chunk-D3-1 §3 invariant, applied to the 13 NEWLY archived entries only)

For each of these 13 entries: `r-drs-role-split-2`, `review-convention-gemini-stderr.log`,
`review-convention-gemini.json`, `review-convention-grok-stderr.log`, `review-convention-grok.json`,
`review-gemini-round2.json`, `review-gemini-stderr.log`, `review-gemini.json`, `review-grok-round2.json`,
`review-grok-round3.json`, `review-grok.json`, `rung3-droid-exec-stderr.txt`, `rung3-extract-tool-calls.sh`:

Test each of the three forms: `<entry>`, `phase-4.5/build-evidence/<entry>`,
`evidence/phase-4.5/build-evidence/<entry>` against `evidence/LEDGER.md`, `tests/`, `tools/`.

Expected: 0 hits for any combination (these 13 were already zero-reference at chunk-D3-1 time per
its review round-2 verdict; the only archive delta since is the move into `archive/`, no new references).

### Check 13 — Git history travels with the moves

```sh
git log --follow --oneline -5 evidence/phase-4.5/build-evidence/archive/r-drs-role-split-2/grok-4.5.stream.json
git log --follow --oneline -5 planning/pilots/ai-discovery/README.md
```

Expected: each path's --follow traces back to `4965f1e` (D2 baseline) at minimum; the README.md
follows back through `ee90061` (D1 baseline).

### Check 14 — Scope escapes

```sh
git diff fee5b37..HEAD -- tokens/ evidence/LEDGER.md tests/ tools/orchestrate-review.py tools/cross_family_review.py   # expected: empty
git ls-tree HEAD pilots/    # expected: empty
git log fee5b37..HEAD --oneline | wc -l   # expected: 1 (just the chunk commit)
```

## Output format

Return a single markdown report with these sections in this order:

1. A per-check PASS/FAIL table (rows numbered 1–14).
2. A "Findings" section. Each finding, if any, must use exactly this shape (TAML keys in `code`-block text):
   ```
   - severity: <blocker|high|medium|low|nit>
     category: <correctness|process|scope|factual|convention|security>
     section: <path>:<line range> OR <commit message phrase>
     claim: <one short factual sentence>
     evidence: <one short paragraph: commands run, exit codes, observed output, pointers to file:line>
     recommended_change: <one short actionable sentence OR "no gate action">
   ```
3. A single final line: `VERDICT: ACCEPT` / `VERDICT: ACCEPT-WITH-NITS` / `VERDICT: REJECT`.

Deduplicate. If two findings name the same root cause for different files, keep only the one with the
clearest anchor. Re-verify every claim with a tool call; cite the actual output, NOT a paraphrase.
Do not invent counts.

A finding is REPORTABLE iff it would block an honest merge. Cosmetic notes (subjective wording
preferences, test-file verbosity, file organization nitpicks NOT anchored to a documented convention
or to a sibling-file pattern) are FILTERED OUT and reported as a single line under "Findings"
prefixed `nit:`.
