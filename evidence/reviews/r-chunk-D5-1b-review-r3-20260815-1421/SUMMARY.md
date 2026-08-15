# chunk-D5-1b review — audit-script-only (single reviewer)

Commits under review: `4422ff0 chunk-D5-1b: spec/prompt/convention updates for sprint-keyed outputs` + `07a8c6c chunk-D5-1b: sprint-keyed wrapper + tightened convention`
Branch: `factory/d5-tooling-docs-1b` (on top of `c8161bd`)

Predecessor: chunk-D5-1 squash-merged into origin/main via PR; chunk-D5-1a (self-anchor) at `77a316c`. chunk-D5-1b is a follow-on that introduces sprint-keyed output routing.

Per `planning/evidence-hygiene/PLAN.md §2` row 1, audit-script-only tier, 1 reviewer.
Default model `kimi-k3` (moonshot / kimi-family, per `tools/sprint_loop/config.py:59`).

## Round 1 — single reviewer

| Validator   | Family                       | Verdict           | Envelope SHA-256 (first-27 hex) |
|-------------|------------------------------|-------------------|---------------------------------|
| kimi-k3     | moonshot / kimi-family       | ACCEPT-WITH-NITS  | `5f1c9d56606f111e808bf13814d`   |

(Full 64-hex: `5f1c9d56606f111e808bf13814d43f75de736ee9a9495744f3c6e4f1416016ff`)

Run: 17 turns, 448281 ms wall-clock. Stderr-log empty on success per review-bundle §4.

## §3 floor-check verdicts (re-derived by reviewer)

All seven exit criteria PASS at the reviewer level:

| §3 check | Outcome | One-line evidence |
|---|---|---|
| 1. review-bundle.md §1 split + exemplars | PASS | §1.Historical at line 12, §1.Current at line 24; both exemplar citations 2× each (≥ 2 floor). |
| 2a. exec bit | PASS | `test -x tools/run-review.sh` exit 0. |
| 2b–2e. refusal cases (no-args, each-empty-arg) | PASS | All four bash calls exit 2 with the §2.2 refusal message. |
| 2f. mkdir failure | PASS | `mkdir -p` on `sprint/.d5v-blocker/.d5v-blocker/sub` triggers ENOTDIR → exit 3. |
| 2g. round-derive loop | PASS | Pre-seeded round1 + round3 under test sprint; live fire occupies round2 (lowest vacant). |
| 2h. DROID_MODEL_ID propagation | PASS | Only propagation at line 35; no re-check in the wrapper (`run-with-model.sh` owns §17.1 gate). |
| 2i. no cwd writes | PASS | Both redirects path through `${SPRINT_DIR}/${ROUND}/`; `$PWD` only used as `--cwd` for the droid session. |
| 2j. cwd-isolation (live fire) | PASS | From `/tmp/d5-1b-cwd-verify`: cwd empty post-run; `evidence/reviews/<sprint>/round1/{envelope,stderr-log}` produced. |
| 3. README section | PASS | `## When to use which review tool` at line 269, all four scripts listed. |
| 4. PLAN.md §2 3-tier table | PASS | Tier rows verbatim, all three precedent SHAs present. |
| 5. pytest | PASS | 241 passed, 3 skipped in 2.90s. |
| 6. audits | PASS | `wiki-link-audit.py` clean; `plan-lint.py` PASS. |
| 7. LOC caps | PASS | `tools/run-review.sh` 22 code-only non-blank ≤ 30; `tools/conventions/review-bundle.md` 55 non-blank ≤ 55. |

## Findings

5 nits, none blocking. All five queued as future housekeeping per chunk-D4-1 precedent (ACCEPT-WITH-NITS nits → roadmap).

1. **spec §3 item 1 says "§5 (Exemplars)"** but Exemplars is at §6 in `review-bundle.md` since chunk-D5-1. (Section-number drift since the convention doc's `## 5. Model family taxonomy` is currently between Header and Exemplars.) Future spec revision cites §6.
2. **commit body `07a8c6c` claims "both exemplar citations still appear 4 times each"** — actual grep count is 2 per artifact (still satisfies the §3 ≥ 2 floor). Future executor should state their measured count, not a descriptive number.
3. **round10-exhaustion gap (latent, outside §3 contract).** If `round1..round10` already exist under a sprint, the loop's `ROUND` is never reassigned (initial value `1`); mkdir creates a dir literally named `1/` and writes there. NOT a contract failure — `## §3 item 2` as written passes. Future hardening recommended: exit 3 on exhaustion.
4. **spec §2.2 vs `tools/run-review.sh:20` derivation divergence (benign).** Spec shows `REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`. Code uses `REPO_ROOT="$(dirname "$SCRIPT_DIR")"` unconditionally. Both produce the same repo root while the script lives at `tools/run-review.sh`; the code's version is arguably more robust (no git dependency). Reconcile in future spec revision.
5. **process note (verification tooling).** Pytest's final-count line (`241 passed, 3 skipped ...`) was missing from stdout when piped. Future audit-script-only verifiers should redirect pytest to a file before grepping or counting.

## Verdict

**ACCEPT-WITH-NITS.** §3 floor checks all PASS on disk and in git. Cross-family separation holds (anthropic implementer vs moonshot/kimi reviewer). All findings are nits only, queued for future housekeeping per chunk-D4-1's precedent of ACCEPT-WITH-NITS nits being roadmap material rather than blocking.

Per `planning/evidence-hygiene/PLAN.md §2` row 1 lighter-gating, the chunk can be merged to `main` after operator reviews this SUMMARY.

## Verifier residue (untracked artifacts left on disk)

The reviewer created test artifacts during floor-check verification (latent defect probes + live cwd-isolation fire). All untracked, none staged:

- `evidence/reviews/chunk-d5-1b-kimi-cwd-verify/round1/` — live cwd-isolation fire test.
- `evidence/reviews/chunk-d5-1b-kimi-round-derive/round{1,3}/` — round-derive loop sequencing test.
- `evidence/reviews/chunk-d5-1b-verifier-round10/round1..round10/`, `evidence/reviews/chunk-d5-1b-verifier-round10/1/` — round10-exhaustion latent-defect probe.
- `evidence/reviews/r-chunk-D5-1b-review-20260815-1142/round1/` (0-byte envelope) — earlier SIGTERM'd fire that proved path-routing even if not the model.

Operator may prune when convenient.
