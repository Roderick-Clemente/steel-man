# The meta-narrative — building the loop with itself

**The harness used as its own test target surfaces two kinds of bugs.** The
ones in the code being shipped, and the ones in the runtime shipping the
code. Both land on the same §13 efficacy surface and both deserve to be
tracked.

Phase 1 of this project gave us the first six-reviewer-session case study
of that loop running on itself. The slice is small (17 files, +757 lines),
the case study is concrete enough that the headline sensors become
observable, and the headline it offers is the same headline from
[`findings/fake-pass.md`](../findings/fake-pass.md) at Phase 0.5: **the
verifier itself must be from a family that did not author the work**.

## Phase 1 in three rounds of two reviewers

The pilot repository was `~/work/quantum-bank--llms-txt-pilot`; the
defect under test was a doubled `charset= utf-8` token in the
`Content-Type` header returned by Flask on QuantumBank's `/llms.txt`,
because the endpoint set `mimetype="text/plain"` and Werkzeug appended
`charset=utf-8` twice. The fix is `mimetype="text/plain"` is fine — Werkzeug
only doubles the charset if the param is given in `Content-Type`-style
already. The locked test asserts exactly one `charset=` token in
`request.headers["Content-Type"]`.

### Round 1 — first review pair

| reviewer | family | decision | duration | num_turns | tokens (in/out/think) | key takeaway |
|---|---|---|---|---|---|---|
| Grok (`grok-4.5`) | xAI | ACCEPT (7 minors/nits) | ~380s | 40 | 210623 / 19065 / 10755 | test-quality nit: "real Werkzeug behavior; would not pass no-op/404" |
| Gemini (`gemini-3.1-pro-preview`) | google | REJECT-blocked-by-tooling | ~177s | 26 | 698878 / 10718 / 2937 | refused to render judgment — Execute tool not in `--enabled-tools` |

Grok's seven findings were all on the read of the code: an unused
`accepted_assertion` load, a missing-invalid-signature gap,
fail-open-on-malformed-manifest, dead `SHELL_WRITE_OPERATORS` surface,
brittle `conftest.py` regex, plus two quality nits (Phase 0.5 hand-off
cleanliness and the test-quality confirmation above).

Gemini, on the other hand, never read the code. Its single BLOCKING
finding was the tooling-blocker refusal itself — the
`--enabled-tools Read,Glob,Grep,LS` allowlist denied `Execute`, so
`git show origin/factory/phase-1-test-evidence:<path>` could not be
called. That refusal is itself a concrete surface: it tells us the
`Read,Glob,Grep,LS,Execute` allowlist is the right default for
cross-family reviews. The prompt subsequently grew a v2 explicitly
permitting read-only Executables (see `/tmp/phase-1-review-prompt-gemini.md`).

### Round 2 — post-fix

After applying the first round of fixes — manifest protection, multi-step
hook gating, valid-red signature enrichment, ledger RED-step row — four
commits landed on `factory/phase-1-test-evidence`:

| SHA | subject |
|---|---|
| `5f503fd` | hook: lock manifest protection + tokenized Execute guard |
| `dc983f7` | verify-green: accepted_assertion re-check + fail-closed |
| `6fe440c` | valid-red: 13 → 15 signatures per PRD §5.4 |
| `d58c46f` | RUN-LEDGER: capture RED-step evidence |

The cross-family pair looked at the new tip and reported:

| reviewer | family | decision | duration | num_turns | tokens (in/out/think) | key takeaway |
|---|---|---|---|---|---|---|
| Grok (`grok-4.5`) | xAI | REJECT (BLOCKING: `python3` inline-eval bypass) | 229s | 10 | 37570 / 12417 / 9851 | caught a regression the round-1 fix had introduced |
| Gemini (`gemini-3.1-pro-preview`) | google | REJECT (3 hook bypasses) | 265s | 12 | 576120 / 15639 / 3344 | glob short-circuit on basename prefilter; same `python3` finding; `MultiEdit` missing from matcher |

