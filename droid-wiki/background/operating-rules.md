# Operating rules

Rules learned the hard way running this repo across several agents (Factory Droid, Codex, Claude Code) and more than one machine. Full text in `tools/OPERATING-RULES.md`.

## The 8 rules

1. **Commits are the only cross-machine channel.** No shared working tree, no shared session state. The git repo is the entire coordination surface. Untracked files don't travel; `STEER.md` is machine-local.

2. **Capture before you change.** Before upgrading, wiping, or reconfiguring any environment that is itself evidence, commit the evidence first. A control environment is only as durable as what's in git.

3. **Version-stamp every finding.** CLI behavior is not stable across patch releases. Every claim that depends on CLI behavior carries the version it was observed under.

4. **Two numbering schemes, never collapse them.** Repo defect-N and GitHub issue-N are different identifiers with different sources of truth. They disagree, and that is correct.

5. **No unsupervised building.** The worker never crosses from probing/planning into building without an explicit human go and a named unit of work. "Pick something and go" is the anti-pattern.

6. **Enforcement is not calibration.** A boundary held by a well-behaved model is not enforced. Re-run with the cheapest cross-family executor available and try to break it.

7. **Assert on reality, never on exit code.** The platform's default failure mode is silent green. Never trust `exit 0` as proof work happened. Assert on hook logs, file SHAs, and captured output.

8. **When scope shifts, name it.** If the work you're doing is not what the phase's RUN-PROMPT scoped, say so explicitly. Decide: absorb (small, in-scope) or push out (larger, different concern). Record the decision in ASSUMPTIONS.md. Most scope shifts want their own loop. Added after Phase 3.2, where the orchestration gap (a framework-level Act 2 concern) was discovered and built inside a phase-3.2 loop instead of getting its own prompt.

## Key source files

| File | Purpose |
|---|---|
| `tools/OPERATING-RULES.md` | Full text of all 8 operating rules |
| `tools/wake-loop.md` | The orchestrator/worker pattern these rules assume |
| `AGENTS.md` | Repo conventions (public-repo fence, branch-by-author, commits-as-baton) |
