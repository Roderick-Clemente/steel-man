# `usage.factory_credits` envelope shape — drift between 0.180 and 0.186

**Date:** 2026-08-03 · **Host:** macOS Darwin 25.5.0 · **CLI:** `droid 0.180.0`

## Finding

At `droid 0.180.0` the `droid exec -o json` envelope does **not** carry a
`factory_credits` field inside `usage`. Observed envelope shape from a
trivial sanity run:

```json
{
  "duration_ms": …,
  "is_error": false,
  "num_turns": 1,
  "result": "Done.",
  "session_id": "…",
  "subtype": "success",
  "type": "result",
  "usage": {
    "input_tokens": …,
    "output_tokens": …,
    "cache_read_input_tokens": …,
    "cache_creation_input_tokens": …
  }
}
```

There is **no `factory_credits` key** at any level of the envelope.

## Why this matters — Probe 2 cites this field

[Probe 2's result](../../README.md#probe-2--fallback-safety) and the
[Phase 0 GO/NO-GO §"Why the design must change"](../../GO-NO-GO.md) both
rest on a specific claim:

> `usage.factory_credits` is **per run**, so one invocation per role
> attributes cleanly.

The concrete value Probe 2 captured (quoted in
[`droid-wiki/probes/index.md`](../../../droid-wiki/probes/index.md)):

> Probe 4's canary run, in `phase-0/evidence/probe-4/reverify/raw/canary-run.json`,
> reports `"usage": {"input_tokens": 4, "output_tokens": 193,
> "cache_read_input_tokens": 15786, "cache_creation_input_tokens": 15971,
> "factory_credits": 45023}`.

At **0.186.0** the field is present and integer-valued. At **0.180.0** the
field is **absent entirely**.

## Implications

This is a second axis of drift between 0.180 and 0.186.0, on top of:

- The `.factory/hooks.json` path (was a working loader at 0.180; silent at 0.186) — see [`tier-A-ledger.md`](./tier-A-ledger.md) Primitive 3.
- The `DROID_PLUGIN_ROOT` env var in plugin hook scripts (still poisoned with `/PLUGIN_ROOT_NOT_EXPANDED_ERROR` at 0.180 — see Primitive 1).

The drift specifically:

- Partially blocks Probe 7 (per-role usage attribution). Phase 0 marked Probe 7 **partially unblocked** by Probe 2's `factory_credits` finding. If the field was renamed/removed/moved between 0.180 and 0.186, then any per-role cost-attribution design that worked at 0.186.0 may not work at 0.180.0 — and we have no record that it was ever re-verified at a different invocation path or that `factory_credits` is the canonical name across the surface.
- Touches H3 (the "role-tiered models cut cost without cutting task success" hypothesis). H3 is unmeasurable without per-role attribution. The Phase 0 evaluation design says "real numbers, not 'roughly 50% cheaper'." If `factory_credits` is not stable across patch versions, that evaluation design is fragile.

The version-stamp rule from [`phase-0/evidence/README.md`](../README.md)
applies: any new probe or per-role attribution test should capture and
display the **envelope field name** it relied on, not just the value, because
field names are not themselves stable across the 0.180 → 0.186 spread.

## What we did not test

We did not exhaustively map the envelope — only the `usage` sub-dict was
inspected, because Probe 2's claim is specifically about that field. A
broader envelope diff between 0.180 and 0.186 (other top-level keys,
nested structures) was not produced. That is a possible follow-up but not
required for this finding.

## Provenance

This came from the sanity-check run that preceded the A4 bypass
reproduction:

```
$ droid exec --output-format json --model gpt-5.4-mini --auto low \
    "Run \`echo hello_mini\` with the Execute tool."

python → parse → usage.factory_credits == None
        keys(result) == ['duration_ms', 'is_error', 'num_turns',
                         'result', 'session_id', 'subtype', 'type',
                         'usage']
```

Single sample. Cross-validation against Phase 0's captured raw envelope
is the basis for the version-stamp claim.
