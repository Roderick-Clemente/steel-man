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

## Phase 2 — the planning slice on itself

Phase 2 pushed the loop one step earlier: can the panel review a *plan*
before any code exists? On one real slice (a read-only `GET /profile`
page for the pilot bank), two single-blind cross-family stages (brief,
then plan) each ran Grok + Gemini. The brief came back
ACCEPT-WITH-NITS / ACCEPT and was reconciled; the pinned planner
(`claude-opus-5`) drafted a plan hashed to `sha256:72eccff5…`, and both
families **APPROVED it with zero blocking findings** — a clean null per
PRD §13.

The calibration divergence inverted Phase 1's pattern: on specification
and planning artifacts, Grok was the finder and Gemini the confirmer —
the mirror of Phase 1, where Gemini was the security finder on hook
code. That task-conditioned divergence is exactly the
`first_seen_in_panel_position` signal Phase 6 will accumulate.

## Phase 3 — end-to-end execution

Three chunks built through the full loop, all cross-family ACCEPT, 99
tests passing. The mechanism works. But 3 of 4 exit criteria were
missed: no replayable demo, no baseline comparison, no local PR
creation. Orchestration was manual (run by hand, not scripted). The
retry/re-plan path was never exercised (zero rejections — a valid clean
null per §13). Telemetry rows were reconstructable from 13 committed
envelopes via `gen-telemetry.py`.

## Phase 3.1 — the degraded spike

Deliberately violated invariant #1 (same-family test-author + executor)
to measure whether cross-family validation alone compensates for lost
test-independence. Result: **panel-dependent**. The deterministic
standalone gate caught the bias every time. The cross-family panel
split — Grok caught the encoded bias, Gemini dismissed the identical
failure. Cost 2.38x control (mostly from the retry cycle). Fed back
into PRD §17.6 as a binding rule. See
[Phase 3.1 degraded spike](phase-3.1-degraded-spike.md).

## Phase 3.2 — the evidence provider

Externalized the deterministic evidence tier into a compact signed
`EvidenceBundle` that validators consume instead of re-running pytest.
Local backend as default (zero CI); Harness as an interchangeable
backend behind the same interface. The orchestration script
(`orchestrate-review.py`) ran with partial success — 12 telemetry rows,
10 from orchestrated runs with real decisions (ACCEPT, REJECT,
ACCEPT-WITH-NITS, ERROR, UNKNOWN). H-CI experiment designed but not
yet run. See [Phase 3.2 evidence provider](phase-3.2-evidence-provider.md).

## Phase 4 — the roadmap review (hardening on itself)

The roadmap review was the framework hardening itself ahead of
schedule. A single-family (Claude) audit of all prior phases was sent
to Grok and Gemini for cross-family panel review — the same treatment
every artifact gets. **v1 was REJECTED by both reviewers** for three
material factual errors: Phase 0.5 was declared "never built" (it was
done), orchestration was declared "never ran" (it did, 10 rows with
real decisions), and proposed rule §12 conflicted with PRD §13's
null-result rule. The irony is the point: a single-family review is
not independence, and the panel caught exactly the blind spot the
framework exists to prevent.

v2 corrected all errors and returned APPROVE-WITH-NITS from both
reviewers. v3 folded in the nits: three parallel tracks (cheap
closures, orchestration→H-CI→H3, demo honesty), proposed operating
rules (§9–§17, to be landed in `tools/OPERATING-RULES.md`), and an
honest re-sequencing. See
[The roadmap review](roadmap-review.md).

The review itself was recognized as **Phase 4 (Hardening + roadmap
review)** — a consolidation phase that arrived ahead of schedule
because the foundation needed attention before extending. All
subsequent phases were renumbered: old Phase 4 → Phase 5 (Generalize),
old Phase 5 → Phase 6 (Hardening settling pass), old Phase 6 → Phase 7
(Human compression).

### Phase 4 execution

Three parallel tracks executed the review's plan:

- **Track A** ran `valid-red.py` against the Phase 1 locked test
  (closing the "never run" gap), created 4 invalid-RED fixtures, found
  and fixed an ANSI stripping bug in the classifier, reconstructed 34
  telemetry rows from committed envelopes, and created
  `findings.jsonl` with 71 findings from 9 review rounds.
- **Track B** hardened the orchestrator (adapter shim, stray-write
  baseline, transient retry, deterministic multi-run), ran the H-CI
  experiment (27.8% mean token saving, quality holds, fairness rule
  holds), and ran H3 validation (gpt-5.4-mini implemented from
  un-hinted spec, GREEN on first attempt, cross-family ACCEPT).
- **Track C** packaged the demo with strict honesty bounds: Act 1
  (manual baseline), Act 2 (command-orchestrated, no Mission cosplay,
  "close the laptop" dropped), Act 3 (Phase-0-verified controls only).

The track execution was itself cross-family reviewed. Grok returned
REJECT (7 findings, 2 HIGH: demo claimed Track B unfinished after it
shipped, telemetry reconstruction not actually run). Gemini returned
APPROVE (0 findings). The calibration divergence continued: Grok
catches honesty violations, Gemini gives clean passes. All HIGH
findings were fixed.

Phase 4 closed with all exit criteria met: orchestration stabilized,
H-CI and H3 results recorded, demo packaged, telemetry SoR populated,
and §9–§17 operating rules landed in `tools/OPERATING-RULES.md`.
