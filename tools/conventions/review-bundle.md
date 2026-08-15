# tools/conventions/review-bundle.md

Canonical bundle shape for chunk-review directories. Two layouts:
**historical** (frozen; `evidence/phase-4.5/build-evidence/<bundle>/`,
exemplars in §6) and **current** (sprint-keyed;
`${REPO_ROOT}/evidence/reviews/<sprint-name>/round{N}/`) for new
chunks from chunk-D5-1b. Migration of historical files is a roadmap
item (chunk-D5a/D6), out of scope here.

## 1. Directory layout

### 1.Historical (frozen) — pre-chunk-D5-1b artifacts

```
evidence/phase-4.5/build-evidence/<bundle>/       (named r-chunk-N-review-<ts>)
├── round1/{review-<model>-envelope.json, review-<model>-stderr.log, verifier-prompt.md}
├── round2/...                                   (only if round1 was REJECT)
└── SUMMARY.md                                   (chunk-level verdict; always present)
```

Frozen at current paths. Exemplars in §6 live here; **new chunks
do not add to this tree**.

### 1.Current (sprint-keyed) — new chunks from chunk-D5-1b onwards

```
${REPO_ROOT}/evidence/reviews/<sprint-name>/       (sprint-name = the 3rd positional arg)
├── round1/{review-<model>-envelope.json, review-<model>-stderr.log, verifier-prompt.md}
├── round2/...                                      (only if round1 was REJECT)
└── SUMMARY.md                                      (chunk-level verdict; always present)
```

`<sprint-name>` is the 3rd positional arg to `tools/run-review.sh`,
which auto-derives the next vacant `round{N}/` (scans
`round1..round10/`) and never writes to cwd.

## 2. Envelope shape — `round{N}/review-<model>-envelope.json`

Top-level keys verbatim from `droid exec --output-format json`:

| Key           | Type   | Notes                                                            |
|---------------|--------|------------------------------------------------------------------|
| `result`      | string | Reviewer markdown body (findings + verdict + evidence).          |
| `session_id`  | string | Droid UUID; stable across re-fires.                              |
| `usage`       | object | `input_tokens`, `output_tokens`, `cache_read_input_tokens`, …   |
| `duration_ms` | int    | Wall-clock ms for the run.                                       |

The 27-char SHA prefix is `hashlib.sha256(open(json_path,'rb').read()).hexdigest()[:27]`;
the full 64-char SHA also appears in the chunk-close token.

## 3. SUMMARY.md section order

Matches the `r-chunk-d3-1-review-20260814-2152/SUMMARY.md` and
`r-chunk-d4-1-review-20260815-1423/SUMMARY.md` exemplars:

1. Header — commit under review (`git show <sha>` + parent), branch, dossier reference (`planning/evidence-hygiene/PLAN.md §2`).
2. Round-by-round tables — per round: `Validator | Family | Verdict | Envelope SHA-256`.
3. Findings — TAML bullets (`severity` / `category` / `section` / `claim` / `evidence` / `recommended_change`).
4. Final verdict — `ACCEPT-WITH-NITS` / `REJECT`, plus a process note if a round was invalidated and re-fired.

## 4. Stderr/log convention

`droid exec` stderr routes to `review-<model>-stderr.log`. **On success
the log is empty**; a non-empty log is a defect signal (SUMMARY notes).

## 5. Model family taxonomy

Derive reviewer family from `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`,
not this doc — so provider re-homing doesn't stale this convention.

## 6. Exemplars

| Path                                                              | What this exemplar teaches                                                              |
|-------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `…/r-chunk-d3-1-review-20260814-2152/SUMMARY.md`                 | judgment-call: 2-round review, REJECT → ACCEPT-WITH-NITS, per-round SHAs in table.      |
| `…/r-chunk-d4-1-review-20260815-1423/SUMMARY.md`                 | audit-script-only: single round, dual cross-family ACCEPT-WITH-NITS; nits quieted.      |
