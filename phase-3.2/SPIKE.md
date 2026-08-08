# Phase 3.2 — Spike: externalize the deterministic evidence tier into CI

**Status:** PLAN ONLY. This is a planner handoff, not an execution artifact. No
pipeline code, no MCP wiring, no pilot edits are produced here. The output is a
reviewable spec plus a recommendation; building waits on human approval.

**Control arm:** Phase 3 (complete, merged to `main` @ `ade12c0`). Baseline in
`telemetry/runs.jsonl`: **≈540.6k tokens** input+output over 12 successful role
runs — **validators ~84% (453,918)**, executor ~13% (68,723), test-designer ~3%
(17,945). Within the panel, `gemini-3.1-pro-preview` alone was ≈384k (96k–165k
*input* per run) vs `grok-4.5` at 16k–30k input.

---

## 1. The problem this spike attacks

Today every seat that touches the deterministic layer re-runs it *in session*:

- the executor runs pytest to reach GREEN;
- **each** validator runs pytest again and reads raw stdout to trust the green;
- the orchestrator re-runs the hash-locked `verify-green.py` gate.

The 84% panel cost is not one thing. Decomposing a validator run:

1. reading the **diff + spec** (irreducible — it is the review),
2. running pytest and ingesting **raw test output** (the deterministic re-run),
3. reasoning to a verdict.

Only **(2)** is a candidate for externalization. A neutral producer (CI) runs
the deterministic work once and the panel consumes a compact structured result
instead of raw pytest stdout. The hypothesis is that (2) is a meaningful slice
of the 84% and that a structured bundle is smaller than the stdout it replaces.

**Non-goal:** making the review cheaper by removing review. (1) and (3) do not
move. CI *augments* the panel; it does not replace it (see §4).

---

## 2. The evidence-provider abstraction (interface, not a vendor)

The load-bearing decision from the originating session: **CI is a *mode*, not a
dependency.** The loop must run with **zero CI**. So the primitive is an abstract
**evidence-provider** interface with a **local backend as the default**, and
Harness as *one* interchangeable backend behind the same interface.

### 2.1 Interface

An evidence provider answers one question: *"for this exact change, what does the
deterministic tier report?"* It returns a signed, compact **evidence bundle**.

```
EvidenceProvider.get_evidence(change_ref) -> EvidenceBundle

change_ref:
  repo            # pilot repo identity
  commit_sha      # the change under review (feature branch HEAD)
  locked_test_sha # sha256 from the lock manifest (see §4.1) — REQUIRED input,
                  # so the provider proves it ran THE locked test, not some test

EvidenceBundle (schema-versioned, the ONLY thing agents read):
  bundle_schema_version
  producer            # "local" | "harness" | <other> — recorded, never trusted-blind
  change:
    commit_sha
    locked_test_sha_observed   # what the producer actually hashed and ran
  tests:
    passed / failed / skipped  # counts
    failures[]: {nodeid, assertion_line, short_message}  # NO full traceback dump
    suite_exit_code
  coverage (optional):
    lines_pct, changed-lines-covered summary
  security (optional, SEPARATE lens — see §3.3):
    findings[]: {rule_id, severity, file, line, short_message}  # SARIF-derived
  provenance:
    producer_run_id, started_at, finished_at, tool_versions
  signature   # so "who produced this" is not spoofable inside an agent's context
```

Design rules for the bundle:

- **Compact by construction.** Failure records are `{nodeid, assertion_line,
  short_message}`, never full tracebacks. The whole point is that the bundle is
  smaller than in-session stdout; a bundle that inlines raw pytest output has
  thrown away the win before the experiment runs.
- **The method depends on the *capability* (deterministic evidence for a locked
  change), never on Harness.** Any backend that can run the locked test and
  return this schema is admissible.
- **Read-only, scoped to *this change's* results.** No whole-org visibility, no
  cross-change data (§4, §5).

### 2.2 Local backend (the default — zero CI)

Composes tools the repo already has:

