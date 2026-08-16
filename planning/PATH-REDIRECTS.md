# `PATH-REDIRECTS.md` — old path → new home

Deliverable D1 (chunk-D1-2, commit `ee90061`) moved **618 tracked files** out of
the `phase-N/` silos and into homes organized by kind. This file is how a citation
written before that move is still followable afterwards.

It exists because the alternative does not scale and would not be honest.
**788** bare `phase-N/` tokens survive the move across markdown; **105** of them
sit in living documents that a reader follows today, and those were rewritten in
chunk-D1-3. The other **683** must not be edited at all:

* **`planning/layout-refactor/**` (265 tokens at measurement time)** — the move
  specs. Their `phase-N/` tokens are the *before* side of move tables. "Updating"
  `` `phase-0/evidence/` → `evidence/phase-0/` `` yields
  `` `evidence/phase-0/` → `evidence/phase-0/` `` and destroys the document.
* **`planning/phase-N/**` (418 tokens, 357 after the LEDGER moved out)** —
  time-stamped run records. `planning/phase-3/RUN-COMMANDS.md` records the literal
  command that was executed at the time. Rewriting it produces a command that was
  never run: a falsified record in exchange for a working link.
* **Committed evidence under `evidence/`** — immutable by §5/§21. 146 lines
  across 78 envelope/capture files carry old prefixes and stay exactly as
  the reviewer wrote them. (Measured at `0b5343d`, tracked files only. The
  pin is deliberate: this count grows with every evidence commit, so an unpinned
  figure is stale the moment it is written — which is how the previous hand-typed
  144/76 got here.)

For all of those, this file carries the delta instead. That is the §5 hard stop
working as designed rather than a scope cut.

## Matching algorithm

Carried from `planning/layout-refactor/PLAN.md`:

1. Strip an optional absolute repo-root prefix
   (`/Users/factory/work/adversarial-sprint-dev/`) from the cited path.
2. Match the **longest** old prefix in the table below against the resulting
   relative path.
3. Apply only to path-shaped tokens:
   `(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry|evidence|planning)/[\w/.-]+`
4. Leave prose mentions ("Phase 1 built…") untouched.

The mapping is **segment-preserving**: everything after the matched prefix is
copied through unchanged, so
`phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt` →
`evidence/reviews/drs-role-split-1/envelopes/grok-4.5.raw.txt`.

## Prefix table — 45 rows (44 from `ee90061`, 1 added by chunk-D4-1)

Generated from the move commit's own rename records
(`git show --name-status --find-renames`), not hand-transcribed, and every
destination is probed on disk before this file is written. The count is how many
files moved under that prefix.

| redirect | files |
|---|---|
| `phase-0/` → `planning/phase-0/` | 2 |
| `phase-0/evidence/` → `evidence/phase-0/` | 159 |
| `phase-1/` → `planning/phase-1/` | 5 |
| `phase-1/build-evidence/` → `evidence/phase-1/build-evidence/` | 6 |
| `phase-1/fixtures/` → `tests/fixtures/phase-1/` | 4 |
| `phase-1/hooks/` → `tools/phase-1-hooks/` | 1 |
| `phase-1/locks/` → `tools/phase-1-locks/` | 6 |
| `phase-1/probes/` → `tools/phase-1-probes/` | 1 |
| `phase-1/prompts/` → `planning/phase-1/prompts/` | 2 |
| `phase-1/scripts/` → `tools/phase-1-scripts/` | 3 |
| `phase-2/` → `planning/phase-2/` | 5 |
| `phase-2/build-evidence/` → `evidence/phase-2/build-evidence/` | 10 |
| `phase-2/reviews/` → `planning/phase-2/reviews/` | 3 |
| `phase-3.1/` → `planning/phase-3.1/` | 3 |
| `phase-3.1/` → `tools/phase-3.1-gen/` | 1 |
| `phase-3.1/build-evidence/` → `evidence/phase-3.1/build-evidence/` | 42 |
| `phase-3.1/locks/` → `tools/phase-3.1-locks/` | 3 |
| `phase-3.1/prompts/` → `planning/phase-3.1/prompts/` | 10 |
| `phase-3.2/` → `planning/phase-3.2/` | 7 |
| `phase-3.2/build-evidence/` → `evidence/phase-3.2/build-evidence/` | 6 |
| `phase-3.2/evidence/` → `evidence/phase-3.2/` | 2 |
| `phase-3.2/evidence/` → `tools/phase-3.2-evidence/` | 3 |
| `phase-3.2/reviews/` → `evidence/phase-3.2/reviews/` | 14 |
| `phase-3.2/reviews/` → `planning/phase-3.2/reviews/` | 2 |
| `phase-3.3/` → `planning/phase-3.3/` | 1 |
| `phase-3/` → `planning/phase-3/` | 4 |
| `phase-3/` → `tools/phase-3-gen/` | 1 |
| `phase-3/build-evidence/` → `evidence/phase-3/build-evidence/` | 26 |
| `phase-3/prompts/` → `planning/phase-3/prompts/` | 9 |
| `phase-3/reviews/` → `evidence/phase-3/reviews/` | 1 |
| `phase-4.5/` → `planning/phase-4.5/` | 19 |
| `phase-4.5/adversarial_review/` → `planning/phase-4.5/adversarial_review/` | 11 |
| `phase-4.5/build-evidence/` → `evidence/reviews/` | 158 |
| `phase-4.5/prompts/` → `planning/phase-4.5/prompts/` | 3 |
| `phase-4.5/tokens/` → `evidence/phase-4.5/tokens/` | 5 |
| `phase-4/` → `evidence/phase-4/` | 4 |
| `phase-4/` → `planning/phase-4/` | 5 |
| `phase-4/` → `tools/phase-4-gen/` | 2 |
| `phase-4/demo/` → `planning/phase-4/demo/` | 4 |
| `phase-4/h-ci/` → `evidence/phase-4/h-ci/` | 44 |
| `phase-4/h3/` → `evidence/phase-4/h3/` | 12 |
| `phase-5/` → `planning/phase-5/` | 3 |
| `phase-5/prompts/` → `planning/phase-5/prompts/` | 2 |
| `phase-5/scripts/` → `tools/phase-5-scripts/` | 3 |
| `pilots/` → `planning/pilots/` | 4 |

