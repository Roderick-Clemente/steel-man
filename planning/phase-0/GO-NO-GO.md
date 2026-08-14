# Phase 0 — Go / No-Go

**Recommendation: GO, with one mandatory design change.**

Build it **command-orchestrated**, not Mission-native. Everything the method actually depends on is reachable today; the piece that is broken (`droid exec --mission`) is the piece §8 already had a contingency for.

**Date:** 2026-08-03 · **Scoped to `droid` 0.186.0**, macOS (darwin 24.6.0). Every claim below re-verifies with a `run.sh` under [`evidence/`](./evidence/). A CLI upgrade invalidates this document until the probes are re-run.

---

## The one-paragraph version

Factory cannot fail loudly. Four independent probes hit the same shape: a run that does nothing, a hook that never loads, a model quietly downgraded, every tool call denied — all reporting `exit 0`. That is the platform's default failure mode, and taken alone it would be a no-go for a method whose entire value is a gate you can trust.

But the same probes found one primitive that fixes it. A ~30-line `PreToolUse` hook that reads `transcript_path`, inspects what actually happened, and fails closed enforces **three** different invariants — locked tests, context isolation, and model-family separation — and detects the silent degradation the platform will not report. It ships inside a plugin and activates on install. That is a stronger position than hand-rolling orchestration from scratch, and it is the spine of the build.

---

## Invariant scorecard

| # | Invariant | Status | Basis |
|---|---|---|---|
| 1 | **Family separation** | 🟢 **via contingency** | Mission-level `--worker-model`/`--validator-model` are unusable (Probe 1). But explicit `--model` pins resolve exactly, and an invalid ID **fails closed** at exit 1 (Probe 2). Per-role pinning = one `droid exec` per role. The family gate hook verifies it at runtime. **Never use `--model auto`** — it resolved to a concrete model the caller cannot predict. |
| 2 | **Fresh review context** | 🟡 **enforceable, not default** | A custom Droid does get fresh context, but the executor's session is readable from `~/.factory/sessions/` with `Grep` alone, and independently via `droid search` (Probe 3 + addendum). Isolation holds only if a guard blocks those paths. Buildable with the same primitive. |
| 3 | **Independent test authorship** | 🟢 **conditional** | A hook blocks the agent's own `Edit` to a hash-locked test, the executor receives `SPEC_OR_TEST_BLOCKED` verbatim, and **the run continues** to act on it (Probe 4). Conditions are absolute: register via `settings.json` or a plugin, match `Execute`, and **fail closed** — miss any one and a `sed -i` walks straight through. |
| 4 | **Valid RED before GREEN** | ⚪ **unprobed, low risk** | Pure orchestration: run the test, capture the exit code, assert it failed for the expected reason. No platform capability is in question. Should still be built with the "never trust exit 0" rule. |
| 5 | **Immutable evidence** | 🟢 | The blocked attempt persists in two independent places: a hook-side log whose path the orchestrator chooses, and 3× in the session transcript (Probe 4, Test D). |
| 6 | **Blocking validation** | 🟡 **wrapper owns it** | Mission rejection routing was never reachable (Probe 5, blocked by Probe 1). In a command-orchestrated design the wrapper owns the state machine, so this is our code, not a platform feature. Cost is real but bounded. |
| 7 | **Explicit degradation** | 🟡 **only if we build it** | The platform actively violates this: `-r xhigh` on a model that does not support it silently resolves to **`off`** at exit 0 (Probe 2). Four silent-green instances total. Recoverable, because the family gate detects wrong-model runs before any tool acts — but the detection is ours to write. |
| 8 | **Human merge** | 🟢 | Git-level, no platform dependency. |

**Nothing is red.** Three green, three amber that are green once the guard exists, one unprobed and low risk.

---

## Why the design must change

`droid exec --mission` performs no work and reports success — 0 turns, 0 tokens, exit 0 (Probe 1). That single defect blocks Probes 5 and 7 and removes the Mission-native path, because the per-role model flags (`--worker-model`, `--validator-model`) are *only valid with* `--mission`.

The §8 contingency stands up cleanly:

| Mission-native assumption | Command-orchestrated replacement | Verified by |
|---|---|---|
| Per-role model pinning via mission flags | One `droid exec --model <id>` per role | Probe 2 (T3b, T4) |
| Mission validation stage routes rejection | Wrapper owns the state machine | — (our code) |
| Mission artifacts capture the run | Hook-side log + session transcript | Probe 4 (Test D) |
| Per-role usage attribution | `usage.factory_credits` is **per run**, so one invocation per role attributes cleanly | Probe 2 |

That last row is worth calling out: **it partially unblocks Probe 7 and hypothesis H3.** Per-role cost attribution was thought to depend on missions. It does not — invoking once per role gives per-role credits directly in the result envelope.

---

## The reference guard

One primitive, three policies. Write it once.

```
PreToolUse hook
  ├── registered in .factory/settings.json (hooks key) or a plugin's hooks/hooks.json
  ├── matcher covers Edit|Create|ApplyPatch|Execute
  ├── reads transcript_path to learn what actually happened
  ├── FAILS CLOSED on any payload it cannot interpret
  └── emits a contract string on stderr, exit 2 → delivered to the agent, run continues
```