Grok's BLOCKING finding is the case study's most striking row. The
round-1 fix had added `python3` and `python` to `READ_ONLY_HEADS`
thinking to widen the allowlist; it actually opened an inline-eval
bypass (`python3 -c "open('locked','w').write(...)"`). Grok caught it
in 10 turns, 229 seconds. The round also produced a wrenching
realisation: **a verifier's verifier must be a different family than
the verifier**. The harness that runs `python3 scripts/` cannot be the
verifier for whether the harness should be allowed to run `python3 -c`.

Gemini caught three hook-layer defects in the same round too: the glob
short-circuit (the basename prefilter had been masking the glob check
when the basename wasn't in the segment), the same `python3` finding,
and an omission of `MultiEdit` from the matcher. The three findings
were orthogonal — separate lookups, distinct fixes.

### Round 3 — confirmatory

After applying the round-2 fixes — `python3`/`python` dropped from
`READ_ONLY_HEADS`, structural glob heuristic with cwd-anchored dirname
check, `MultiEdit` added to matcher, `rm -rf <dir-of-locked>` closed:

| SHA | subject |
|---|---|
| `9940d40` | hook: round-2 review fixes — MultiEdit + token-first guard + structural glob heuristic |

| reviewer | family | decision | duration | num_turns | tokens | key takeaway |
|---|---|---|---|---|---|---|
| Grok (`grok-4.5`) | xAI | ACCEPT-WITH-NITS | 215s | 13 | 46623 / 11599 / 8410 | 2 majors (ledger-completeness), 2 minors (case/regex), 2 nits |
| Gemini (`gemini-3.1-pro-preview`) | google | ACCEPT | ~265s | 12 | (cached engram) | only nit on hook: structurally sound |

Net: ACCEPT-WITH-NITS. Both reviewers sign off. The remaining 4
findings are documentation-completeness and code-quality polish,
queued for Phase 1.1 or folded into the merge rationale.

## Tokens spent well

The full panel-side footprint across the three rounds:

- **Grok sessions:** 3 sessions, ~695k input tokens, ~62k output tokens.
- **Gemini sessions:** 3 sessions, ~1.7M input tokens, ~36k output tokens.
- **Total:** ~3.4M tokens across the panel — most of which is
  `cache_read`, the runs re-hitting the same slice tree for each round.

Compare with two human reviewers spending an hour each on a 16-file
diff: same-or-fewer findings, much higher dollar cost in People-time,
and lower reproducibility. The lever is reproducibility — the panel
under `--enabled-tools` and `--model <id>` is reproducible to the byte.

## Cross-family divergence is the §13 efficacy signal

The two reviewers didn't catch the same defects:

| defect family | Grok caught | Gemini caught |
|---|---|---|
| Hook security bypass (glob short-circuit, `MultiEdit` missing) | no | yes (×3) |
| Valid-red signature gap (service unavailable / empty selection) | yes | no |
| Case-sensitivity disagreement between red and green checks | yes | no |
| Ledger-completeness (recorded RED not mechanically re-run via script) | yes | no |
| Hook lock-manifest unprotected (round-1 finding) | no | yes |

Either family alone misses 3 of 5. The adversarial sprint's job is to
bring each family's blind spot into the surface — that's the
calibration-divergence metric captured as `first_seen_in_panel_position`
in the telemetry schema (`telemetry/SCHEMA.md`).

## What the loop is doing when it serves itself

This is the lesson we want to hold onto: a build-review-find loop used
to build the loop's own runtime surfaces both kinds of bugs. Phase 1
case study gave us:

1. **Test-quality rubric validation.** The locked test passes six of
   the seven items in [method/sprint-template.md test-quality rubric](../method/sprint-template.md).
2. **Process-bug-as-code-bug.** Round 2's over-deny regression showed
   that even a verifier's verifier must be from a different family. The
   fix was structural, not discipline.
3. **Cross-family panel as anisotropy check.** The panel surfaces
   security, correctness, and rubric-compliance defects no single
   family catches. Calibration divergence is the lever.
4. **Cost law.** ~3.4M tokens and ~30 minutes of wall-clock for three
   rounds of two reviewers is a price worth paying for the level of
   review it produces. The marginal cost per extra reviewer is the
   strongest efficacy sensor.
