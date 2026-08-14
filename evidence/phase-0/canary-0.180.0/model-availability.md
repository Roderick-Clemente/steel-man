# Model availability at `droid` 0.180.0

**Date:** 2026-08-03 · **Host:** macOS Darwin 25.5.0 · **CLI:** `droid 0.180.0`

## Finding

Of the cheap-tier models requested for the cross-family executor
(Kimi, GLM, DeepSeek, Qwen, Grok), **none resolve at 0.180.0**. The
only models that resolve are:

| `droid exec --model` | Status | Family | Source |
|---|---|---|---|
| `claude-opus-5` | VALID — present and is the **default** | Anthropic Claude | default `--model` |
| `gpt-5.4-mini` | VALID | OpenAI GPT | cross-family cheap, used in [Probe 2](../../README.md#probe-2--fallback-safety) |
| `gpt-5.6-luna` | VALID | OpenAI GPT | also referenced in [Probe 2](../../README.md) |

## Models requested, **rejected as invalid** at 0.180.0

```
kimi-k2 · kimi-k2-thinking
glm-4.5 · glm-4.6
deepseek-r1 · deepseek-chat · deepseek-v3 · deepseek-v3-1
qwen-coder · qwen3-235b-a22b · qwen3-235b
gpt-oss-120b · gpt-oss-20b
grok-4 · grok-4-fast
mistral · mixtral · mistral-large · mistral-small
haiku · codestral · devstral · nemotron · dbrx · cerebras
gemini · phi · llama · llama-3.3 · minimax · chatgpt
gpt-5 · gpt-5-mini · gpt-4o · sonnet
claude-3 · claude-3.5 · claude-3.7
claude-sonnet-4 · claude-sonnet-4.5
claude-haiku-3 · claude-haiku-3.5
claude-haiku-4 · claude-haiku-4.5
claude-opus-4 · claude-opus-4.5 · claude-opus-5-mini
openai/o · openai/gpt-5 · openai/gpt-5-mini · openai/o4 · openai/o4-mini · openai/o3
```

Every entry above returns `Invalid model: <id>` with the follow-on line
`Available built-in models:` followed by **nothing** (the CLI declines
to enumerate the available list to a bad ID probe).

## How this was tested

Probe mechanism: `droid exec --list-tools --model <id> --auto low 2>&1`.
A valid model ID returns `Available tools for <friendly-name>` and exits.
A bad ID returns `Invalid model: …`.

Cost: each probe is one CLI call which early-fails before any model
invocation, so credit spend on the enumeration probe is negligible but
non-zero on some probes that timed out before a fast-fail.

## Why this matters

1. **The A4 reproduction in this directory used `gpt-5.4-mini`**, which is
   the cheapest cross-family model available at 0.180.0. The user's
   request was for a Kimi / GLM / DeepSeek executor. None of those exist
   in the 0.180.0 surface. If the A4 reproduction is repeated on a
   version that exposes those models, the result **may move** because
   different non-Opus executors have different "polite refusal"
   calibration. The finding here is therefore not that the matcher gap
   is *proven* on all cheap models — only on the cheapest available
   cross-family model.

2. **Phase 0's family-gate primitive does not depend on which cheap
   model resolves** — the gate denies on `transcript_path`'s resolved
   model ID, not on the requested one. So the cross-family pairing
   mechanic is unaffected; what changes between versions is which
   cheap models are available for routine adversarial pairing.

3. **Probe 7 / H3 evaluation** should record the *enumerated* cheap
   model set used at evaluation time. Comparison across versions
   requires either a stable model set or an explicit enumeration per
   version. There is no current CLI command that lists models from
   outside the binary's own network calls; the way to enumerate is
   `--list-tools --model` probes. Cheap but no absolute source of truth.

## What we did NOT test

- We did not probe every plausible ID variant — only the most likely
  / most-named. Naming conventions for cheap-tier providers are not
  standardized across the platform surface.
- We did not test BYOK / custom endpoints, where the model list is
  whatever the user has configured.
- We did not confirm that the resolved `gpt-5.6-luna` is meaningfully
  cheaper than `gpt-5.4-mini` (both resolved "VALID" but cost data
  was not captured).

## Source

The enumeration was driven by the cross-validation goal: re-run the
[A4 bypass reproduction](./a4-bypass-reproduction.md) with a non-Opus
executor to *force* the matcher gap to surface, since the default
`claude-opus-5` declined pre-tool (Probe 8 calibration). The cheapest
available differently-family'd model at this version is
`gpt-5.4-mini`, which is what was used.
