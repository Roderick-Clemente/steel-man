# How to contribute

There are two ways to engage with this repo, and they suit different people. You can help build the framework itself, or you can take the method home and run it against your own project. Both are welcome, and neither requires permission to start.

This is a multi-model adversarial coding framework. The interesting part is not the code, it is the discipline: independent model families review each other's work, every chunk close is gated by a signed token, and a clean run is treated as data rather than proof. If that sounds like something you want to poke at, read on.

## Contribute to the framework

The framework lives at `/Users/factory/work/adversarial-sprint-dev`. It is a normal Python repo with a test suite, a runner, and a set of gates. If you can write Python and read a spec, you can work here.

Start with [getting started](../overview/getting-started.md) to clone and run the suite. Then read [development workflow](development-workflow.md) for the branch-by-author convention, the commit body recipe, and how the three agents hand work off to each other. The [testing](testing.md) page explains what the 233 tests actually cover and how to run them.

The repo is organized by kind, not by phase. Code is in `tools/`, plans in `planning/`, evidence in `evidence/`. The [architecture](../overview/architecture.md) page has the full tree. Before you change a gate or a path constant, read [patterns and conventions](patterns-and-conventions.md), which summarizes the operating rules and the commit-body format every model-carrying commit needs.

Good first contributions: a new adapter in `tools/adapters/` for a CLI other than Factory, a plan-lint rule in `tools/plan-lint.py`, or a test that pins a behavior you found surprising. The [findings](../findings/index.md) pages are full of behaviors worth pinning.

## Adopt the method on your own project

You do not need to modify this repo to use it. The framework ships a per-pilot overlay you drop into your own repo, and from there one command fires the runner.

Read [adopting the method](adopting-the-method.md) for the full setup: copying the overlay templates, editing the config, setting your signing key, and choosing a run mode. You need a pilot repo with its own tests, API keys for the model families in your panel, and the `droid` CLI installed. A dry-run wiring test costs no model credits and is the recommended first step.

If you want to understand what the runner is doing before you point it at your code, read [the sprint loop runner](../features/sprint-loop-runner.md) and the operating rules in `tools/OPERATING-RULES.md`.

## The short version

Clone, run `python3 -m pytest -q`, pick a path above, and jump in. The repo's thesis is that independent reviewers catch what a single reviewer misses, so the bar for a contribution is not perfection, it is that the work survives review by a different model family than the one that wrote it.