### Prefixes that fan out to more than one root

The move split silos by **kind**, so a few old prefixes have no single answer:
code went to `tools/`, committed evidence to `evidence/`, plans and prompts to
`planning/`. Longest-prefix matching is not enough for these; resolve them
file by file.

**`phase-3.1/`**

| old | new |
|---|---|
| `phase-3.1/RESULTS.md` | `planning/phase-3.1/RESULTS.md` |
| `phase-3.1/RUN-PROMPT.md` | `planning/phase-3.1/RUN-PROMPT.md` |
| `phase-3.1/SPIKE.md` | `planning/phase-3.1/SPIKE.md` |
| `phase-3.1/gen-telemetry.py` | `tools/phase-3.1-gen/gen-telemetry.py` |

**`phase-3.2/evidence/`**

| old | new |
|---|---|
| `phase-3.2/evidence/bundle_schema_v1.json` | `evidence/phase-3.2/bundle_schema_v1.json` |
| `phase-3.2/evidence/consumer.py` | `tools/phase-3.2-evidence/consumer.py` |
| `phase-3.2/evidence/local_backend.py` | `tools/phase-3.2-evidence/local_backend.py` |
| `phase-3.2/evidence/security_allowlist.json` | `evidence/phase-3.2/security_allowlist.json` |
| `phase-3.2/evidence/token_accounting.py` | `tools/phase-3.2-evidence/token_accounting.py` |

**`phase-3.2/reviews/`**

| old | new |
|---|---|
| `phase-3.2/reviews/RUN-COMMANDS.md` | `planning/phase-3.2/reviews/RUN-COMMANDS.md` |
| `phase-3.2/reviews/orchestrated/review-gemini-3.1-pro-preview-envelope.json` | `evidence/phase-3.2/reviews/orchestrated/review-gemini-3.1-pro-preview-envelope.json` |
| `phase-3.2/reviews/orchestrated/review-gemini-3.1-pro-preview-stderr.log` | `evidence/phase-3.2/reviews/orchestrated/review-gemini-3.1-pro-preview-stderr.log` |
| `phase-3.2/reviews/orchestrated/review-grok-4.5-envelope.json` | `evidence/phase-3.2/reviews/orchestrated/review-grok-4.5-envelope.json` |
| `phase-3.2/reviews/orchestrated/review-grok-4.5-stderr.log` | `evidence/phase-3.2/reviews/orchestrated/review-grok-4.5-stderr.log` |
| `phase-3.2/reviews/orchestrated/review-summary.json` | `evidence/phase-3.2/reviews/orchestrated/review-summary.json` |
| `phase-3.2/reviews/review-gemini-envelope.json` | `evidence/phase-3.2/reviews/review-gemini-envelope.json` |
| `phase-3.2/reviews/review-gemini-stderr.log` | `evidence/phase-3.2/reviews/review-gemini-stderr.log` |
| `phase-3.2/reviews/review-grok-envelope.json` | `evidence/phase-3.2/reviews/review-grok-envelope.json` |
| `phase-3.2/reviews/review-grok-stderr.log` | `evidence/phase-3.2/reviews/review-grok-stderr.log` |
| `phase-3.2/reviews/review-prompt.md` | `planning/phase-3.2/reviews/review-prompt.md` |
| `phase-3.2/reviews/roadmap-review-cross-family-findings.json` | `evidence/phase-3.2/reviews/roadmap-review-cross-family-findings.json` |
| `phase-3.2/reviews/roadmap-review-gemini-envelope.json` | `evidence/phase-3.2/reviews/roadmap-review-gemini-envelope.json` |
| `phase-3.2/reviews/roadmap-review-grok-envelope.json` | `evidence/phase-3.2/reviews/roadmap-review-grok-envelope.json` |
| `phase-3.2/reviews/roadmap-review-v2-cross-family-findings.json` | `evidence/phase-3.2/reviews/roadmap-review-v2-cross-family-findings.json` |
| `phase-3.2/reviews/roadmap-review-v2-gemini-envelope.json` | `evidence/phase-3.2/reviews/roadmap-review-v2-gemini-envelope.json` |

