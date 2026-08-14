# Phase 3.2 — RUN PROMPT (ready-to-run handoff)

You are the **orchestrator/executor** for Phase 3.2: externalizing the
deterministic evidence tier so the model panel consumes a compact structured
result instead of re-running pytest in-session. The design is in
`phase-3.2/SPIKE.md` and the sequencing/first-lens call is in
`phase-3.2/RECOMMENDATION.md` — **read both first.** This file is the execution
recipe. The plan is human-approved (commit `5ea085a`); you may build now.

Build **strictly from the committed spec.** Where the spec is silent, make the
smallest reasonable choice, follow existing repo conventions, and **log the
decision** (see "Assumptions & gaps log" below). Do not assume undocumented
context; if something is genuinely undecidable from the docs, record it as a
blocker rather than inventing policy.

## Scope of THIS run (the zero-CI local milestone)

Build-order steps 1–3 + 5 from `SPIKE.md` §9 — the **local** evidence provider,
with **no CI and no Harness**:

1. **Freeze the `EvidenceBundle` schema** (`bundle_schema_version` v1) exactly as
   specified in `SPIKE.md` §2.1.
2. **Local backend adapter** (`SPIKE.md` §2.2): runs pytest, reuses
   `phase-1/scripts/verify-green.py` for the locked-hash check (emit
   `locked_test_sha_observed`), runs the security scanner, normalizes to the
   bundle, signs it.
3. **Wire a validator + the orchestrator to consume the bundle** in local mode
   (`SPIKE.md` §5 seat allocation): the validator reads the bundle instead of
   re-running pytest; the orchestrator does the §4.1 locked-sha cross-check.
4. **Instrument the token accounting** (`SPIKE.md` §3.2 fairness rule): record
   both the in-session raw-test-output tokens (the thing being replaced) and the
   bundle-read tokens (the replacement), so the fairness ceiling is measurable.

**Explicitly OUT of scope for this run** (do not build): the Harness backend
(`SPIKE.md` §2.3 flavor b), the full N-run H-CI experiment (`SPIKE.md` §3), the
3.3 visual tier, and the framework-repo dogfood target (`SPIKE.md` §7). This run
produces the *provider*; the experiment that uses it is the follow-on.

## The one variable (for the eventual experiment, not this build)

When H-CI is later run, the **only** changed variable vs the Phase 3 control is
the **evidence source** (in-session pytest → local bundle). Same models, prompts,
diff, chunk structure, locked tests, acceptance gate. Do not change anything else;
in particular this is **not** the degraded-models variable (that was 3.1).

## Open questions — recommended defaults (human may override)

These are the planner's recommendations from `RECOMMENDATION.md`; treat as
defaults and flag if you deviate:

- **Local scanner:** Semgrep **and** Bandit (both). Whichever run, the §4.4
  rules bind: gate on **new-vs-baseline** (not total history) and carry a
  **curated allowlist** scoped to specific known-public values (the
  gitleaks/`SPLIT_CLIENT_KEY` false-fail lesson).
- **Executor/coder MCP grant:** **no** — hidden tests must stay out of its
  context. Only validators + orchestrator consume the bundle.
- **Telemetry SCHEMA bump:** do it **first** — add the `test-designer` role
  (KI-4) and the MCP call/payload token fields the fairness rule needs, and bump
  `schema_version` per `telemetry/SCHEMA.md`.

## Guardrails (method integrity + repo safety)

1. **Never trust a run's own account.** "CI/bundle says green" is verified, not
   trusted: the bundle's `locked_test_sha_observed` must match the local lock
   manifest or the chunk fails closed (`SPIKE.md` §4.1). Re-verify GREEN against
   `phase-1/scripts/verify-green.py`.
2. **Fail closed on missing/bad evidence** — no bundle, red bundle, or hash
   mismatch → stop and surface it; a missing account is a stop, like silent-green.
3. **MCP/evidence access is read-only and scoped to this change's results.** No
   whole-org visibility. Hidden tests never enter any agent's context.
4. **Isolate the working tree.** Other agents may be active. Work in an isolated
   checkout/worktree on a feature branch; never share a tree.
5. **Keep spec/convention changes reviewable.** Land nothing on `main` without
   cross-family review. Stop at the human gate; do not self-merge.
6. **Bundle must be compact by construction** (`SPIKE.md` §2.1): failure records
   are `{nodeid, assertion_line, short_message}`, never full tracebacks — a
   bundle that inlines raw pytest output defeats the experiment.

## Steps

1. Hydrate: `phase-3.2/SPIKE.md`, `phase-3.2/RECOMMENDATION.md`, `PRD.md` §13 +
   §17.1 + §17.5 + §17.6, `telemetry/SCHEMA.md` and the Phase 3 rows in
   `telemetry/runs.jsonl` (control numbers), `phase-3/KNOWN-ISSUES.md` (KI-1..4),
   `phase-1/scripts/verify-green.py`.
2. Do the SCHEMA bump (above) before writing bundle-emitting code.
3. Implement the schema, then the local backend adapter, then the validator +
   orchestrator consumption path. Follow existing repo conventions for code
   placement; log where you put things and why.
4. Demonstrate end-to-end on **one** Phase-3 pilot chunk: produce a bundle for
   the locked `/profile` chunk, have a validator reach a verdict from the bundle
   (not from re-running pytest), and capture both token figures (§3.2).
5. Capture every envelope/artifact under `phase-3.2/build-evidence/`. Preserve
   failures verbatim.

## Assumptions & gaps log (mandatory deliverable)

Write `phase-3.2/ASSUMPTIONS.md`. For **every** point where the spec did not
fully determine what to build, record: (a) the decision you made, (b) why, and
(c) what in the spec was missing or ambiguous. This is a first-class output, not
an afterthought — it is how the spec gets hardened for later phases. "Nothing was
ambiguous" is a valid entry only if genuinely true.

## Deliverables

- The v1 `EvidenceBundle` schema (frozen, versioned).
- The local backend that emits it, reusing `verify-green.py` for the locked-hash
  check and a scanner for the security lens (new-vs-baseline + allowlist).
- A validator + orchestrator consumption path proven on one pilot chunk, with the
  §3.2 token accounting captured.
- `phase-3.2/ASSUMPTIONS.md` (the gap log).
- A short `phase-3.2/BUILD-NOTES.md`: what was built, how to run it locally with
  zero CI, and what remains for the H-CI experiment + Harness backend.

## Definition of done

The local evidence provider runs with **zero CI**, emits a compact signed bundle
whose locked-sha the orchestrator cross-checks, and a validator reaches a verdict
by reading the bundle instead of re-running pytest — demonstrated on one locked
pilot chunk, with both token figures recorded and the assumptions log written.
Presented at the human gate; no self-merge; Harness and the full N-run experiment
left as the clearly-marked follow-on.
