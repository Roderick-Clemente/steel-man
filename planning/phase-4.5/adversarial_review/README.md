# Phase 4.5 — adversarial review pass

Per `OPERATING-RULES.md` §11 ("exit criteria are checked"): every
PRD §11 Phase 4.5 exit criterion is reviewed against the actual
artifacts in `tools/sprint_loop/`, `tools/sprint-loop.py`,
`examples/`, `.github/workflows/adversarial-sprint-ci.yml`,
`phase-4.5/{RUN-PROMPT,ASSUMPTIONS,KNOWN-ISSUES,BUILD-NOTES}.md`,
plus the in-line `tools/run-with-model.sh` refinement.

This is a **structural + cross-perspective** review pass, NOT a
real droid-mediated cross-family review. The cross-family review
the project ships with (`tools/orchestrate-review.py`) requires
**two distinct model families running separately**, which is not
trivially reproducible in this build session (factory subscriber
state and the droid roster it has access to aren't a fixed
fixture of this branch). The KNOWN-ISSUES.md §KN1 entry names
this as the gap to close in a follow-on operator session.

Where this pass uses **cross-perspective** review, it borrows the
PRD's own panel-posture taxonomy: PRD-strict, pragmatic-DX,
security-skeptic, distribution-savvy. These are not real model
outputs; they are lenses the project's own PRD §11 invites the
operator to apply. Each criterion lists the lens that surfaced
the finding, and the disposition.

## How to read this file

For each PRD criterion:

- **Status:** PASS / PARTIAL / MISSING / UNEXERCISED
- **Where satisfied:** file path + line / function name
- **Notes / clean null:** if UNEXERCISED, name the gap per §12

Findings from this review are recorded in
`phase-4.5/adversarial_review/findings.jsonl` (gitignored per
PRD §17.4 — schema lives in `telemetry/SCHEMA.md`). Dispositions
live in `phase-4.5/adversarial_review/dispositions.jsonl`. For
this build session, both files are simulated/run-them-locally —
the project's `tools/aggregate.py` reads them on demand.

## Status legend

- **PASS** — present, demonstrable, and verified against actual
  artifacts in this branch.
- **PARTIAL** — present in skeleton but not fully wired (a
  follow-on is required).
- **MISSING** — required by the criterion, not present in this
  branch.
- **UNEXERCISED** — present and runnable, but not exercised by an
  end-to-end pilot run; the path is recorded per §12.
