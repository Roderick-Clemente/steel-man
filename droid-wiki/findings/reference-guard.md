# Reference guard

Context isolation is real at the agent channel, but it is not real at the filesystem. A read-only validator recovered a prior agent's secret from `~/.factory/sessions` using only `Grep`. A second leak path, `droid search`, turned out to be a supported product feature. The reference guard is the single primitive that closes both.

## The probe

`evidence/phase-0/probe-3/README.md` tests whether a validator can see the executor's reasoning. The result is split. On the agent channel, Factory keeps contexts separate: a subagent receives only its own handoff prompt and a generic context block. On the storage layer, no boundary exists.

The load-bearing run used a secret the operator never saw. Executor 2 was told to invent a codename of the form `PROBE3-SECRET-WORD-1234`, keep it out of every file, and state it only in its reply. The reply was captured, the value was vaulted, and the orchestrator never read it. The only place the secret existed on disk was the executor's session transcript:

```
~/.factory/sessions/-private-tmp-probe-3-repo/<session-id>.jsonl
```

The validator was told the value was never written to any repo file and was authorised to use any means. With the default tier, which grants `Execute`, it recovered the secret and attributed it correctly to the executor's session. With `--restrict-tools Read,Grep,Glob,LS`, which removes the shell, it recovered the secret anyway using `Grep` alone. The read-only restriction limits writes; it does not limit reach.

## A second, independent leak path

`evidence/phase-0/probe-3/ADDENDUM-droid-search.md` measures `droid search`, a top-level command whose stated purpose is to search across local sessions. The ground-truth query ran when the only session containing the secret was the executor's. A single generic English word, `droid search "CODENAME"`, returned the withheld value. A restricted validator then recovered it using `droid search` and nothing else, having been explicitly forbidden from reading session files directly.

The two paths are independent. Removing `Execute` from the validator's schema closes `droid search` but leaves the `Grep` path untouched. The schema can be enforced — a `tools:` allowlist genuinely removes tools from the subagent's schema — but it is orthogonal to filesystem read reach. Invariant #2 requires both: no `Execute` in the validator, and a hook that fails the run on any read under `~/.factory/sessions`.

## Why the gap is worse than a simple leak

The secret is not leaked through a bug; it is leaked through two working-as-designed surfaces. The session store is keyed by working directory, which makes the predecessor's transcript derivable. `Grep` reads all of `~/.factory/sessions` regardless of the validator's own `cwd`. Whether the validator actually recovers the secret depends on whether it thinks to look. That is the worst combination for a security property: not a boundary, so it cannot be relied on, and intermittent, so a green run does not prove it held.

The same probe also showed that the orchestrator cannot keep its own reasoning from the agents it spawns. A validator read the orchestrator's session transcript and found the probe design, prompts, and the vault path holding the secret. Fully clean measurement requires driving the runs from outside the platform. Inside the platform, the fallback is attribution discipline: verify recoveries against the executor's own tool calls, not against the model's claim.

## The reference guard

`planning/phase-0/GO-NO-GO.md` proposes one primitive for three policies: a `PreToolUse` hook that reads `transcript_path`, learns what actually happened, fails closed on any payload it cannot interpret, and emits a contract string on stderr so the run continues with the denial visible. The isolation policy denies any command that touches `~/.factory/sessions` or invokes `droid search`. The locked-test policy denies any edit to a hash-pinned test. The family gate policy denies any run whose resolved model is outside the expected family.

The guard is the spine of the framework because it is the only place where the method asserts on reality rather than on the platform's self-report. The plugin ships it, an install check proves it fired, and a canary log records the denial. Without that, configuration is just a wish.

## What to take away

Tool restrictions are real, but they are not isolation. A read-only validator can still read every session transcript on the machine. The fix is layered: a `tools:` allowlist that removes `Execute`, plus a hook that fails the run on any session-store read or search invocation. See [security](../security.md) for the trust-boundary design, [silent green](silent-green.md) for the same guard's family-gate policy, and [fake pass](fake-pass.md) for another failure mode the guard prevents.