- tests → pytest (as `verify-green.py` already invokes it);
- locked-hash check → **reuse `phase-1/scripts/verify-green.py`** (it already
  recomputes the test sha, compares to the lock manifest, and refuses GREEN on
  mismatch — that is exactly `locked_test_sha_observed`);
- security → a local scanner (**Semgrep and/or Bandit**) emitting SARIF, mapped
  into `security.findings[]`.

The local backend is a thin adapter that runs these, normalizes to the bundle
schema, and signs it. It runs on a developer machine with no network CI. This is
what makes CI a mode: the *same* bundle schema is produced locally.

### 2.3 Two flavors of "CI backend" — keep them distinct

"CI is a backend" is really two different things behind the same interface. The
distinction matters because it decides *how much* is portable:

- **(a) CI-as-runner.** The pipeline just executes the **local backend's own
  script** as a job step. The bundle is produced by *our* code; CI supplies only
  the trigger + compute. This is identical on GitHub Actions, GitLab CI, Harness,
  or a cron box — maximally portable, and it is the cheapest bridge from "runs on
  a laptop" to "runs in a pipe" because it is the *same producer* in a different
  place.
- **(b) CI-as-native-producer.** The platform does the deterministic work *its
  own way* and we adapt its output into our bundle schema. For **Harness** that
  is pulling native tests / coverage / SARIF / **Test-Intelligence** for *this
  change* via **Harness MCP** (the inbound edge, §6) rather than scraping
  artifacts. More platform-specific, but it inherits the platform's extras
  (flaky-test detection, incremental testing, baseline diffing — see §4.4).

The **local default is flavor (a) with no pipeline at all**. **Harness is our
first flavor-(b) backend**, chosen to prove the interface generalizes beyond
"just run our script." Other CIs (GHA, GitLab) arrive later as thin adapters —
flavor (a) is free on all of them; flavor (b) is per-platform work. Either way,
nothing in the panel prompt names a vendor; it names the bundle. **Code to local
+ Harness for now.**

### 2.4 How the backend is selected — it auto-resolves; it is NOT a feature flag

Backend choice is **dependency selection, not behavior gating**: every backend
produces and the panel consumes the *same* `EvidenceBundle`, so the loop's
behavior does not change with the backend — only the producer does. That rules
out a feature-flag system (runtime toggles / a flag service are for rolling out
*behavior* changes; there is no behavior change here to gate). It should not be
optional busywork either — the everyday path takes **zero configuration**.

The rule, mirroring the repo's existing model-seat discipline (§17.1
attribution-vs-enforcement — *auto where nothing binds, pin where it matters,
always know which one ran*):

- **Auto-resolve by context is the default, and it just happens.** Running on a
  developer machine → the local backend produces. A commit/PR firing the pipeline
  → the pipeline's producer runs. **Nobody picks a backend**; the execution
  context determines it. No flag, no daily switch.
- **The explicit selector is an escape hatch, not the daily path.** Its one real
  use is the H-CI A/B (§3.4), where you *deliberately* force the same locked
  slice through local vs Harness back-to-back to compare tokens. Outside that
  experiment it stays untouched.
- **The producer that actually ran is always recorded** in the bundle's
  `producer` field (§2.1) and the run artifact. Attribution is the load-bearing
  part, not the switch — you must always *know* which producer ran, even though
  you rarely *choose* it.

Why the escape hatch is per-invocation (not global state): H-CI needs each arm
to be a clean, independently-recorded run; a global toggle flipped between runs
is exactly the shared-state confound the experiment must avoid.

---

## 3. The headline experiment (H-CI), designed to be credible

**Hypothesis (H-CI):** routing deterministic evidence through a provider (CI)
*reduces average token cost at equal acceptance quality.* Phase 3 = control arm;
3.2 = treatment arm. **Only the evidence source changes.**

### 3.1 Metric

- **Primary cost:** total input+output tokens to reach the *same* ACCEPT, per
  chunk and summed. Same reporting shape as the Phase-3 slice table.
