# CI gate — Phase 4.5 Track C flavor (a)

Companion doc for `.github/workflows/adversarial-sprint-ci.yml`.

## What this workflow does

For every PR opened/synchronised/reopened on the pilot repo, the
workflow:

1. Checks out the pilot repo + the framework repo (which contains
   the runner).
2. Verifies that the `droid` CLI is on the runner image (see §4
   below).
3. Runs `phase-3.2/evidence/local_backend.py` to produce a signed
   `EvidenceBundle` (HMAC-SHA256 over the bundle's canonical JSON,
   signed with `EVIDENCE_SIGNING_KEY`).
4. Runs `tools/orchestrate-review.py` in **bundle mode**
   (`--treatment`) so validators consume the bundle instead of
   re-running pytest. This is the **KI-2 preventive fix** — by
   construction, validators in this mode have NO `Execute` in
   `--enabled-tools` (see `tools/orchestrate-review.py:step3` +
   `--treatment`'s `args.evidence_source` derivation).
5. Reads `phase-4.5-ci/reviews/review-summary.json` to extract the
   gate decision.
6. Posts the gate decision as a **PR comment** AND a **PR status
   check named `adversarial-sprint-review/gate`**.

## Gate → status-check mapping

| Gate decision | Conclusion | Merge-protection default |
|---|---|---|
| `ACCEPT` | success | allowed |
| `ACCEPT-WITH-NITS` | success | allowed (operator should review nits) |
| `HUMAN_DECISION` | neutral | operator gates (configure as required) |
| `REJECT` | failure | **blocks merge** |
| `STOP` | failure | **blocks merge** |
| `ERROR` | failure | **blocks merge** |

To make this binding, configure the pilot repo's branch-protection
rule with the `adversarial-sprint-review/gate` status check marked
**Required**.

## KI-2 preventive fix (the point of flavor (a))

When the EvidenceBundle is the evidence source, validators in
`orchestrate-review.py` no longer need `Execute` to re-run pytest.
The workflow passes `--treatment` so the orchestrator strips
`Execute` from validators' `--enabled-tools`. This closes the
post-Phase 3.1 panel-split finding (Gemini ACCEPT + grok REJECT
against the same code) by removing the write vector inside the
validator's `--auto high` context, not by adding a post-hoc check.

Per PRD §11 / Track C: "the workflow is portable (not
Harness-specific)" — `.github/workflows/adversarial-sprint-ci.yml`
is GitHub-flavored but the underlying runner + backends are not.
Adapting to GitLab CI / Harness CI / CircleCI is a wrapper of the
same shape: trigger → checkout → run `local_backend.py` → run
`orchestrate-review.py --treatment` → gate decision → status check.

## Required secrets

| Secret | Required? | Notes |
|---|---|---|
| `EVIDENCE_SIGNING_KEY` | yes | HMAC-SHA256 key for the bundle. The consumer (`phase-3.2/evidence/consumer.py`) refuses bundles whose signature does not verify. Without this secret set, `local_backend.py` generates a random per-run key (logged) and the consumer cannot verify across processes — gate fails closed. |
| `DROID_TARBALL_URL` (org-level var, not secret) | no | Best-effort install path for droid CLI on GitHub-hosted runners. Self-hosted runners install droid differently. |
| Per-vendor API keys | depends | The validator sub-agents (`droid exec`) call external model providers. The PR template should set these per environment. |

## How the chunk spec gets into the runner

The workflow reads the chunk id from the PR title — convention is
`[chunk:<id>]` prefix. The runner is invoked WITH this chunk id;
the chunks-file convention lives in
`templates/overlay/sprint-loop-chunks-example.template.json`
(copied at install time to
`<PILOT_REPO>/.adversarial-sprint/chunks.json`).

If the PR title does not include `[chunk:<id>]`, the workflow
surfaces an `::error::` and the gate is **`STOP`** until the PR is
re-titled. This prevents auto-firing against unbounded scopes.

## Limitations / honest gaps (also in KNOWN-ISSUES.md)

1. **Droid CLI installation** is platform-specific. GitHub-hosted
   runners do not ship droid; the workflow's "Install droid CLI"
   step is **best-effort** (best-effort = non-blocking). Repos that
   want the workflow binding must use a self-hosted runner with
   droid installed at a known path. PRD §3 "v1 non-goal" → no
   "automatic adaptation to every runner image."
2. **Signing-key distribution** is the residual from the Phase 3.2
   signing-key fix (`ROADMAP-REVIEW.md §3.8`). The fix made the
   default key forgeable; this workflow expects explicit key
   distribution. Multi-repo CI handoff is a follow-on.
3. **`Agent.Shi + OpenTelemetry`** are listed in PRD §15 Act 3 as
   Phase 0 candidates but were NOT verified by Phase 0. This
   workflow does NOT claim them.
4. **Multi-repository orchestration** (PRD §3 v1 non-goal). The
   workflow runs ONE PR at a time; PRs across multiple repos do not
   converge.
5. **The runner's `--validation-backend=ci`** is the
   `--validation-backend=ci` stub from `tools/sprint_loop/backends.py`.
   This CI workflow does **NOT** use the runner's `--validation-backend`
   flag — it inlines the same `local_backend.py` + `orchestrate-review.py`
   flow directly because the runner is not available on the git host.
   The runner's MCP integration (PRD §11 Track C flavor b) is
   Backlog E.

## Operator checklist before merging the first PR with this workflow

- [ ] `EVIDENCE_SIGNING_KEY` is configured at the repo / org secret level.
- [ ] Required provider API keys are configured for the chosen
      validator panel (grok + gemini are the default).
- [ ] A self-hosted runner with `droid` installed is available, OR
      `DROID_TARBALL_URL` is configured to a valid upstream tarball.
- [ ] Branch protection requires the
      `adversarial-sprint-review/gate` status check.
- [ ] PR template instructs engineers to title PRs with the
      `[chunk:<id>]` convention so the workflow has a chunk spec.