**`phase-3/`**

| old | new |
|---|---|
| `phase-3/KICKOFF.md` | `planning/phase-3/KICKOFF.md` |
| `phase-3/KNOWN-ISSUES.md` | `planning/phase-3/KNOWN-ISSUES.md` |
| `phase-3/README.md` | `planning/phase-3/README.md` |
| `phase-3/RUN-COMMANDS.md` | `planning/phase-3/RUN-COMMANDS.md` |
| `phase-3/gen-telemetry.py` | `tools/phase-3-gen/gen-telemetry.py` |

**`phase-4/`**

| old | new |
|---|---|
| `phase-4/gen-findings.py` | `tools/phase-4-gen/gen-findings.py` |
| `phase-4/post-v3-review-gemini-envelope.json` | `evidence/phase-4/post-v3-review-gemini-envelope.json` |
| `phase-4/post-v3-review-grok-envelope.json` | `evidence/phase-4/post-v3-review-grok-envelope.json` |
| `phase-4/post-v3-review-prompt.md` | `planning/phase-4/post-v3-review-prompt.md` |
| `phase-4/reconstruct-telemetry.py` | `tools/phase-4-gen/reconstruct-telemetry.py` |
| `phase-4/track-a-prompt.md` | `planning/phase-4/track-a-prompt.md` |
| `phase-4/track-b-prompt.md` | `planning/phase-4/track-b-prompt.md` |
| `phase-4/track-c-prompt.md` | `planning/phase-4/track-c-prompt.md` |
| `phase-4/track-execution-review-gemini-envelope.json` | `evidence/phase-4/track-execution-review-gemini-envelope.json` |
| `phase-4/track-execution-review-grok-envelope.json` | `evidence/phase-4/track-execution-review-grok-envelope.json` |
| `phase-4/track-execution-review-prompt.md` | `planning/phase-4/track-execution-review-prompt.md` |

## Historical-narrative exceptions

Spec §2.3 keeps historical narrative out of the rewrite: a sentence about what
was built, or a measurement of a past tree, is a record rather than a pointer.
Every surviving residual on the §2.1a surface is listed here — **0**
tokens after the wiki regeneration — so that a residual is an accounted-for
decision and never a missed sweep. `tests/test_layout_paths_chunk3.py` asserts
this list in both directions: no unlisted residual, and no listed row that is
no longer residual.

The previous wiki carried 49 residual tokens across `droid-wiki/by-the-numbers.md`
(33) and `droid-wiki/lore.md` (16). The lean wiki regeneration rewrote both
files with updated paths, leaving zero residuals. Line numbers are exact as of
the commit that lands this file. They are regenerable — see
`evidence/reviews/chunk3-nits/` — and the judge fails loudly rather than
quietly if they rot.

## Stale citations inside lock-frozen live code

One residual is not in a document at all. `tests/test_layout_paths.py` line 571
carries a comment citing the ledger at its pre-chunk-3 path,
`planning/phase-4.5/LEDGER.md`. That file is a judge, content-locked at
`cb00dfac…` against `tools/phase-1-locks/tests/test_layout_paths.py.lock.json`,
and the executor of this chunk may not touch it — not even to fix a comment
(spec §6, framework invariant #3).

It is called out separately because it is the first case where this file covers a
stale citation inside **live code** rather than inside a document or an evidence
byte. A future reader who greps the tests, finds the old path, and cannot find
the file needs to know that the staleness is intentional and where the ledger
went: `planning/phase-4.5/LEDGER.md` → `evidence/LEDGER.md`, moved by `git mv` in
chunk-D1-3 with zero content edits, because the ledger is append-only (§5, §21)
and a sprint-wide record does not belong inside one phase's planning directory.

## Scope

This file is a redirect map, not a to-do list. The 683 tokens it covers are
**deliberately** unedited, for the reasons at the top. Anyone tempted to "finish
the job" by sweeping them should read spec §5 first — and
`test_chunk3_redirect_only_surfaces_untouched` fails if those trees are swept,
which is the same hard stop expressed as a test.