- **Primary quality (guard, not a bonus):** acceptance-pass-rate **must not
  drop**. Cheaper-but-worse is not a win (PRD §13: "no decrease in hidden
  acceptance-test pass rate"). If quality drops, H-CI fails regardless of cost.
- Report against the PRD §13 goal (≥25% lower cost than the separated-role arm,
  as a goal not a guarantee).

### 3.2 Fairness rule (MANDATORY — the experiment is a lie without it)

**Count the MCP call + returned payload tokens on the treatment side.** The
evidence bundle enters some agent's context and costs input tokens to read;
those tokens are part of the treatment cost. Offloading is not free.

> The win is real **only if** `tokens(evidence bundle read) <
> tokens(in-session raw test output it replaces)`.

Predict a **partial** win. Decompose a validator run into (1) diff+spec read,
(2) test-output read, (3) verdict reasoning (§1). CI only moves (2). The validator
still pays (1) and (3). So the *ceiling* on H-CI's saving is the size of (2),
and the realized saving is `size(2) − size(bundle)`. On the Phase-3 numbers the
context-heavy validator (gemini, 96k–165k input) is where any (2) saving would
show; grok (16k–30k input) has less headroom. The spike must instrument (2)
explicitly so the ceiling is measured, not assumed.

### 3.3 Keep security scans OUT of the cost comparison

Security scans **add a lens** (new findings) — a coverage gain, not a cost delta.
Folding them into the token comparison would contaminate "did CI make the loop
cheaper" with "CI also does more work now." So:

- the **cost** comparison uses tests+coverage evidence only, matched to what
  Phase 3 actually ran in-session;
- **security findings are reported separately** as a coverage result (what new
  categories did the scanner surface that the panel did not?).

### 3.4 Control confounds

Identical models, reasoning efforts, prompts, diff, chunk structure, locked
tests, acceptance gate. The **only** changed variable is the evidence source.
Run **N times** (single runs lie — the same discipline as 3.1). Isolate the
pilot working tree with `git worktree` if a 3.1 run is live (§ parallelization,
EXPLORER-PROMPT).

### 3.5 What each outcome means

- **Bundle < in-session output, quality holds:** externalization is a real cost
  lever on the panel; promote CI-evidence as a mode. Size names how much of the
  84% was deterministic-re-run vs irreducible review.
- **Bundle ≥ in-session output (or quality drops):** the deterministic re-run
  was *not* the expensive part — the review reasoning is — and the bigger lever
  is panel size / validator context discipline (the phase-3 slice already
  suspected this). A null result is valid data (PRD §13).

---

## 4. Trust rules to preserve (CI must not weaken the method)

### 4.1 "CI says green" is itself an account, and accounts are verified

A bare "green" is the silent-green defect in a new costume. The provider **must
publish the locked-test sha it actually ran** (`locked_test_sha_observed`), and
the **orchestrator cross-checks it against the local lock manifest** before
trusting the bundle. The trusted statement is *"CI ran the **locked** test
(hash matches the manifest) and it passed,"* never *"CI is green."* This is the
same content check `verify-green.py` already enforces locally; the provider
simply carries the observed sha out so the orchestrator can re-assert it.

Corollary: a bundle whose `locked_test_sha_observed` ≠ manifest sha is rejected
exactly like a hash-mismatch GREEN today — fail closed.

### 4.2 When the gate fires, and how failures become visible

The trigger cadence is pinned to the loop's own beat — **the chunk** — not to
every commit:

- **Chunk boundary = the review signal.** Each chunk ends on a feature-branch
  commit/PR and must reach ACCEPT before the next unblocks (PRD §5.2). The
  **gate pipeline (pre-merge) fires there**, and the validators consume *that
  chunk's* bundle before they vote. That is the moment a failure becomes visible
  and can block the next chunk — the panel votes on CI evidence, not ahead of it.
- **Merge-to-main = the baseline pipeline**, the regression + security baseline
  (§4.4 history scope). Not the per-chunk signal and not on the review critical
  path; it establishes the post-merge floor.
- **Awareness = fail closed, surfaced by the orchestrator.** No bundle, a red
  bundle, or a `locked_test_sha_observed` mismatch (§4.1) → the chunk does **not**
  advance and the orchestrator raises it. The agents do not poll for status; the
  gate makes the failure loud. A *missing* account is a stop, exactly as a silent
  green is (`droid-wiki/findings/silent-green.md`).

Every-commit triggering is deliberately avoided: agent-visible gating on every
commit adds cost and churn without adding a decision point, since nothing
advances between chunk boundaries anyway.

### 4.3 CI augments, does not replace, the panel

Tests + scans are **necessary, not sufficient**. The cross-family review of the
diff — spec conformance, semantics, over-exposure (e.g. `SELECT *` / leaking
`id`/`created_at`, the exact things Phase-3 validators checked at runtime) —
still stands. CI removes the *re-run*, not the *review*.

Phase 3.1 corroborates why the panel stays: with a same-family (cheap)
test-author, `grok-4.5` caught the weakened test while `gemini-3.1-pro-preview`
dismissed the identical failure and returned ACCEPT (`phase-3.1/RESULTS.md`). A
single-model gate would have shipped it; the ≥2-model fail-closed panel is what
compensated. CI evidence does not change that — it feeds the panel, it is not the
panel.

### 4.4 Security-gate discipline (learned from the first real Harness run)

The pilot's `feat/user-profile` went through the Harness pipeline and produced
three concrete lessons — all from **pre-existing debt, not the Phase-3 change**.
The 3.2 security lens must be built to these, or it will cry wolf:

1. **Gate on NEW findings vs a baseline, not total history.** Gitleaks failed the
   build on `fail_on_severity: low` against the full 89-commit history, while its
   own report said `newIssuesCount: 0` — the finding was legacy debt, not new in
   this change. If the gate keys on total history, every run trips on old debt
   and the "did *this change* introduce a problem?" signal drowns. The bundle's
   `security.findings[]` must carry a **new-vs-baseline flag** (SARIF
   `newIssues*` / new-occurrences), and the merge gate keys on *new* only.
2. **The scanner is not an oracle — a human/model still classifies.** Gitleaks
   flagged `SPLIT_CLIENT_KEY` (a Split.io *client-side* key, public by design —
   it ships in browser JS) as `generic-api-key` on a pure entropy heuristic. A
   false positive. This is "an account is not evidence" applied to CI: the
   security tier needs a **curated allowlist scoped to the specific known-public
   value** (not whole files, so a real future secret still trips), and its
   verdicts *feed* the panel's judgment, they do not end it.
3. **Diff-scoped vs history-scoped are both valid at their scope.** The
   orchestrator's pre-push scan was diff-scoped (our new commits — correctly
   found nothing); gitleaks was full-history (found legacy debt). The bundle must
   **label which scope produced a finding**, and the design must be explicit:
   the **diff/new** scope gates the merge; the **history** scope is a standing
   baseline report (§4.2 on-merge pipeline), never a merge blocker on its own.

