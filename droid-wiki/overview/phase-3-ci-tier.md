# Phase 3 — the CI/CD evidence tier (first live test)

**Phase 3 proved the loop end to end and stopped at the human merge gate. What
happened next is the first real-world test of the idea behind Phase 3.2: push
the merged slice through an actual CI/CD pipeline (Harness) and see whether the
deterministic evidence tier — tests, lint, security scans — catches things the
model panel does not, and what it costs to trust it.**

This is a companion to `phase-3-execution-slice.md`. That page ends at "the
slice is presented, not merged." This one covers landing it: the pilot's
`feat/user-profile` → `fix/ci-hygiene` branch run through Harness STO, the
findings, their triage, and the design lessons that feed Phase 3.2.

## What the pipeline surfaced

Three scanners ran against the pilot branch. Every finding was **pre-existing
debt, not introduced by the Phase 3 `/profile` work** — the CI tier simply scans
the whole tree/history, so it sees what the loop's diff-scoped review never
looked at.

| scanner | finding | class | disposition |
|---|---|---|---|
| gitleaks | `SPLIT_CLIENT_KEY` in `static/js/split-client.js` + `docs/TECHSUMMARY.md` (`generic-api-key`, Medium) | **false positive** | scoped `.gitleaks.toml` allowlist |
| ruff / black | `api/llms_txt.py` would reformat | style debt | `black` format |
| osv-scanner | `click==8.1.7` → PYSEC-2026-2132 (command injection in `click.edit()`, High) | **real, low exploitability** | bump to `8.3.3` |

The texture is the point: **one false positive, one real-but-negligible CVE, one
style nit.** The security tier's value is not that it is always right — it is that
it *surfaces candidates* for judgment. Two of the three needed a human/model call
the scanner could not make on its own.

### The false positive (gitleaks)

`SPLIT_CLIENT_KEY` is a Split.io **client-side** SDK key — public by design; it
ships in the browser bundle and only authorizes flag evaluation for a traffic
key. Gitleaks' `generic-api-key` rule is a pure entropy heuristic: it saw a
high-entropy string assigned to a `*_KEY` name and fired. The genuinely
sensitive key (`SPLIT_API_KEY`, server-side) is env-loaded and never committed.
Fix: a narrowly-scoped allowlist keyed to the `SPLIT_CLIENT_KEY` line and its two
files, so any *other* secret in those files still trips.

### The real one (osv-scanner)

`click 8.1.7` carries a command-injection vuln in `click.edit()` (fixed in
8.3.3). Honest exploitability read: `click` is present as Flask's CLI dependency
and the app never calls `click.edit()`, so real exposure is ~nil — but the bump
is the clean fix and Flask 3.1 only requires `click>=8.1.3`. Verified after the
bump: `pip-audit` clean, full suite still green.

## "An account is not evidence" — applied to CI

The most instructive moment was a **stale cache**. After the `click` bump was
pushed, the osv step still reported the old High finding. It was not a
regression or an expired exception: the pipeline had replayed a cached result.
The tell was unambiguous — an **identical `jobId`** and **microsecond-identical
timing** (`2.176535ms elapsed`) across two supposedly separate runs. A real
re-scan cannot reproduce timings to the microsecond.

We only trusted the fix after re-deriving from the source of truth:
`git show origin/<branch>:requirements.txt` piped to a fresh `pip-audit`, which
reported no vulnerabilities. The pipeline's displayed verdict was an *account*;
the audit of the actual committed file was *evidence*. This is the same
discipline the runtime loop applies to executor and validator self-reports — and
it turns out CI needs it too. A one-line cache-busting commit (new SHA) forced a
real re-scan, which went green.

## Design lessons for Phase 3.2

The whole point of running this was to learn what the CI-externalized evidence
tier must get right. Three rules fell out, all recorded in the Phase 3.2
explorer brief:

- **Gate on NEW findings vs a baseline, not total history.** Gitleaks failed the
  build on `fail_on_severity: low` against the full 89-commit history, yet its
  own report said `newIssuesCount: 0` — the finding was legacy debt, not new in
  this change. If the gate keys on total history, every run trips on old debt and
  the "did *this change* introduce a problem?" signal drowns.
- **The scanner is not an oracle.** It needs a curated allowlist and its verdicts
  feed judgment; they do not end it. False positives are a cost of the tier, not
  a defect to hide.
- **Diff-scoped and history-scoped scans are both valid — at their scope.** The
  orchestrator's pre-push scan was diff-scoped (our new commits — correctly found
  nothing); gitleaks was full-history (found legacy debt). The design must be
  explicit about which scope gates the merge (diff/new) and which is a standing
  baseline report (history).

And the standing rule that frames all of it: **CI augments, it does not replace,
the model panel.** Tests and scans are necessary-not-sufficient; the
cross-family review of the diff (spec, semantics, over-exposure) still stands.

## Outcome

The three fixes landed on the pilot's `fix/ci-hygiene` branch, each verified
locally before push, and the branch went fully green (gitleaks / ruff / black /
osv). It was then merged to pilot `main` (merge commit `d120c971`): **103 passed,
0 vulnerabilities.** This is early, single-run evidence for the Phase 3.2 thesis —
that routing deterministic evidence through CI adds coverage the panel lacks. The
formal token cost claim (does it also make the loop *cheaper*?) is the Phase 3.2
A/B experiment, not this run.
