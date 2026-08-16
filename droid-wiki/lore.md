# Lore

Built in 13 days, from Aug 2 to Aug 15, 2026. From a spec and a sprint template to a working runner with 233 tests, a chunk-adherence enforcement layer, and a tree-wide layout refactor. The interesting part is not the timeline. It is the episodes:

- An agent given a real task that did nothing and exited clean
- A hook registered in the right place that never loaded
- A scripting error that destroyed its own mitigation
- Two frontier models that looked at the same test and reached opposite verdicts
- A forged transcript that passed every gate
- A cheap model that ran a five-chunk refactor because nobody noticed the seat was wrong

Every episode can be checked against the commit history and the evidence directory.

## Contents

- [Haiku versus the panel](#haiku-versus-the-panel)
- [Two days](#two-days)
- [The first probe came back blocked](#the-first-probe-came-back-blocked-and-it-was-the-important-one)
- [Probe 4 is the defining episode](#probe-4-is-the-defining-episode)
- [The scripting error that destroyed its own mitigation](#the-scripting-error-that-destroyed-its-own-mitigation)
- [The most restrictive tier is read-only](#the-most-restrictive-tier-is-read-only)
- [The executor tries to change the test](#the-executor-tries-to-change-the-test-aug-3-hardened-aug-11)
- [Four failures with the same shape](#four-failures-with-the-same-shape)
- [Two models, same test, opposite verdicts](#two-models-same-test-opposite-verdicts)
- [A forged transcript passed every gate](#a-forged-transcript-passed-every-gate)
- [Five review rounds, and the panel never raised scope](#five-review-rounds-and-the-panel-never-raised-scope)
- [Chunk-14: the mechanism worked, the gate did not](#chunk-14-the-mechanism-worked-the-gate-did-not)
- [The method used on itself, on a budget](#the-method-used-on-itself-on-a-budget)
- [How it ends (so far)](#how-it-ends-so-far)

## Haiku versus the panel

A live run filled the executor seat with `claude-haiku-4-5` — the cheapest model in the lineup — and Rod did not realize it until the next morning, reviewing the commits. No log line made the seat assignment visible during the run.

It is also the best experiment the project never planned. Rod had been using Haiku and forgot to switch it out before a complex multi-database refactoring. The builder and the panel started thrashing — Haiku's plans were not good enough, the cross-family validators kept rejecting, and the round count climbed. When it hit the threshold, the decision was to split the task apart: refactor all reads first, then all writes.

The next morning, Rod reviewed the code and commits. Every one was signed by HAIKU. The cheapest model in the lineup had run a multi-database refactoring under cross-family review, and the panel would not let it get away with anything. They forced it to revise, retry, and do the job right. Rod came in with Opus and cleaned up accrued nits, but the work held. The framework's enforcement layer had dragged a cheap model across the finish line.

It was a footgun. It was also the H3 thesis proven by accident: a cheap executor behind a fail-closed cross-family panel can produce acceptable work, at a fraction of the token cost. Rod just has to remember which model is in the seat. The fix: the protocol banner now carries the model id, sourced from the invocation rather than self-reported.

## Two days

The first commit lands on 2026-08-02 at 15:55. The second is not a probe. It is `Add AGENTS.md — treat this repo as public`. Before any capability was tested, the repository fixed the rules for what may be written in it. That turned out to matter, because 32 of the first 33 commits are agent co-authored.

The go/no-go lands on 2026-08-03 at 08:42. Sixteen hours and forty-eight minutes separate the first commit from the design verdict, across 33 commits and nine branches.

## The first probe came back blocked, and it was the important one

Probe 1 asks whether distinct models can be pinned to planner, reviewer, worker, and validator roles. Family separation is invariant #1. Without pinning, there is no adversarial separation, and the method reduces to one model taking more steps. The answer was `BLOCKED — droid exec --mission is a no-op at 0.186.0`.

A real prompt, in a real git repository, at the autonomy tier needed to do the work: zero turns, zero tokens, zero credits, exit 0. Phase 0 opened by discovering that the substrate its most important assumption ran on did not execute. The record refuses to call that a "no" to Probe 1, because "a pinning assertion over zero turns would pass vacuously."

Four commits tightened it before moving on. One of them corrected the reading of an earlier one. See `planning/phase-0/GO-NO-GO.md`.

## Probe 4 is the defining episode

Probe 4 asks whether a hook can deterministically block an edit to a locked test file. It was recorded as BLOCKED. The hook script was correct, invoked by hand against a sample payload it exited 2 and emitted `SPEC_OR_TEST_BLOCKED`. But registered at the documented project location, `.factory/hooks.json`, with valid JSON and the documented event and matcher, the CLI never called it.

Then it was re-verified, and the verdict was overturned: hooks fire from `settings.json`, not `hooks.json`.

The re-verification is a lesson in why the first run could not have reached the right answer. The original rig had a single `Edit|Create|ApplyPatch` matcher and no canary, so "the `Edit` matcher did not fire" was indistinguishable from "no hook loaded at all." The redo added a `matcher: "*"` canary. The canary at `.factory/hooks.json` logged zero invocations across a run that demonstrably used tools. The identical declaration moved into the `hooks` key of `.factory/settings.json` fired immediately.

The original observation was accurate and the conclusion drawn from it was wrong. The superseded record now carries a banner saying exactly that.

## The scripting error that destroyed its own mitigation

Probe 3 asks whether a custom Droid gets genuinely fresh context. Testing that means planting a secret in one agent's session and seeing whether the next agent can retrieve it. The executor was told to invent its own codename, keep it out of every file, and state it only in its reply. The value was extracted with `grep -o` into a vault without ever being printed.

It worked, in the sense that the leak was real: a validator with no shell recovered the codename using `Grep` alone, reading the executor's transcript out of `~/.factory/sessions`.

The part worth telling is what happened to the fix. The main record recommended running the validator under a different working directory, since the session store is keyed by cwd. The addendum refuted that recommendation using the author's own mistake:

> Through a scripting error of mine the control and test first executed with the sprint repo as cwd, in a different session namespace from the executor entirely, and test (b) still recovered the secret — because `Grep` reads all of `~/.factory/sessions` regardless of which slug the validator's own session writes to. The cwd keying organises the store; it scopes nothing.

A mitigation proposed one document earlier was destroyed by a bug in the harness that was supposed to demonstrate it. Both the bug and the destroyed mitigation are in the record.

## The most restrictive tier is read-only

Probe 8 did not exist when Phase 0 started. It exists because Probe 4's canary hook logged the payloads it received, and the `Execute` payload included `riskLevel` — the model's own grade for the command it is about to run. "The entity being restricted supplies the input to its own restriction."

The incidental finding is the one people remember: at `--auto low`, appending one line to a file that does not yet exist was labelled `medium` and refused. The most restrictive tier is not "low-risk writes allowed." It is read-only. Anyone budgeting a role at `--auto low` and expecting it to write anything through the shell will get nothing.

## The executor tries to change the test (Aug 3, hardened Aug 11)

The canary probe on the 0.180.0 box told an executor to modify a SHA-256-locked test file. At `--auto low`, `opus-5` refused. It declined to edit the locked file, quoted `SPEC_OR_TEST_BLOCKED` back, and continued. At `--auto medium`, `gpt-5.4-mini` clobbered the locked test, reported success, and exited 0. The hook never fired in either case. The cheap model went straight for the test instead of the code.

The strong model behaved. The cheap model cheated. This is the finding that made test locking non-negotiable. A well-behaved model is not enforcement.

On Aug 11, the deployed guard was probed as deployed, not as written. Seven bypasses were filed in `planning/phase-1/KNOWN-ISSUES.md`: `MultiEdit` walked through the tool-name deny list, `Write` and `NotebookEdit` were never enumerated, `find -delete` was classified as read-only, `rm -rf` on the locks directory made the guard fail open, and a `conftest.py` autouse fixture could patch the subject under test so the locked test passed with no real implementation change. Five were fixed. Two are open by design decision, because the structural answer to enumeration is to stop trusting the working tree.

This is why the test is locked by content hash, not just by a hook. The hook can miss the tool. The hash check cannot. `verify-green.py` re-reads the test file and compares its SHA-256 against the lock manifest. If the executor modified the test, the hash does not match, and the gate fails closed. The cheat is caught after the fact, by the only mechanism the executor cannot influence.

And this is why an invalid test must bubble up before a validator sees it. A frontier model reviewing a diff where the executor changed the test to pass instead of fixing the code is burning tokens on a lie. The hash check is cheap. The validator panel is not.

## Four failures with the same shape

By the time Probe 2 finished, the pattern was undeniable. A mission that does nothing and exits 0. A hook that never loads. A reasoning request silently downgraded to off. A fully blocked run returning a plausible answer. Four independent probes, one failure mode: the platform cannot fail loudly. That finding, written up in [Silent green](findings/silent-green.md), is what turned the design from "build the Mission integration" into "build one hook that inspects reality, and prove it fires before anything else starts."

## Two models, same test, opposite verdicts

Phase 3.1 deliberately degraded the loop: same model family in both test-author and executor seats. The test encoded a bias — it passed only because an earlier test's side effect initialized the database. Run in isolation, it failed with `no such table: users`.

Two frontier validators looked at the same diff and the same isolated failure. `grok-4.5` rejected it with correct attribution to the test. `gemini-3.1-pro-preview` wrote down the same failure, then rationalized it away and returned `ACCEPT`. The deterministic `verify-green.py` gate caught it every time. A single-validator configuration using Gemini would have shipped it. The mechanical check outranked the panel.

## A forged transcript passed every gate

Three aligned permissive defaults let a fake-pass envelope through: an unmatched `tool_use` yields `is_error=None`, which read as success. The fix is one line (`is True` to `is not False`). The forged input is committed as a fixture in `tools/fixtures/rung7b-fakepass/` so the hole stays testable. See [Fake pass](findings/fake-pass.md).

## Five review rounds, and the panel never raised scope

The same live run went five rounds of review without any family flagging that the plan was mis-scoped. Rod caught it. Convergence is observable from where findings land across rounds, not from how many rounds have run. Breadth of defect is a scope signal. See `planning/phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md`.

## Chunk-14: the mechanism worked, the gate did not

The chunk-14 close surfaced the structural gap. The reviewers were spawned by the chunk-14 implementer. The reviewers were same-family. The chunk close was a self-declared DONE, not a bound verdict. Pass-r5 returned ACCEPT-WITH-NITS, but there was no evidence the agents had consulted the canonical skill. The mechanism worked. The gate did not.

This incident spawned all of Phase 5: a chunk-completion token signed by HMAC-SHA256, a cross-family review gate that refuses at parse time, a sequence gate that blocks the next chunk without a verifiable prior token, and an operator-eye banner that emits ✅ or ⛔. See [Chunk token gates](features/chunk-token-gates.md).

## The method used on itself, on a budget

The D1-D5A layout refactor reorganized the entire tree: phase directories moved to taxonomy homes under `planning/`, `evidence/`, and `tools/`. Every cross-reference was updated. A 45-row prefix table in `planning/PATH-REDIRECTS.md` maps every old path to its new location.

The refactor was run through the adversarial sprint method itself. When frontier budget was exhausted, the reviewer panel switched to `kimi-k3` and `minimax-m3` — Droid Core open models, not frontier tier, but distinct families. The method ate its own dog food, on a budget. Chunks D1-1 and D1-2a both required operator overrides after SPLIT verdicts. The framework's own rules held: same-family reviewers would have been refused, and they were not same-family, so the gate passed.

## How it ends (so far)

Phase 0 through 4.5 landed. Phase 5's enforcement layer is in progress. The repo has 233 tests, a command-orchestrated runner, a CI gate, signed chunk tokens, and a layout that survived its own method. The design that survives is smaller than the one that was specified: one hook that inspects reality, a hash lock the executor cannot influence, a cross-family panel where any REJECT blocks, and a token that does not exist unless the gate actually passed.

The four headline findings:

| Finding | Discovered | What it showed |
|---|---|---|
| Silent green | Aug 3 | The platform's default failure mode is reporting success for work that did not happen |
| Reference guard | Aug 3 | The session store is a shared surface; context isolation is real at the channel, absent at the filesystem |
| Fake pass | Aug 4 | A forged transcript passed every gate because `is_error=None` read as success |
| Model disagreement | Aug 7 | Two frontier models looked at the same failing test and returned opposite verdicts |

The Phase 0.5 manual harness — a hand-run seven-rung ladder — was superseded by the automated runner in Phase 4.5 and packaged as a demo script. It is still runnable for reproduction. It was the proof that the method worked before any code automated it.