These three are why security is reported as a *separate lens* (§3.3) and kept out
of the H-CI token comparison: their value is finding *new* real issues without
drowning in old-debt false-fails, which is a coverage/precision property, not a
cost delta.

---

## 5. MCP seat allocation (default)

Read-only, scoped to **this change's** results, never whole-org. The deciding
constraint: **hidden tests stay out of every agent's context, executor
included** (PRD §13 — a seat that can see held-out tests can code/coach toward
them).

| Seat | MCP? | Why |
|---|---|---|
| Validators | **yes** | They are the 84% and the primary win; they consume the bundle instead of re-running pytest. |
| Orchestrator | **yes** | Gating + the §4.1 locked-hash cross-check. |
| Executor / "coder" | **default no** | Hidden tests must not reach it; if ever granted, scope strictly to *its own change's* results, never the held-out set. |
| Test-designer | no | Authors the locked test; no need for evidence pull. |

All access read-only and change-scoped. This mirrors §17.5's least-privilege
tool surface and KI-2's write-vector concern (a read-only evidence pull is
strictly safer than the current in-session `Execute`-at-`--auto-high` pytest
run, and would *reduce* the KI-2 residual for the seats that switch to it).

---

## 6. Integration edges (native, no bespoke connector)

- **Outbound (invocation):** a git trigger on push/merge fires the pipeline. One
  already exists on quantum-bank; a framework-repo trigger is planned. No custom
  invocation layer.
