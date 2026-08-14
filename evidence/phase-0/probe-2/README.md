# Probe 2 — Fallback safety and effective model resolution

**Verdict: CONDITIONAL PASS.** The abort mechanism is buildable and demonstrated. Getting there turned up a genuine silent-degradation defect in the platform.
**Date:** 2026-08-03
**CLI under test:** `droid` 0.186.0 · **Host:** macOS (darwin 24.6.0)
**Scratch repo:** `/tmp/probe-2/repo` (throwaway `git init`, one file)
**Raw:** [`raw/`](./raw/) · **Rig:** [`rig/`](./rig/) · **Reproduce:** [`run.sh`](./run.sh)

**Question:** can the plugin resolve *effective* model IDs at runtime and abort before a family-violating fallback occurs?

**Answer:** yes, with a hook — and the answer arrives in an unexpected place. The resolved model is **not** in the `droid exec` result envelope, but it *is* in the session transcript's startup context from turn 0, before any tool runs. A `PreToolUse` hook can read it there and deny. Two things qualify the pass: `--model auto` makes the family unknowable before the session starts, and an unsupported `--reasoning-effort` **silently resolves to `off`**.

## Where the resolved model is, and is not

| Surface | Contains resolved model? |
|---|---|
| `droid exec -o json` result envelope | **No.** Keys are `type, subtype, is_error, duration_ms, num_turns, session_id, result, usage`. `usage` has `input_tokens`, `output_tokens`, `cache_*`, `factory_credits`, `thinking_tokens` — and no model field. Checked on all 9 runs. |
| Session transcript, `message.modelId` | **Yes**, plus `message.reasoningEffort`. Per-message, so a mid-run change would be visible. (Method inherited from the Probe 3 addendum.) |
| Session transcript, **startup context** | **Yes** — the environment block injected before the first turn carries a `Model:` line, e.g. `Model: GPT-5.4 Mini`. |

That last row is the load-bearing one. It means the effective model is knowable **before any tool call executes**, not merely after the run. It also means the agent is told its own model, which is worth remembering when reasoning about what a validator can infer about its counterpart.

The absence from the result envelope is the real gap: **a caller that only reads `-o json` cannot tell which model ran.** Attribution requires reaching into `~/.factory/sessions/`, which is undocumented for this purpose, and which the Probe 3 addendum showed is also a confidentiality problem. Invariant #7 wants degradation to be explicit *to the caller*; today it is merely discoverable.

## Explicit pinning is honest; the two escape hatches are not

| Test | Requested | Resolved | Exit | Verdict |
|---|---|---|---|---|
| T1 | `--model definitely-not-a-real-model-9x` | — | **1** | **Fails closed.** `Invalid model:` plus the full valid list. No substitution. |
| T4 | `--model gpt-5.4-mini` | `gpt-5.4-mini` / `high` | 0 | exact |
| T3b | `--model claude-haiku-4-5-20251001 -r high` | `claude-haiku-4-5-20251001` / `high` | 0 | exact |
| **T3** | `--model claude-haiku-4-5-20251001 -r xhigh` | `claude-haiku-4-5-20251001` / **`off`** | **0** | ***silent degradation*** |
| T2 ×2 | `--model auto` | `gpt-5.6-luna` / `medium` (both runs) | 0 | resolved, but not predictable |

**T3 is a defect worth reporting.** Haiku 4.5 advertises `[off, low, medium, high]`; `xhigh` is not in its list. Asking for `xhigh` does not error, and does not clamp to the nearest supported value (`high`) — it resolves to **`off`**, the weakest setting available. The request was for maximum reasoning; the delivery was none; the exit code was 0 and nothing was printed. A validator pinned at `-r xhigh` against a model that does not support it would run with reasoning disabled, indefinitely, silently. This inverts the intent of the flag, and it is precisely the failure invariant #7 exists to prevent — a green check over a degraded run. Compare T3b, one flag value different, which resolves exactly as asked: the flag works, the *invalid* case is what degrades silently.

**T2 is the family risk.** `auto` resolved to `gpt-5.6-luna` on both runs, so it is not random here, but the caller cannot know the family before the session exists. A config that pins the executor to `claude-opus-5` and leaves the validator on `auto` would have satisfied invariant #1 today by luck; a router change, a capacity event, or a different prompt could put both roles in the same family with no signal. **`auto` is unusable for role-pinned work.** Pass explicit IDs.

## The abort mechanism works — T5 vs T6

A `PreToolUse` hook ([`rig/hook-family-gate.py`](./rig/hook-family-gate.py)) reads `transcript_path` from its stdin payload, extracts `message.modelId`, compares the family against `EXPECT_FAMILY`, and exits 2 on mismatch. It fails closed: if the model cannot be determined, it denies. Registered via `.factory/settings.json` per Probe 4.

| Test | Gate expects | Run resolved to | Tool calls | Outcome |
|---|---|---|---|---|
| **T5** | `claude` | `gpt-5.4-mini` | `Execute`, `LS` | **both denied**, `is_error: true` on each |
| **T6** | `claude` | `claude-opus-5` | `Execute` | **allowed**, normal `tool_result` |
| T7 | `claude` | `gpt-5.6-luna` (via `auto`) | `Execute` ×2 | **both denied** |

One variable between T5 and T6 — the resolved model — and the gate's decision follows it. The denial reaches the agent as a tool result:

