# tools/conventions/review-bundle.md

Canonical bundle shape for `evidence/phase-4.5/build-evidence/r-chunk-N-review-<ts>/`
directories. The two canonical **exemplars** cited below are the
artefacts this document formalises; plagiarism of the layout is fine.

## 1. Directory layout

```
r-chunk-N-review-<ts>/
├── round1/
│   ├── review-<model>-envelope.json   (droid exec --output-format json)
│   ├── review-<model>-stderr.log       (empty on success — defect signal otherwise)
│   └── verifier-prompt.md              (the reviewer's brief)
├── round2/...                          (only if round1 was REJECT)
└── SUMMARY.md                          (chunk-level verdict; always present)
```

## 2. Envelope shape — `round{N}/review-<model>-envelope.json`

Top-level keys verbatim from `droid exec --output-format json`:

| Key           | Type   | Notes                                                            |
|---------------|--------|------------------------------------------------------------------|
| `result`      | string | Reviewer markdown body (findings + verdict + evidence).          |
| `session_id`  | string | Droid UUID; stable across re-fires.                              |
| `usage`       | object | `input_tokens`, `output_tokens`, `cache_read_input_tokens`, …   |
| `duration_ms` | int    | Wall-clock ms for the run.                                       |

The 27-char SHA prefix referenced by `tools/cross_family_review.py`
is `hashlib.sha256(open(json_path,'rb').read()).hexdigest()[:27]`; the
same gate's full 64-char SHA appears in the chunk-close token, whose
first 50 chars form a `PLACEHOLDER_LEADING_RUN_MIN` fingerprint.

## 3. SUMMARY.md section order

Matches the `r-chunk-d3-1-review-20260814-2152/SUMMARY.md` and
`r-chunk-d4-1-review-20260815-1423/SUMMARY.md` exemplars:

1. Header — commit under review (`git show <sha>` + parent), branch,
   dossier reference (`planning/evidence-hygiene/PLAN.md §2`).
2. Round-by-round tables — per round: `Validator | Family | Verdict |
   Envelope SHA-256`.
3. Findings — TAML bullets (`severity` / `category` / `section` /
   `claim` / `evidence` / `recommended_change`).
4. Final verdict — `ACCEPT-WITH-NITS` / `REJECT`, plus a process note
   if a round was invalidated and re-fired.

## 4. Stderr/log convention

`droid exec` stderr routes to `review-<model>-stderr.log` next to the
envelope. **On success the log is empty.** A non-empty log is a defect
signal — capture in SUMMARY process notes.

## 5. Model family taxonomy

Derive reviewer family from `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`,
not from this doc. A future droid re-derives family from the canonical
map so provider re-homing doesn't silently stale this convention.

## 6. Exemplars

| Path                                                              | What this exemplar teaches                                                              |
|-------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `…/r-chunk-d3-1-review-20260814-2152/SUMMARY.md`                 | judgment-call: 2-round review, REJECT → ACCEPT-WITH-NITS, per-round SHAs in table.      |
| `…/r-chunk-d4-1-review-20260815-1423/SUMMARY.md`                 | audit-script-only: single round, dual cross-family ACCEPT-WITH-NITS; nits quieted.      |