- **Inbound (evidence):** **Harness MCP** — a Factory agent *pulls* the
  structured bundle on demand. No artifact scraping, no bespoke connector. In the
  local mode there is no inbound edge at all; the local backend produces the
  bundle in-process.

---

## 7. Second target: dogfood the framework repo (and what else runs on the pipe)

The human wants **this framework repo** (`adversarial-sprint-dev`), not just the
pilot, run through a pipeline — a distinct target of the *same* evidence-provider
abstraction. Two different kinds of work run on that pipeline, and keeping them
separate keeps the scope honest:

- **A deterministic producer (the 3.2 core, no judgment).** Validate the
  framework's own deterministic assets against the same bundle contract: the hook
  matcher, `phase-1/scripts/` (e.g. `verify-green.py`), `phase-3/gen-telemetry.py`,
  and `telemetry/runs.jsonl` against `telemetry/SCHEMA.md`. This gives the
  framework its own regression net and proves the abstraction generalizes beyond
  one repo. It is a **separate target from the pilot** and must **not** feed the
  H-CI token A/B (different repo, different assets — mixing them contaminates the
  control).
- **CI-triggered *agent* tasks (judgment/generation, distinct from the
  producer).** Triggering an agent from a commit/merge is a legitimate pattern —
  e.g. a wiki-refresh-on-merge agent. It maps onto §2.3 **CI-as-runner
  (flavor a)**: the pipe is only *trigger + compute*; the method still lives in
  the agent. **Sequencing:** such tasks are **downstream of 3.2** — they reuse
  the CI trigger + run-an-agent-from-the-pipe machinery this spike establishes,
  so they come *after* 3.2 lands, not as a separate parallel track. Guardrails
  carry over unchanged: family separation and hidden-test exclusion must hold in
  CI exactly as in-session, and generated output (docs, reviews) still hits a
  review gate before landing on `main` — "runs in CI" must not quietly erode the
  invariants or auto-merge unreviewed narrative.

The boundary to hold: **the deterministic producer emits evidence; agent tasks
are separate jobs on the same trigger.** Do not conflate "externalize the
deterministic tier" (this spike) with "relocate a judging agent into CI" (a
different decision with its own independence accounting).

---

## 8. What this spike deliberately does NOT decide

- The exact local scanner (Semgrep vs Bandit vs both) — pick at prototype time;
  the interface does not care.
- The bundle signature scheme — an implementation detail of "producer is not
  spoofable in-context"; name it when building.
- Whether the framework-repo trigger ships with 3.2 or later — the pilot
  (quantum-bank) already has a trigger, which is enough to run H-CI.

---

## 9. Build order when approved (for reference, not this pass)

1. Freeze the `EvidenceBundle` schema (`bundle_schema_version` v1).
2. Local backend adapter over pytest + `verify-green.py` + Semgrep/Bandit.
3. Wire validators + orchestrator to consume the bundle (local mode) — this
   alone lets H-CI run with **zero CI**, cleanly isolating "structured evidence"
   from "Harness."
4. Add the Harness backend behind the same interface (MCP inbound) as the second
   producer; re-run H-CI to confirm the backend is interchangeable.
5. Instrument (2) (in-session test-output tokens) so the fairness ceiling (§3.2)
   is measured on both arms.

The step-3 local mode matters for confounds: it separates the variable *"panel
reads a compact bundle instead of raw stdout"* from *"Harness is involved,"* so a
positive or null H-CI result is attributable to externalization itself.
