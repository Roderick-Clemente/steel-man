# Phase 0 Evidence

Committed evidence for the Phase 0 probes. One directory per probe: `probe-4/`, `probe-1/`, and so on.

## Why this exists rather than `.factory/`

PRD §9 nominates `.factory/adversarial-sprints/<run-id>/` as the default artifact path, but `.factory/` is gitignored here as local tool state. Evidence written there would be invisible to git, and Phase 0's exit criteria requires a *captured* run artifact. §9 permits "another configured artifact path"; this is it, for Phase 0.

This does **not** settle the §16 open decision about artifact paths and retention for repos that should not commit run evidence. That is a product question about arbitrary target repos. This is a local choice for this repo's probes.

## What a probe record needs

A probe result is version-scoped and unfalsifiable without provenance. Each directory should carry:

- the exact commands run, with exit codes
- raw stdout/stderr, secret-filtered
- the `droid --version` under test, since a "no" recorded against no version cannot be rechecked later
- resolved model IDs where the probe touches model selection, not the requested IDs

Negative results matter most and get the same treatment as positive ones. A probe that fails is the artifact, not a missing artifact.

## Reproducing

Prefer a committed script over prose instructions. If a probe cannot be re-run from what is in its directory, it is a claim rather than evidence.
