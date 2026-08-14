# FINDINGS — chunk-D1-3 (builder seat)

Findings raised by building chunk-D1-3 against
`planning/layout-refactor/CHUNK-3-SPEC.md`. Each one is a *problem statement*
for the planner/referee, not a spec edit — the builder seat does not amend the
spec (§13, §6). Every claim below is a measurement with the command behind it;
the harness that produces the numbers is `verify-chunk3.sh` in this directory
and its capture is `verify-chunk3.out`.

Interpreter for every count: `/private/tmp/asprint-venv/bin/python` (3.13.3).

## Summary of the build

| | |
|---|---|
| §2.1a surface residuals, before | **105** tokens across 15 files |
| §2.1a surface residuals, after | **49** tokens across 2 files, all enumerated as historical narrative |
| Mechanical rewrites applied | 57 across 13 files, plus 4 markdown link targets and 2 stale tails |
| Dead relative links on the surface | 4 → **0**, out of 47 links resolved |
| Files edited outside the citation rewrite | `README.md` Layout block (§2.5), `planning/PATH-REDIRECTS.md` (new), 2 generated `.cursor` mirrors (F7) |
| Renames | exactly 1: `planning/phase-4.5/LEDGER.md → evidence/LEDGER.md`, +0/-0 |

---

## F1 — `droid-wiki/by-the-numbers.md` is a measurement, so re-rooting it would falsify it

**Classification, not a defect.** 33 of the 49 surviving residuals live here.
Every row in that file is a count taken against one commit — files, lines, mean
line length, per directory. Re-rooting the directory name falsifies the number
printed beside it. The sharpest case:

```
| `phase-3.2/` | 21 | 8,681 | 413 |
```

There is no directory today that holds those 21 files. On the move commit, the
`phase-3.2/` silo fanned out to three roots — measured from `ee90061`'s own
rename records, **22** paths to `evidence/`, **9** to `planning/`, **3** to
`tools/` (34 paths, because the wiki's 21 was counted at an earlier commit; the
drift is itself the point). Rewriting the label to any one of the three
produces a row whose count was never true of the directory it now names. A
measurement is only true of the tree it was taken on. Spec §2.3 already carves
out historical narrative; this is the strongest instance of it, and the file is
listed in §2.1b as redirect-only for exactly this reason.

## F2 — `droid-wiki/lore.md` is a build record, and §2.3 names this case

The remaining 16 residuals are `Key files created:` lines — a record of what
each phase created **at the path it created it at**. Spec §2.3 names this case
verbatim ("Phase 1 built `phase-1/scripts/lock.py`") and rules it out of the
rewrite. Handled by enumeration in `planning/PATH-REDIRECTS.md`, not by editing.

## F3 — the residual matcher cannot see a markdown link *target*, only its label

The judge's `_BARE_PHASE` and my rewriter share a negative lookbehind
`(?<![/A-Za-z0-9_.\-])`, which is what stops an already-rooted `evidence/phase-3/`
from being rewritten twice. A markdown link target is written `](./phase-3.1/RESULTS.md)`
— the character before the token is `/`, so **the lookbehind excludes it**.

Consequence, and it is a §7 silent-green shape: rewriting only the visible label
leaves the href still 404ing on GitHub while **every token count reads clean**.
README carried four of these (`./phase-3.1/RESULTS.md`,
`./phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md` ×2, `./phase-1/KNOWN-ISSUES.md`).
The judge is not fooled — §3.1 asserts on link *resolution* rather than on token
counts, which is the right shape and caught this — but the blind spot is shared
by both the matcher and any future sweep tool derived from it. Handled here by a
separate `LINK_FIXES` pass in `rewrite-citations.py` (documented inline) and
measured by `dead-links.py` (§4.4): 47 links checked, 0 dead.

**For the planner:** any later chunk that greps for residual tokens as its exit
check inherits this hole. The exit check must resolve links, not count tokens.

## F4 — `tools/OPERATING-RULES.md:581-582` cited two files that never existed

The rule text cited `phase-4.5/prompts/phase-5-grok-validator.md` and
`…-gemini-validator.md`. Neither has ever existed: `git log` shows `6c315a2`
added them as `phase-5-grok-validator-spawn.md` / `-gemini-validator-spawn.md`,
so the citation was stale **before** the move.

Re-rooting alone would have produced `planning/phase-4.5/prompts/phase-5-grok-validator.md`
— a path that is correctly rooted and still 404s. That is the silent-green shape
§7 forbids: it *looks* swept, and a token-counting exit check would agree. I
re-rooted **and** corrected the tails, with both referents verified on disk, and
recorded the reasoning in `rewrite-citations.py`'s `TAIL_FIXES` comment rather
than leaving it to the diff.

**For the planner:** the tail correction is arguably outside a
"citation-re-rooting" chunk. I judged that landing a knowingly-dead re-rooted
path is worse than the scope widening, and flag it here for a ruling.

## F5 — two cited paths resolve nowhere at all, in either taxonomy

`phase-3.2/evidence/single-round-report.py` and `phase-2/brief-v2.md` are cited
in the two narrative files and were **never tracked** (`git log --all -- <path>`
is empty; they were scratch files at the time of writing). No redirect can be
correct for them, because there is no destination. They are covered by
enumeration in the narrative exception list, not by a table row — and the
prefix-table generator would have refused to emit a row it could not probe on
disk (F6).

## F6 — the generator refuses rather than absorbs, so the judge's assertion is not vacuous

