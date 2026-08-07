# Phase 3.3 — Spike seed: the visual / behavioral evidence tier

**Status:** SEED. Spec lightly; **do not build.** This is the second half of the
"externalize the deterministic evidence tier" theme (3.2 = tests + security;
3.3 = visual/behavioral). It reuses the 3.2 evidence-provider abstraction and
extends it to a screenshot/DOM lens. It is the *later* of the two; 3.2 is
near-term.

---

## 1. Motivating evidence (already in hand — this is not speculative)

During Phase 3 the live `GET /profile` rendered **"Demo User"** against the
persistent dev DB even though the chunk-3 seed change was correct and every
unit test passed. A **fresh-DB unit test hid what a running-page lens would have
caught** — the **R3 stale-DB caveat**. The deterministic tier (pytest against a
fresh fixture DB) is *blind to the deployed runtime state*: correct code, green
tests, wrong pixels.

That gap is the entire case for a visual/behavioral tier. It is a different
*kind* of evidence — not "does the locked assertion pass on a fresh DB" but
"what does the actually-rendered page show against the running system." The two
tiers are complementary: 3.2 hardens the deterministic account; 3.3 adds the
account the deterministic tier structurally cannot give.

---

## 2. Where it fits: same abstraction, new evidence kind

The visual tier is **another evidence-provider backend** (3.2 §2), emitting an
extended bundle, not a parallel mechanism:

```
VisualEvidenceBundle (extends EvidenceBundle):
  rendered:
    url / route
    runtime_target        # which running system was hit (fresh-seeded vs dev DB — R3!)
    screenshot_ref        # artifact pointer, NOT inlined pixels
    dom_snapshot_digest   # hash + compact extracted assertions, NOT full DOM dump
  behavioral_checks[]:
    {check_id, expectation, observed, pass/fail}   # e.g. "profile shows full_name != 'Demo User'"
  provenance: { producer_run_id, target_env, tool_versions }
  signature
```

Two design rules carried from 3.2:

- **Compact by construction.** The panel reads *extracted assertions and a
  screenshot pointer*, never a raw DOM dump or inlined image tokens. Same
  fairness discipline as H-CI: a bundle that inlines the artifact has thrown
  away the token win.
- **Runtime target is first-class.** The R3 bug was a *target* problem (dev DB
  vs fresh seed). The bundle must state which running system it observed, so a
  green visual check against the wrong target is not mistaken for a pass.

---

## 3. Surface options to weigh (pick one to prototype later)

| Surface | What it is | Pros | Cons / unknowns |
|---|---|---|---|
| **Local Playwright** | Headless browser driven locally; screenshot + DOM extraction | Zero external dependency (matches the 3.2 "local default" principle); fully in-repo; cheapest to stand up | Someone must run/host the app + a defined target env; no hosted judging |
| **Harness hosted Playwright + screenshot agent** | CI-hosted browser run, pulled via Harness MCP | Same inbound edge as 3.2; no local browser infra; artifacts already structured | Vendor backend (must stay *a* backend, not *the* dependency); a "screenshot agent" implies a model doing judging — whose model? (§4) |
| **Factory Droid Control / Automated QA** | Factory-native driving of the running app | Native to the toolchain; potential demo asset | Maturity/capability for headless assertion + artifact export is an open question to probe |

Consistent with 3.2: **local is the default backend** (zero external dependency,
loop runs without CI); hosted surfaces stub in behind the same interface. The
method depends on the *capability* (render the page against a named target and
return compact visual/behavioral evidence), never on any one product.

---

## 4. Independence: a visual validator is still a validator

This is the load-bearing constraint and the easiest to get wrong.

- A visual check **occupies a validator seat** and must respect family
  separation exactly like the code panel: **≠ executor family**, cross-family
  with the rest of the panel (PRD §17.2, invariant #1). It is not a free "extra
  check" exempt from the seat rules.
- **A screenshot-judging agent is a model, and its family must be named and
  folded into the independence accounting.** "Does this rendered page show the
  right identity?" is a *judgment*, not a deterministic assertion — so whatever
  model powers the screenshot/DOM agent is a panelist. If it shares a family with
  the executor (or with a standing code validator in a way that correlates blind
  spots), independence is weakened. The spec must record: *whose model judges the
  pixels, and does that family collide?*
- Distinguish the **deterministic** part (Playwright navigates, captures, runs a
  literal DOM assertion like `full_name != "Demo User"` — no model) from the
  **judgment** part (a model interpreting a screenshot). The deterministic part
  is evidence like any other bundle field and carries no independence cost; only
  the model-judgment part consumes a seat and must satisfy separation. Prefer
  pushing as much as possible into the deterministic DOM-assertion path and
  reserving model judgment for what genuinely needs perception.
- **A single judging model is not a safe gate — Phase 3.1 proved this
  empirically.** On the same-family-author chunk, `grok-4.5` caught the weakened
  test while `gemini-3.1-pro-preview` observed the identical failure and still
  returned ACCEPT (`phase-3.1/RESULTS.md`). A one-model judge would have shipped
  it. The direct 3.3 consequence: a lone screenshot-judging model is exactly that
  fragile single gate, and any *perceptual* verdict must sit behind the same
  **≥2-model, fail-closed** panel semantics — or, better, be reduced to a
  deterministic DOM assertion that does not depend on a model's judgment at all.

---

## 5. Open questions for the human (3.3-specific)

- **Target-env policy:** does the visual tier run against a fresh-seeded target
  (reproducible, but re-hides R3) or against a dev-like persistent target (catches
  R3, but is non-deterministic)? Likely: *both*, reported separately — a fresh
  target for a reproducible gate and a dev-like target specifically to surface
  stale-state divergence. Needs a human call.
- **Judging model seat:** which family powers screenshot judgment, and does it
  force a code-panel swap to preserve separation?
- **How much can stay deterministic** (DOM assertions) vs needs perception
  (model)? The more that is deterministic, the smaller the independence and token
  cost.
- **Sequencing:** 3.3 is explicitly after 3.2 lands the abstraction; confirm it
  is not pulled forward.

---

## 6. Why this is a seed, not a plan

3.2 must first prove the evidence-provider abstraction and the H-CI economics on
the *deterministic* tier. 3.3 inherits that abstraction; building it before 3.2
would fork the interface. The concrete deliverable here is only: the R3
motivation, the surface options, the extended-bundle shape, and the
independence treatment of a visual validator. Prototype selection and target-env
policy wait on the 3.2 result and a human decision.
