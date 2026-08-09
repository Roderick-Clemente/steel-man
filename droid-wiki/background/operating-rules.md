# Operating rules

Rules learned the hard way running this repo across several agents (Factory Droid, Codex, Claude Code) and more than one machine. Full text in `tools/OPERATING-RULES.md`.

## The 17 rules

1. **Commits are the only cross-machine channel.** No shared working tree, no shared session state. The git repo is the entire coordination surface. Untracked files don't travel; `STEER.md` is machine-local.

2. **Capture before you change.** Before upgrading, wiping, or reconfiguring any environment that is itself evidence, commit the evidence first. A control environment is only as durable as what's in git.

3. **Version-stamp every finding.** CLI behavior is not stable across patch releases. Every claim that depends on CLI behavior carries the version it was observed under.

4. **Two numbering schemes, never collapse them.** Repo defect-N and GitHub issue-N are different identifiers with different sources of truth. They disagree, and that is correct.

5. **No unsupervised building.** The worker never crosses from probing/planning into building without an explicit human go and a named unit of work. "Pick something and go" is the anti-pattern.

6. **Enforcement is not calibration.** A boundary held by a well-behaved model is not enforced. Re-run with the cheapest cross-family executor available and try to break it.

7. **Assert on reality, never on exit code.** The platform's default failure mode is silent green. Never trust `exit 0` as proof work happened. Assert on hook logs, file SHAs, and captured output.

8. **When scope shifts, name it.** If the work you're doing is not what the phase's RUN-PROMPT scoped, say so explicitly. Decide: absorb (small, in-scope) or push out (larger, different concern). Record the decision in ASSUMPTIONS.md. Most scope shifts want their own loop. Added after Phase 3.2, where the orchestration gap (a framework-level Act 2 concern) was discovered and built inside a phase-3.2 loop instead of getting its own prompt.

9. **If it's not scripted, it didn't happen.** A phase that runs `droid exec` by copy-pasting commands has no reproducible evidence. The orchestration script is the default; RUN-COMMANDS.md documents it, doesn't replace it.

10. **Telemetry rows are written by the script, not by the operator.** Multi-invocation phases must emit `runs.jsonl` from the orchestration script. Committed envelopes + reconstruction recipes remain valid for past phases. Forward-looking, not retroactive.

11. **Exit criteria are checked, not assumed.** "Invalid RED cases are rejected" means one was run and rejected — not that the script exists. "Replayable demo" means a demo artifact exists — not that the wiki is comprehensive.

12. **Unexercised safety paths are named gaps, not phase blockers.** A clean null (plan converged round 1, all validators ACCEPT) is valid completion per PRD §13. Record the unexercised path as a named gap. Do not manufacture disagreement.

13. **Don't give the executor the answer.** The executor prompt describes the problem, not the implementation. If the prompt contains the exact fix, the executor is a `sed` command. H3 depends on independent implementation.

14. **Use the adapter shim and the model-discipline wrapper.** Scripts that read envelopes go through `tools/adapters/factory.py`. Scripts that invoke `droid exec` go through `tools/run-with-model.sh`. No direct `DROID_BIN` or raw field access.

15. **Assert on reality includes git history.** Never judge past phases on uncommitted working tree state. Inspect git history and the system of record before concluding something was "never built" or "never ran."

16. **Demo claims bind to Phase-0-verified capabilities.** No demo beat may claim a capability Phase 0 did not verify. No Mission cosplay. "Close the laptop" requires a demonstrated durable runner. Act 3 stays inside probes that returned PASS.

17. **Capacity envelope: name the next 1-3 deliverables.** A roadmap re-sequencing names what can actually be done next, not an unbounded list. Refuse unbounded foundation programs.

## Key source files

| File | Purpose |
|---|---|
| `tools/OPERATING-RULES.md` | Full text of all 17 operating rules |
| `tools/wake-loop.md` | The orchestrator/worker pattern these rules assume |
| `AGENTS.md` | Repo conventions (public-repo fence, branch-by-author, commits-as-baton) |