```
Error: MODEL_FAMILY_VIOLATION: run resolved to 'gpt-5.4-mini' (effort 'high'),
expected family 'claude'. Aborting before any tool acts.
```

T7 is the useful one operationally: it catches the `auto` router putting a run in the wrong family, which is the exact scenario invariant #7 describes, and it catches it before the first tool acts.

So **the capability the probe asked for exists.** Not as a pre-flight caller-side check — as a per-tool-call gate that fires before any tool has an effect. For a plugin, that is close enough to the requirement: no file is written and no command runs under a wrong-family model.

## The catch, and it is the same catch as everywhere else in Phase 0

**T5 exited 0 with a confident final answer while every single tool call was denied.**

```
num_turns=3   is_error=False   exit=0
result: `a.txt`
```

The gate fired 4 times. The run reported success. The answer was even *correct* — and the model did not fabricate it: the startup context block includes `% ls` output, so it answered from context it was handed at session start rather than from the tool calls it was denied. That is a subtle and unpleasant combination. **A hook can block every action a run takes without changing the run's exit code or making the final summary look wrong**, because startup context is enough to produce a plausible answer to a shallow question.

An orchestrator that gates on `exit_code == 0` and reads `result` would conclude T5 succeeded. It must instead read the hook's own log, or check `is_error` on individual tool results in the transcript. This is the fourth appearance of the silent-green shape in Phase 0, after the mission no-op (Probe 1), the storage leak (Probe 3 addendum), and the misregistered hook (Probe 4). It is no longer a series of coincidences; it is the platform's default failure mode, and anything built here has to assume it.

Note also that `MODEL_FAMILY_VIOLATION` never reached the final `result` text, unlike Probe 4 where the agent quoted `SPEC_OR_TEST_BLOCKED` verbatim. Whether the contract surfaces in the summary is up to the model. **Do not rely on the agent to relay a block. Read the hook's log.**

## Design impact

1. **Pin explicit model IDs. Never `auto` for a role.** Invalid IDs fail closed (T1), and valid ones resolve exactly (T3b, T4), so pinning is trustworthy — the danger is delegation to the router.
2. **Validate `--reasoning-effort` against the model's advertised list before invoking.** The list is available for free from `droid exec --help` ([`raw/model-ids-0.186.0.txt`](./raw/model-ids-0.186.0.txt)). Do not pass a value the model does not support and assume clamping: T3 shows it resolves to `off`. This check belongs in the plugin's config loader.
3. **Ship the family gate as defense in depth**, reading `modelId` from `transcript_path`, failing closed. It is ~30 lines and it is the same primitive as Probe 4's locked-test guard and Probe 3's isolation hook — one reference guard, three policies.
4. **Never trust `exit 0` or the `result` string.** Assert on the hook log and on per-tool `is_error`. T5 is the demonstration.
5. **Record the resolved model in run evidence** by reading the session store, since the envelope will not tell you. Every probe from 3 onward now does this; it should be a helper the plugin owns rather than repeated per probe.

## Limits

| | |
|---|---|
| Not tested | A *real* fallback. No quota exhaustion, capacity error, or server-side substitution was induced — T2/T5 use `auto` and an explicit cross-family ID as **proxies** for a fallback. So "the gate catches a genuine mid-run downgrade" is inferred from "the gate reads `modelId` per message," not directly observed. Inducing a real fallback needs either a quota-exhausted account or vendor cooperation. |
| Not tested | Whether `modelId` can change **mid-session**. The hook re-reads on every tool call and takes the last value, so it would catch it, but no run exhibited a change. |
| Not tested | `SessionStart` / `Stop` hook events, which might allow a true pre-flight abort instead of a per-tool-call one. Only `PreToolUse` was exercised, here and in Probe 4. |
| Not tested | Custom / BYOK models (`custom:` prefix). `~/.factory/settings.json` has no `custom_models` entries on this machine, so `custom:` resolution is unmeasured — and a BYOK endpoint substituting a model server-side is the most plausible real-world silent fallback. |
| Sample | T2 ran twice and resolved identically. Two samples do not establish that `auto` is deterministic, and the recommendation does not depend on it. |
| Reasoning-effort scope | T3 was tested on one model with one unsupported value. Whether every unsupported value on every model degrades to `off`, or whether `off` was incidental, is unverified — but one reproducible instance is enough to stop trusting the flag. |

## Relation to the other probes

- **Probe 4** supplied the registration channel and the fail-closed discipline this gate is built on. Third policy on one primitive.
- **Probe 8** is the companion finding: there, a self-reported label was trusted; here, a silently downgraded reasoning effort is invisible. Both are cases of the platform's stated configuration differing from what actually ran, and both are caught by a hook that inspects reality instead of config.
- **Probe 1** stays BLOCKED, and this probe partially routes around it: `--worker-model` / `--validator-model` are mission-only flags, but per-role pinning can be achieved by invoking `droid exec` per role with explicit `--model`, then gating the family with this hook. That is the command-orchestrated contingency in §8, and Probe 2 shows its safety story is buildable without missions.
- **Probe 7 / H3** needs the resolved model recorded per role to attribute cost; recommendation 5 is the mechanism, and the envelope's `usage.factory_credits` is per-run, so per-role attribution requires one invocation per role.