`test_chunk3_every_residual_token_is_accounted_for` asserts that every residual
appears in the PATH-REDIRECTS exception list. A generator that simply enumerated
whatever residuals it found would satisfy that test **by construction** — a
future half-swept sweep would be papered over by re-running the generator, and
the judge would still go green.

`gen-path-redirects.py` therefore enumerates residuals **only** in the two files
named in its `NARRATIVE` dict (the classification is the human judgment; only
the line numbers are mechanical) and exits 1 writing nothing if a residual turns
up anywhere else. Same discipline in `prefix_map()`: it raises rather than
emitting a row for a non-segment-preserving rename or a destination that does
not resolve on disk. The prefix table is derived from the move commit's own
rename records (`git show --name-status --find-renames ee90061`), so it cannot
disagree with what actually moved.

## F7 — `.cursor/rules/*.mdc` are outside the §2.1a allowlist but pinned to it by an existing test

§2.1a allowlists `skills/adversarial-sprint/SKILL.md` (4 tokens) and
`skills/sprint-invocation/SKILL.md` (1 token). It does not mention
`.cursor/rules/adversarial-sprint.mdc` / `sprint-invocation.mdc` — which are
**generated mirrors of those exact files**, and which
`tests/test_sprint_loop.py:1698` (`…cursor_mdc_body_matches_canonical_g6`) pins
body-for-body to the SKILL.md canon.

Demonstrated mechanically rather than argued: stashing just the `.cursor/`
changes and re-running that test fails with
`G-6: committed .mdc body drifted from canonical body`; restoring them passes.
So editing an allowlisted file **requires** committing the generated mirror, and
a builder who honoured the allowlist literally would have shipped a red suite.

Regenerated through the sanctioned script (`./tools/install-skill.sh cursor`,
§14) and proved byte-identical to what is on disk, so the mirrors are generator
output and not hand-edits. The harness re-checks that idempotence.

**For the planner:** §2.1a should name generated mirrors as collateral of their
canonical source, or the spec's allowlist and the suite disagree.

## F8 — the LEDGER's one live-code referrer is inside a locked judge

`tests/test_layout_paths.py:571` carries a comment citing the ledger at its
pre-chunk-3 path. That file is a judge, content-locked at `cb00dfac…` against
`tools/phase-1-locks/tests/test_layout_paths.py.lock.json`, and this seat may
not touch it — not even to fix a comment (§6, framework invariant #3). Left
stale deliberately and called out in `planning/PATH-REDIRECTS.md` under
"Stale citations inside lock-frozen live code", because it is the first case
where the redirect map covers live code rather than a document or an evidence
byte.

## F9 — chunk-2a's recorded `KNOWN 1-FAILURE` is machine-dependent, not commit-dependent

The chunk-2a close records:

> `KNOWN 1-FAILURE: test_chunk2a_emitted_envelope_paths_resolve[reconstruct-telemetry]`
> fires its vacuity guard — all emitted paths already exist in the SoR … Not a judge defect.

At this commit on this machine, **all 23 chunk-2a tests pass**, including all
three parametrizations of that test. The reason is not a fix: the guard compares
emitted `envelope_path` values against the rows already in
`tools/telemetry/runs.jsonl`, and **that file does not exist on this machine at
all** (untracked; `tools/telemetry/` is absent). With no SoR, every emitted value
counts as newly generated, the guard is satisfied, and the test asserts on real
resolution.

So the same commit yields ACCEPT here and a fired vacuity guard on a machine
whose SoR happens to be saturated — and running the scripts under test is itself
what saturates it. A judge whose verdict depends on untracked local state is not
reproducible evidence (§7, §9), and the carried "known failure" cannot be
reproduced or fixed by this seat.

**For the planner:** either commit a fixture SoR the guard reads, or scope the
guard to rows the probe itself emitted in-process.

## F10 — `tools/plan-lint.py` with no argument is rc=2, so §4.7 as literally written fails

§4.7 reads "`tools/plan-lint.py` rc=0". The tool takes a required positional
`plan`; bare invocation is an argparse usage error (rc=2) that reads like a chunk
failure but is a missing argument. The harness lints the two documents earlier
chunks used — `planning/layout-refactor/PLAN.md` and this chunk's
`CHUNK-3-SPEC.md` — and reports rc per file.

## F11 — measurement hazard: a second `-q` silently deletes pytest's count line

`pytest.ini` already sets `addopts = -ra --strict-markers -q`. Adding `-q` on the
command line raises quiet level to 2, which **suppresses the `N passed, M failed`
summary line entirely** — `pytest -q | tail -1` returns the last `FAILED` row and
no counts at all. A builder reporting counts from that output has nothing to
report and is one step from hand-writing a number, which is precisely the §9
failure mode.

Recorded because chunk-2a §2.4 K2 already burned one bad evidence row on an
interpreter mix-up; this is the same class of hazard one layer down. The harness
takes its counts from `--junit-xml` instead, which is an artifact rather than a
console line (§7).

## F12 — §5 hard stop respected

§4.2's residuals are only historical narrative (F1, F2), so per §5 the chunk
**stops**: 683 tokens across `planning/layout-refactor/**` (265),
`planning/phase-N/**` (418, 357 after the LEDGER moved out) and committed
evidence are deliberately unedited, and the delta is carried by
`planning/PATH-REDIRECTS.md` instead.
`test_chunk3_redirect_only_surfaces_untouched` is that hard stop expressed as a
test, and it passes — which is the useful shape: sweeping those trees "to finish
the job" would now redden the suite.
