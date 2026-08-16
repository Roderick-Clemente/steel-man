# Security

Security in this project has two meanings that share a fence but answer different questions. The first is about what may be written into a repo that is assumed public from day one. The second is about trust boundaries in the multi-agent system the spec describes — whether one agent's context can leak into another's review. Both are engineering problems, and both have concrete rules and probe evidence behind them. For the system architecture that these boundaries protect, see [overview](overview/index.md) and [the method](method.md); for the findings the probes produced, see [findings](findings/index.md).

## Part 1 — content policy

The repo's content policy lives in `AGENTS.md` and applies to every agent working here. The core assumption: anything committed will be read by outside parties, including the vendors whose products this framework evaluates. There is no "it's private for now" state to rely on.

**Never written here:** personal or confidential context, names of individuals at vendors or target companies, competitive or negotiating strategy, and secrets, credentials, tokens, or employer-confidential material. That content belongs in a separate private repo, which is not referenced by path from this one.

**Written here:** engineering rationale, design trade-offs, what was tried and rejected, and honest technical assessment — including unflattering findings. Recording that a platform capability is immature, undocumented, or broken is legitimate engineering work. The line is not "avoid criticism" — it is "keep it technical, sourced, and fair."

**History hygiene:** a clean working tree is not enough. Git history travels with the repo. If anything sensitive is ever committed, the rule is to squash or rewrite before the first push, not to add a follow-up "scrub" commit that leaves the original in history.

## Part 2 — trust boundaries

The Phase 0 probes tested whether the platform's controls can enforce the method's independence invariants. The evidence is in `evidence/phase-0/`, and the decision is in `planning/phase-0/GO-NO-GO.md`. Three findings define the trust boundary picture.

### The session store is a shared surface

`Grep` reads all of `~/.factory/sessions` regardless of the agent's working directory. Probe 3 (`evidence/phase-0/probe-3/README.md`) demonstrated that a read-only validator — restricted to `Read, Grep, Glob, LS` with no shell — recovered the executor's private codename by grepping the session store. The tools are not scoped to the repository under review; they accept any absolute path on the filesystem. The session store is keyed by working directory, which organises the store but scopes nothing. A validator running in an entirely different repository still reads its predecessor's transcript because `Grep` does not honour `cwd`.

The capability is unrestricted and proven. Whether it happens depends on whether the validator thinks to look. That is the worst combination for a security property: not a boundary, so it cannot be relied on; and intermittent, so a green run does not demonstrate it held.

### Droid search is an independent leak path

The addendum (`evidence/phase-0/probe-3/ADDENDUM-droid-search.md`) measured `droid search` — a documented top-level command whose stated purpose is searching across local sessions. A single generic query, `droid search "CODENAME"`, returned the executor's withheld secret when the only session containing it was the executor's. This is a product feature working as designed, not a derivable filesystem path that a future version could scope. Removing `Execute` from the validator's tool set closes this path completely — but leaves the `Grep` path untouched. The two are independent.

### Tool restriction is not path protection

Probe 3 also confirmed that tool restrictions are genuinely enforced: a `tools:` allowlist in a custom Droid config removes tools from the subagent's schema by omission, and a tool absent from the schema cannot be talked into existing. That is the strongest form of write-protection. But it is orthogonal to read-reach. The read-only restriction limits writes, not reads. Every validator run in the probe wandered outside the repo unprompted. The design consequence: a validator's schema must omit `Execute` (closing the `droid search` path), and a hook must fail the run on any read under `~/.factory/sessions` (closing the `Grep` path). Configuration alone cannot carry invariant #2.

### What this means for the method

The `GO-NO-GO` decision built the isolation guard as one of three policies in a single `PreToolUse` hook — the reference guard that is the spine of the framework. The guard fails closed on any payload it cannot interpret, reads the transcript to learn what actually happened, and emits a contract string on stderr so the run continues with the denial visible. The probe evidence is version-scoped to `droid` 0.186.0; a CLI upgrade invalidates the findings until the probes are re-run.
