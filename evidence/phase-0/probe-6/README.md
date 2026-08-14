# Probe 6 — Plugin distribution boundary

**Verdict: PASS.** A single plugin carries the droid, the skill and the hook, and all three activate on install with no manual repo setup. This is the probe that makes the design shippable as one installable thing.
**Date:** 2026-08-03
**CLI under test:** `droid` 0.186.0 · **Host:** macOS (darwin 24.6.0)
**Scratch repo:** `/tmp/probe-6/repo` · **Plugin under test:** [`plugin/`](./plugin/) · **Marketplace:** [`plugin-marketplace/`](./plugin-marketplace/)
**Raw:** [`raw/`](./raw/) · **Reproduce:** [`run.sh`](./run.sh)

**Question:** which settings, hooks, and Mission artifacts are safely distributable inside a plugin?

## Result summary

A minimal plugin (`probe-guard`) was built with one of each component, published through a local marketplace, and installed at project scope.

| Component | Ships in plugin at | Activates on install? | Evidence |
|---|---|---|---|
| **Hook** (`PreToolUse`) | `hooks/hooks.json` | **Yes** | Canary logged 1 invocation on the run's `Execute` call |
| **Droid** (subagent) | `droids/probe-validator.md` | **Yes** | Appears in `subagent_type` list; invoked successfully via `Task` |
| **Skill** | `skills/probe-marker/SKILL.md` | **Yes** | Appears by name in the model's available-skills list |
| **Slash command** | `commands/probe-hello.md` | **Untested** | `/name` commands are interactive-only; `droid exec` has no surface for them |
| **MCP server** | `mcp.json` | **Not tested** | Out of scope for this design; no MCP dependency |

Install wrote exactly two things: `enabledPlugins` into the **project's** `.factory/settings.json`, and a cache copy under `~/.factory/plugins/cache/`. Nothing else in the repo was touched.

## The finding that matters: plugin hooks fire where project hooks do not

Probe 4 established that at project scope, **`.factory/hooks.json` is never read** — a `matcher: "*"` canary logged zero invocations from it, and only the `hooks` key in `.factory/settings.json` worked.

A plugin declares its hooks in a file called **`hooks/hooks.json`** — the same filename that does not work standalone. It fires:

```json
{"hook_event": "PreToolUse", "tool_name": "Execute", "cwd": "/private/tmp/probe-6/repo",
 "plugin_root_env": "/PLUGIN_ROOT_NOT_EXPANDED_ERROR", "ts": "2026-08-03T00:10:53"}
```

The repo's `.factory/settings.json` at that moment contained **only** `{"enabledPlugins": {"probe-guard@mkt": true}}` — no `hooks` key at all. So the invocation can only have come from the plugin's own `hooks/hooks.json`, through a separate loader.

This is good news and a trap. Good news: **the reference guard from Probes 2, 3 and 4 can ship inside a plugin**, which is what "installable product" requires. The trap: `hooks.json` works in one context and is silently ignored in the other, with no diagnostic either way. A developer who tests a guard standalone in `.factory/hooks.json`, sees nothing fire, and concludes hooks are broken will be wrong — as this repo's own Probe 4 was. The two paths must be documented together in anything we build.

### `${DROID_PLUGIN_ROOT}` expands in the command, but the env var is poisoned

The hook was declared as `python3 ${DROID_PLUGIN_ROOT}/hooks/canary.py`. It ran, so **substitution into the command string works**. But the script read its own environment and found:

```
DROID_PLUGIN_ROOT=/PLUGIN_ROOT_NOT_EXPANDED_ERROR
```

A literal sentinel, not a path. So a hook script that resolves sibling files at runtime via `os.environ["DROID_PLUGIN_ROOT"]` — an entirely reasonable thing to do, and the pattern the docs' own "use plugin-root variables" advice invites — gets a path that does not exist. It would fail, or worse, silently mis-resolve.

**Rule for anything we ship: pass the plugin root as an argument in the `command` string; never read it from the environment inside the script.**

## Droids and skills load, and droid tool restrictions are enforced

The plugin's droid appeared in the `subagent_type` registry alongside built-ins and the machine's personal droids, and the skill appeared by name. Neither needed a repo-local file or any manual step.

Invoking `probe-validator` via `Task` and asking it to attempt a write:

> PLUGIN_DROID_REACHED
> Available tools (exact names): `Read`, `Grep`, `Glob`, `TodoWrite`, `Skill`
> File creation attempt: I did not attempt to create [...] I have no write-capable tool available [...] There is no `Create`, `Edit`, `Write`, or shell/`Execute` tool through which a file could be created.

No file was created. This reproduces Probe 3's V9/V10 result — the `tools:` allowlist is enforced by **omission from the tool schema**, not by prompt — and extends it to a **plugin-shipped** droid, which was not previously established.

One detail worth carrying: the declared allowlist was `["Read", "Grep", "Glob"]`, and the droid actually received **five** tools — `TodoWrite` and `Skill` were added by the platform. The allowlist is a floor for write capability, not an exact manifest. Neither addition grants filesystem writes, so isolation holds, but **do not assume `tools:` is the complete list**; assert on what the subagent reports, as this probe did.

## Install, uninstall, and what gets left behind