| Policy | Denies when | Invariant |
|---|---|---|
| Locked-test guard | target path (or a shell command mentioning it) is a hash-pinned test | #3 |
| Isolation guard | command touches `~/.factory/sessions` or invokes `droid search` | #2 |
| Family gate | `message.modelId` is outside the expected family | #1, #7 |

Each was demonstrated working. The family gate is the one to internalise: it reads the resolved model from the transcript's **startup context**, available from turn 0, so it denies **before any tool acts**.

### Five rules that are not optional

1. **Register hooks in `.factory/settings.json` or inside a plugin.** A standalone project `.factory/hooks.json` is silently never read — that trap produced a wrong verdict in this repo (Probes 4, 6).
2. **Fail closed.** A guard keying on `file_path` saw `Execute`'s `command`, understood nothing, exited 0, and the locked file was overwritten (Probe 4, A4).
3. **Match `Execute`.** Path matching alone is one shell call away from bypass.
4. **Never trust `exit 0` or the `result` string.** A run whose every tool call was denied still exited 0 with a plausible answer, sourced from startup context (Probe 2, T5). Assert on the hook log and per-tool `is_error`.
5. **Prove the hook fired.** Install a canary and assert it logged. Configuration being present is not evidence of enforcement.

---

## What Phase 0 also says about the product thesis

The probes double as a platform evaluation, and two findings cut against relying on the platform's own controls for adversarial separation:

- **Autonomy tiers gate on a self-report.** Every `Execute` carries the model's own `riskLevel`, and the tier acts on it. The same `rm scratch.txt` was labelled `high` unprompted and `medium` once the prompt offered a soothing rationale (Probe 8). It never reached `low` across four framings — but that is *this* model's calibration, not an enforced property, and a cheaper executor is exactly what H3 proposes. Use tiers for blast radius, hooks for security. (Open question: the tier may classify independently with the label riding along. Unresolvable from outside the CLI — **ask Factory** before asserting this publicly.)
- **`--auto low` is effectively read-only** for the shell: even appending one line to a new file was refused (Probe 8, T7). A good default for validators and reviewers.

---

## Report upstream

Five defects worth filing, all with reproductions committed:

| # | Defect | Severity |
|---|---|---|
| 1 | `droid exec --mission` is a no-op reporting success (0 turns, 0 tokens, exit 0) | **High** — blocks the entire mission surface |
| 2 | Project `.factory/hooks.json` is silently never read, though documented as the primary location | **High** — a security control that appears installed and is not |
| 3 | Unsupported `--reasoning-effort` resolves to `off` rather than erroring or clamping | **High** — silent maximum-to-minimum degradation |
| 4 | `DROID_PLUGIN_ROOT` env var handed to plugin hooks is the literal sentinel `/PLUGIN_ROOT_NOT_EXPANDED_ERROR` | Medium |
| 5 | Local marketplace keyed by directory basename, not `marketplace.json`'s `name`; error message misdirects | Low |

Common thread across 1–3: **the failure is indistinguishable from success at the exit code.**

---

## Exit criteria

| Criterion | Status |
|---|---|
| Minimal plugin scaffold that installs cleanly | ✅ Probe 6 |
| Two cross-family read-only Droids | 🟡 Components proven separately — read-only enforcement (Probes 3, 6) and cross-family pinning (Probe 2) — but not yet stood up as a pair |
| One hook that provably blocks a locked-test edit | ✅ Probe 4 (A5, with the bypass in A4 as the counterexample) |
| One captured run artifact under `evidence/` | ✅ Six probe directories |
| Written go/no-go on Factory-native orchestration | ✅ This document — **no to Mission-native, yes to command-orchestrated** |

---

## Build order for Phase 1

1. **The reference guard**, with its canary-based install check. Everything depends on it.
2. **The per-role invocation wrapper**: explicit `--model` per role, reasoning effort validated against the model's advertised list, resolved model recorded from the session store, family gate attached.
3. **Locked-test enforcement** on top of the guard.
4. **Isolation guard** for `~/.factory/sessions` and `droid search`.
5. **The rejection state machine** — our code, since missions cannot provide it.

Do not start 3–5 before 1 is proven firing in the target repo.

---

## Known unknowns

Recorded so they are not mistaken for settled:

- **No real fallback was induced.** Probe 2 used `--model auto` and an explicit cross-family ID as proxies. Quota exhaustion and server-side substitution are untested, and **custom/BYOK endpoints are the most plausible real silent fallback** and were not measured at all.
- **Whether hooks fire on a subagent's tool calls is unresolved** (Probe 6). If they do not, a subagent is a hole in invariant #3. Close this early — it is cheap.
- **Whether the autonomy tier truly reads the self-declared `riskLevel`** or classifies in parallel. Changes how strongly Probe 8's caveat should be stated.
- **`PostToolUse`, `Stop`, `SubagentStop` are unmeasured.** Only `PreToolUse` was exercised, and `SubagentStop` is the natural place to validate a validator's output.
- **Interactive vs `exec` mode.** Every probe used `droid exec`. Hook loading may differ interactively.
- Probe 8 measures **model calibration**, so it must be re-run per executor model rather than treated as a platform property.

---

## Bottom line

The method survives Phase 0. It does not survive it on the platform's own guarantees — it survives because one small, well-specified guard can verify reality where the platform reports success regardless. Build that guard first, distribute it as a plugin, and treat every green check as unproven until something we wrote has asserted it.
