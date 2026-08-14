# Chunk-3 citation inventory — measured at `cae00ed`

Builder seat, read-only. Produced while chunk-D1-2 is BLOCKED, because this
inventory is derivable from the *current* tree and is exactly what Chunk 3
needs. Nothing was modified.

Method: `grep -oE '(phase-[0-9]+(\.[0-9]+)?)/[A-Za-z0-9_./-]+'` over the
CHUNK-3-SPEC §2.1 allowlist. Counts are path-shaped tokens, not lines.

| allowlist entry | citations | files |
|---|---|---|
| `droid-wiki/*.md` | **320** | 46 |
| `planning/*.md` (all) | 289 | 7 |
| `tools/OPERATING-RULES.md` | 15 | 1 |
| `PRD.md` | 9 | 1 |
| `README.md` | 8 | 1 |
| `tools/sprint_loop/prompts/*.md` | 6 | 3 |
| `skills/*.md` | 5 | 2 |
| `tools/conventions/*.md` | 1 | 1 |
| `AGENTS.md` | 1 | 1 |
| `tools/README.md`, `KNOWN-ISSUES.md`, `PHASE-0.5-CLOSE.md`, `RUN-LEDGER.md`, `REPRODUCE.md` | 0 | — |
| **total** | **654** | |

Of the 289 under `planning/`, **188 sit in `planning/layout-refactor/`**
(`PLAN.md` 79, `CHUNK-1-SPEC` 55, `CHUNK-2-SPEC` 44, `CHUNK-3/4-SPEC` 5+5).
Those are the specs *describing* the move, and §2.1's allowlist names only
`planning/ROADMAP-REVIEW*.md`, so they are out of scope. In-scope total is
therefore **≈466**, plus the docs Chunk 2 moves into `planning/<phase>/`, which
cannot be counted until Chunk 2 runs.

## Finding — §17 capacity envelope is understated ~3x

CHUNK-3-SPEC §1 says "~150 md citations". Measured in-scope is **≈466** before
Chunk 2's moved docs are added. `droid-wiki/` alone is 320 across 46 files —
more than double the whole stated envelope, and §2.1 scopes it to "path tokens
only", which bounds the *kind* of edit but not the count.

Not a defect in the plan's shape; a number worth correcting before the chunk is
sized, since §17 refuses unbounded programs and §5's hard stop is written as if
the residual set were small.

## PATH-REDIRECTS.md surface: 48 unique old prefixes

Heaviest, and the reason `evidence/` dominates the redirects table:

| old prefix | citations |
|---|---|
| `phase-0/evidence` | 119 |
| `phase-3.2/evidence` | 56 |
| `phase-1/scripts` | 28 |
| `phase-3.2/build-evidence` | 23 |
| `phase-0/GO-NO-GO` | 23 |
| `phase-0/README` | 10 |
| `phase-3.1/RESULTS`, `phase-1/locks` | 8 each |

`phase-0/evidence` at 119 is a single table row in PATH-REDIRECTS but a third of
the whole citation load — worth confirming those are genuine path citations and
not one repeated narrative reference before Chunk 3 is sized.