| Step | Observed |
|---|---|
| `droid plugin marketplace add /tmp/probe-6/mkt` | Registered — **but keyed as `mkt`**, the directory basename, not `probe-mkt` from `marketplace.json` |
| `droid plugin install probe-guard@probe-mkt` | **Failed:** `Marketplace "probe-mkt" not found. Run /marketplace add first.` |
| `droid plugin install probe-guard@mkt --scope project` | Succeeded |
| `droid plugin uninstall probe-guard@mkt --scope project` | Succeeded; `enabledPlugins` emptied; canary logged **0** invocations on a subsequent run |
| `droid plugin marketplace remove mkt` | Succeeded |

**The marketplace naming mismatch is a real papercut.** The docs describe `marketplace.json`'s `name` as "Marketplace identifier," and plugin IDs as `pluginName@marketplaceName`. For a local path source the registry key is the *directory basename* instead, and the two are visibly different in `marketplace list` output:

```
mkt  (1 plugin)  local:/tmp/probe-6/mkt  "probe-mkt"
```

The error message compounds it by advising `Run /marketplace add first` for a marketplace that was just added successfully — it points at the wrong cause. Anyone following the docs' own local-testing snippet hits this. Minor, but it costs a debugging cycle and belongs in the upstream report.

**Uninstall is functionally complete but not tidy.** The hook stopped firing immediately, which is the part that matters. Two residues: `enabledPlugins` was left as an empty object `{}` rather than removed, and the plugin **cache directory survived** at `~/.factory/plugins/cache/mkt-<hash>/probe-guard-<hash>`. Neither is active. Similarly, `marketplace remove` left `"extraKnownMarketplaces": {}` in `~/.factory/settings.json` where no such key existed before.

This probe therefore did not leave the machine as it found it by default. User config was backed up before the install and **restored byte-identical afterward**, and the probe's own cache entry was deleted. Worth stating plainly because it is a distribution-relevant fact: **plugin operations mutate user-level config, and the cleanup is incomplete.** An enterprise rollout should expect config drift across install/uninstall cycles.

## Scope semantics

`--scope project` put `enabledPlugins` in the repo's `.factory/settings.json`. In this repo `.factory/` is gitignored (see [`../README.md`](../README.md)), so **a project-scoped plugin activation would not be committed** and each clone would need its own install. `--scope user` writes to `~/.factory/settings.json` instead, which is per-machine.

For team distribution the documented path is neither: `extraKnownMarketplaces` plus `enabledPlugins` declared in settings, where install scope follows where the setting is defined, with org-managed settings installing at org scope. That is the mechanism to target for a real rollout, and it is **untested here** — this probe only exercised the local-path marketplace and project scope.

## Design impact

1. **Ship as one plugin.** Droid, skill and hook all activate from a single install with no repo-local setup. The "installable product" story holds, which was the open question.
2. **Put the reference guard in `hooks/hooks.json` inside the plugin.** It fires there. Do not ship a standalone `.factory/hooks.json` and expect it to work — and if a repo-local guard is ever needed outside a plugin, it must go in `.factory/settings.json` under `hooks`.
3. **Never read `DROID_PLUGIN_ROOT` from the environment.** Pass it as a command argument. The env var is a sentinel string.
4. **Keep the install check from Probe 4.** It is now doubly justified: hook registration has two valid locations and one invalid-looking one that works only in plugin context. Assert a canary actually fired.
5. **Assert the subagent's real toolset** rather than trusting the `tools:` key, which is a floor rather than a manifest.
6. **Expect config drift.** Install/uninstall cycles leave empty keys and stale caches. If the plugin ever writes user config itself, it should be idempotent and clean up after itself, since the platform does not.

## Limits

| | |
|---|---|
| Not tested | Slash commands. `/name` is interactive-only and `droid exec` offers no way to invoke one, so the `commands/` component is unverified. It is not load-bearing for this design. |
| Not tested | MCP servers (`mcp.json`). No MCP dependency in the design. |
| Not tested | `--scope user`, and the `extraKnownMarketplaces` + `enabledPlugins` settings-driven team rollout — which is the mechanism an enterprise would actually use. Only local-path marketplace + project scope were exercised. |
| Not tested | Install from a **remote** git marketplace. Local path only, so clean-checkout install is unverified — the docs' own pre-share checklist calls this out, and it is the obvious next step. |
| Not tested | Whether plugin hooks fire on a **subagent's** tool calls. The canary logged the parent's `Task` call, but `probe-validator` made no tool calls of its own, so subagent hook coverage is **unresolved**. This matters for invariant #3 — a subagent that escapes a locked-test guard would be a hole — and should be settled before relying on it. |
| Not tested | Plugin hook precedence against a `settings.json` hook declaring the same event, and whether both run. |
| Single sample | One plugin, one install, one machine. |

## Relation to the other probes

- **Probe 4** is the reason this probe knew what to look for. The registration-channel result made `hooks/hooks.json` firing inside a plugin the headline question rather than an afterthought.
- **Probe 3**'s tool-restriction finding is confirmed for plugin-shipped droids, closing the gap between "works from `.factory/droids/`" and "works when distributed."
- **Probes 2, 3, 4** all converge on one reference guard; this probe establishes the vehicle that delivers it.
- **Probe 1** stays BLOCKED, and no Mission artifact was distributable to test, since missions do not execute at this version. Mission artifacts in plugins remain **unanswered by construction**, which is the honest state of the `Mission artifacts` half of this probe's question.
