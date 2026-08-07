# Execute-tool cadence (rate-limit + result-cache awareness)

> **Status — PARKED in Phase 5 (hardening).** Not pulled forward into active
> phases. The wrapper (`tools/exec-cadence.sh`) and this convention doc are
> inventory only: they are not in `AGENTS.md`, not on `$PATH`, not aliased,
> and not lit up by any active-phase workflow. **Do not** route `Execute`
> calls through `tools/exec-cadence.sh` today; if a rate-limit trip becomes
> a recurring failure, promote this convention with a separate commit and
> update AGENTS.md to wire it in. The decision rule for promotion is "we
> have tripped the platform rate-limit twice in a 10-session window and
> retry was blocking progress", not "we have one cancelled tool call".

This is the operational convention for the `Execute` tool in `droid` sessions. PRD §11 Phase 5 lists it as hardening scope; this file specifies the standing rule.

## Rule

When chaining more than one `Execute` invocation inside a single agent turn, or when an `Execute` call is part of a multi-step smoke battery, route it through `tools/exec-cadence.sh`:

```
bash tools/exec-cadence.sh <original-execute-cmd>
```

The wrapper runs three checks in order, each addressing a different failure class:

### 1. CACHE LOOKUP (don't redo work)

The wrapper hashes the argv, computes a 16-char SHA-256 prefix, and checks `$DROID_CADENCE_CACHE_DIR/$argv_hash` (default `~/.factory/cadence-cache/`). If the same argv produced a non-empty, exit-0 result in the recent past (default 1 hour), the wrapper replays the cached output and exits 0 *without re-running the command*. The cadence log records a sentinel line `<unix_ts> 0 CACHED:<hash>` so the postmortem can tell apart real calls from cache hits.

This is the "no redo work" guarantee. A platform-side cancellation followed by retry does not trigger a redundant re-run when the wrapped command is idempotent.

**Default ON. Disable with `DROID_CADENCE_CACHE=0` for stateful commands** — anything that has side effects on disk or remote:

- `git push`, `git commit`, `git merge` (unless in dry-run form)
- `npm install`, `pip install`
- `rm`, `mv` touching things outside the repo (cache, logs)
- Anything touching a write-CI/CD target

The default suffices for read-only smoke calls (`git log`, `git status`, `python3 -m py_compile`, aggregate scripts, `wiki-link-audit.py`).

### 2. PREVENTIVE THROTTLE

If the cache missed, the wrapper enforces a minimum interval since the last wrapped call (default 12s, `DROID_CADENCE_INTERVAL`). This keeps our agent-side rate predictable from the platform's budget window.

Skip with `DROID_CADENCE_SKIP=1` for real-time operator commands where the human typed the call and should not wait.

### 3. REACTIVE RETRY

If the wrapped command exits with `124` (timeout), `137` (SIGKILL), or `143` (SIGTERM), or returns an empty stdout (the cancellation fingerprint in this CLI — the response literally says "Tool execution was interrupted"), the wrapper retries up to `DROID_CADENCE_RETRY_MAX` times (default 3) with linear backoff (5s, 10s, 15s).

The retry path re-runs the command. **The cache check is at the wrapper's outer loop; an empty-stdout cancel never populates the cache.** This is correct — we do not want to "cache" a partial-and-then-cancelled result.

The retry count is bounded because a hard block is a hard block; spinning does not unblock.

## Defaults that worked in the testing above

For read-only smoke batteries (`git log`, compile checks, audit scripts), the defaults produce:

- **Cache hit** when argv already ran recently — instant.
- **Throttled wait** when budget is tight — sleeps until the 12-s window opens.
- **Retry on cancel** — backoff 5–15 s, attempts 1/3 → 2/3 → 3/3.

For stateful commands, set `DROID_CADENCE_CACHE=0` to disable the cache lookup.

For real-time operator commands (`ExitSpecMode`, `ApplyPatch`, single-shot `Read` checks), leave the cache ON and skip the throttle: `DROID_CADENCE_SKIP=1`.

## What is NOT in scope here

- Re-implementing `droid exec`'s scheduler. Agent-side, not platform-side.
- Cross-family review cadence. Reviews are bulk invocations; if cancelled, refire the whole prompt — not retry mid-stream, which would lose reviewer context.
- Cache invalidation on the wrapped command's inputs changing. Right now we hash argv only; if two calls have the same argv but check different state (e.g., `git diff HEAD~1 HEAD` against two different HEADs), they will share a stale cache. The default 1-hour TTL bounds this; for state-anchored commands, the cache TTL can be tightened with `DROID_CADENCE_CACHE_TTL=0`.

## Diagnostic

`tail -n 20 ~/.factory/cadence.log` shows the last 20 invocations. Format: `<unix_ts> <exit_code> <argv0>` for real calls, `<unix_ts> 0 CACHED:<hash>` for cache hits.

`ls -la ~/.factory/cadence-cache/` lists cached argv hashes with mtimes. If a hash shows up repeatedly with successful exit codes but the next cross-family review cancels, the cancellation was on a different tool — `Read`, `Edit`, etc. — and the wrapper here does not cover it. Coverage is `Execute` only.

If the same argv keeps hitting a fresh cache (`CACHED:<hash>` never appears), the wrapper is not being used — install it as the default before launching long smoke batteries:

```
export PATH="$PWD/tools:$PATH"
alias drun='bash tools/exec-cadence.sh'
```
