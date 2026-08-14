# Canary at `droid` 0.180.0

A cross-validation run of the Phase 0 primitives on a droid version **6
patch releases older** than the Phase 0 baseline (0.186.0). The point of
running this is not to repeat the probes as new findings — Phase 0 already
owns those — but to confirm that the load-bearing primitives the GO/NO-GO
recommendation rests on **still exist** on a slightly older CLI, and to
surface any delta (positive or negative) that sits between the two
versions.

## Environment under test

| | |
|---|---|
| `droid --version` | **0.180.0** |
| Host | macOS Darwin 25.5.0, arm64 (case-sensitive) |
| Pilot scratch | `~/work/canary-target`, `~/work/blocker-target` |
| Local marketplace | `~/work/canary-marketplace` (probe-guard) |
| First probed | 2026-08-03 |

Phase 0 baseline [GO-NO-GO](../../GO-NO-GO.md) was scoped to `droid`
**0.186.0** on macOS darwin 24.6.0, with `~/Work/QuantumBank` as the pilot
repo. Re-run any probe from this directory only against the version above.

## Claim

This is a **cross-validation**, not a replication. Phase 0's verdict —

> Build command-orchestrated, not Mission-native. All eight invariants
> are reachable today.

— is the result. This directory tests whether the two primitives that
make that verdict load-bearing — **the plugin hook-fires-from-package**
primitive (Probe 6) and **the hash-locked-test block** (Probe 4) —
still hold at 0.180.0 with no rescue modifications. Both hold. One
defect from GO-NO-GO.md (#2 — `.factory/hooks.json` silently never read)
**does not reproduce** at 0.180.0 and **does reproduce** at the Phase 0
baseline 0.186.0 — i.e., it ran a regression in the **opposite** of the
direction this run would imply if read alone. Cross-referenced
artifact: [`factory-credits-none.md`](./factory-credits-none.md) records
a second drift between 0.180 and 0.186.

## Two numbering schemes — **do not collapse them**

A given finding has two stable identifiers because the source-of-truth
for each is different:

| Scheme | Canonical source | Currently assigns `.factory/hooks.json` … |
|---|---|---|
| Repo defect-N | [`phase-0/GO-NO-GO.md`](../../GO-NO-GO.md) §"Report upstream" and [`droid-wiki/background/open-questions.md`](../../../droid-wiki/background/open-questions.md) §"Defects observed during Phase 0" | **#2** |
| GitHub issue-N | External upstream tracker | **#3** |

Both schemes are **real and current**. They disagree because they index
different things — the repo's defect lists are an internal numbering of
findings produced during Phase 0; the GitHub issues are external-facing
upstream reports that may have been filed in a different order, against a
different surface, or with a different scope. **Nothing in this
directory renumbers, reorders, or re-labels either scheme.** The
discrepancy is recorded here so future cross-reference work does not
silently break by assuming the two schemes converge.

## Artifacts in this directory

| File | What it proves |
|---|---|
| [`tier-A-ledger.md`](./tier-A-ledger.md) | Pass / fail / version-divergent per primitive, in one table |
| [`a4-bypass-reproduction.md`](./a4-bypass-reproduction.md) | Probe 4 A4 reproduced on this CLI with a non-Opus executor — matcher gap is load-bearing |
| [`factory-credits-none.md`](./factory-credits-none.md) | `usage.factory_credits` field is **absent** in the `droid exec -o json` envelope at 0.180.0; the per-role cost attribution that Probe 2 cited is shape-shifted |
| [`model-availability.md`](./model-availability.md) | Of the cheap-tier models (Kimi / GLM / DeepSeek / Qwen / Grok) requested, only `gpt-5.4-mini` and `gpt-5.6-luna` resolve at 0.180.0; this run used `gpt-5.4-mini` for the cross-family executor |
| [`upstream-comment-draft.md`](./upstream-comment-draft.md) | Draft for review. **Not sent.** Combines the A4 reproduction, the regression timeline, and the `factory_credits` envelope change into one comment suitable for the upstream report. Every claim is version-stamped |

## Provenance

All five artifacts are written to be:

- **Version-stamped**: every claim that depends on a CLI behaviour
  carries the version it was observed under.
- **Reproducible from a clean shell**: SHAs and resolved-model IDs are
  recorded exactly as observed, not paraphrased.
- **Diffable against Phase 0**: the structure of each test mirrors the
  probe it cross-validates so any future maintainer can read across to
  the Phase 0 evidence side-by-side.
- **Reversible**: this branch was created off `main` and committed in
  five separate commits, one per artifact, so a bad write can be
  reverted with `git reset` per commit without losing the others.

## Relation to GO/NO-GO

No verdict in [`phase-0/GO-NO-GO.md`](../../GO-NO-GO.md) is **changed**
by this directory. The possibilities this run surfaces are:

1. Confirm a primitive still holds → reinforces the existing verdict.
2. Confirm a defect → adds evidence to a defect already filed.
3. Reveal a drift between 0.180 and 0.186 → adds a new note under the
   defect that surfaces "the failure is indistinguishable from success at
   the exit code."

This directory contains examples of all three.
