# First H1 evidence

The first pilot was the adversarial method run by hand against an external project before the plugin existed. The target was QuantumBank, a small Flask demo. Four units added machine-readable surface (`/llms.txt`, `/robots.txt`, `/llms-full.txt`, `/sitemap.xml`). One model planned and orchestrated; Grok and Kimi validated in fresh contexts. The run showed the method firing, and it showed how easily the wrong model can run a refactor without anyone noticing.

## The four units

`planning/pilots/ai-discovery/README.md` is the primary record. The units were:

| Unit | Surface | Merged as |
|---|---|---|
| 1 | `/llms.txt` | direct to main |
| 2–3 | `/robots.txt`, `/llms-full.txt` | PR #9 |
| 4 | `/sitemap.xml` | PR #10 |

All four are live on `qbank.dev`. The pilot was the adversarial arm, not the Phase 0.5 baseline. It relied on operator-held isolation, not the reference guard or a router.

## What the reviewers found

Three validator outputs are captured under `planning/pilots/ai-discovery/validator-outputs/`:

- **Grok** found a dangling reference: `/robots.txt` and `/llms-full.txt` both declared a `Sitemap:` URL that returned 404. Unit 4 was built to close it.
- **Kimi** found a process-narrative leak in `/llms-full.txt`: internal words like "worker", "pilot", and "human-gated" had leaked into a served, machine-facing artifact.
- **Both** independently flagged the same doubled-charset bug in `/llms.txt`: `Response(..., mimetype="text/plain; charset=utf-8")` produced a malformed `Content-Type: text/plain; charset=utf-8; charset=utf-8`. Both graded it a nit.

The doubled-charset catch is the honest counterweight to the non-overlap story. Two different families, blind to each other, converged on the same real defect. The lock commit `8a10711d` hardened the assertion to count exactly one `charset=` parameter, not just a `text/plain` prefix. That is a true removal lock, not a superstring trap: the test fails if the bug is reintroduced, and passes only when the body contains exactly one `charset=` value.

The Unit 4 close-out in `planning/pilots/ai-discovery/validator-outputs/sitemap-unit4-validation.md` shows the same discipline applied to Grok's dangling-reference finding. The validator asserted that `/sitemap.xml` resolved 200, that the body contained the promised URLs, and that it excluded `/api/` routes. It also ran a true-removal proof: injecting an `/api/` URL caused the assertion to fail, restoring it caused the assertion to pass. This is the RED-before-GREEN pattern the method codifies, executed by hand.

## What the evidence supports and does not support

The pilot supports that independent cross-family review can catch things the planner and executor miss. The unique findings per reviewer plus the overlapping catch make a clean case for the method's value.

It does not support a cost claim. The two reviewers were given different lenses — content versus abuse — so family independence and lens diversity are confounded. No same-prompt A/B was run. The pilot is N = 4 units, one operator, one sitting: enough to show the mechanism fires, not enough for a rate, precision figure, or effect size.

It also does not support that the plugin did this. Isolation and model separation were held by operator convention, not by enforcement. The pilot is the manual arm the plugin will later be measured against.

## The role-split observation

The same record contains a second finding that is not about QuantumBank at all: the wrong model ran a five-chunk refactor, and nothing in the run surfaced it until the operator read the commit record. The cheap seat in the lineup filled the executor role without a banner or a gate. That is why the framework now requires the resolved model ID to be visible in every chunk close and why the family gate is non-negotiable.

## What to take away

The pilot proved the method by hand: plan, execute, cross-family review, reconcile, and ship. It also proved that hand-run isolation is fragile. The same run that found the doubled-charset bug also missed the wrong model. That is the gap the plugin closes. See [the method](../method.md) for the workflow the pilot exercised, [security](../security.md) for the trust boundaries that were held by convention, and [silent green](silent-green.md) for the failure mode the wrong-model observation exemplifies.
