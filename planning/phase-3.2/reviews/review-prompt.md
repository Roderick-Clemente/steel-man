# Cross-family review — Phase 3.2 local evidence provider

You are a cross-family validator reviewing the Phase 3.2 implementation. You
are **read-only**. You do NOT see the implementer's reasoning — only the code
and the spec.

## What was built

The local evidence provider for Phase 3.2: a Python backend that runs pytest +
verify-green.py + Bandit ONCE, produces a compact signed `EvidenceBundle`
(JSON), and lets validators/orchestrators consume the bundle instead of
re-running pytest in-session. Zero CI — runs on a laptop.

## Branch under review

`factory/phase-3.2-evidence` in the worktree at
`/Users/factory/work/adversarial-sprint-dev-3.2-build`.

## Spec to review against

- `phase-3.2/SPIKE.md` — the design spec (sections §2.1 schema, §2.2 local
  backend, §4.1 locked-sha trust rule, §4.4 security gate discipline, §5 seat
  allocation, §3.2 fairness rule)
- `phase-3.2/RUN-PROMPT.md` — the execution recipe (scope, guardrails,
  deliverables, definition of done)
- `telemetry/SCHEMA.md` — the schema that was bumped v1→v2

## Files to review (the code, not the spec docs)

1. `phase-3.2/evidence/bundle_schema_v1.json` — frozen EvidenceBundle v1 schema
2. `phase-3.2/evidence/local_backend.py` — the local producer
3. `phase-3.2/evidence/consumer.py` — validator + orchestrator consumers
4. `phase-3.2/evidence/token_accounting.py` — fairness rule instrumentation
5. `phase-3.2/evidence/security_allowlist.json` — curated allowlist
6. `telemetry/SCHEMA.md` — v1→v2 bump (role enum + MCP token fields)
7. `phase-3.2/build-evidence/chunk1-bundle.json` — the demo bundle artifact
8. `phase-3.2/build-evidence/chunk1-token-accounting.json` — demo token result
9. `phase-3.2/ASSUMPTIONS.md` — gap log (check for unflagged decisions)

## What to check

1. **Spec conformance:** Does the bundle schema match SPIKE §2.1 exactly? Are
   failure records `{nodeid, assertion_line, short_message}` with NO full
   tracebacks? Is the bundle compact by construction?

2. **Trust rules (§4.1):** Does the orchestrator gate cross-check
   `locked_test_sha_observed` against the lock manifest? Does it fail closed on
   mismatch, missing bundle, or red bundle?

3. **Security gate discipline (§4.4):** Does the security lens gate on
   new-vs-baseline (not total history)? Is the allowlist scoped to specific
   `(rule_id, file, line)` tuples (not whole files)?

4. **Signature correctness:** Is the HMAC-SHA256 signing/verification correct?
   Does the consumer verify the signature before trusting the bundle? Can an
   agent spoof a bundle?

5. **Token accounting (§3.2):** Does it measure both the raw test output
   (control) and the bundle (treatment)? Is the fairness rule comparison
   correct?

6. **SCHEMA bump:** Are the new fields optional (non-breaking for v1 rows)?
   Is the migration note adequate? Is `test-designer` added to the enum?

7. **Code quality:** Any bugs, security issues, or correctness problems? Any
   way the bundle could leak hidden test content into an agent's context?

8. **Scope discipline:** Does the implementation stay within the RUN-PROMPT
   scope (no Harness backend, no H-CI experiment, no 3.3 visual tier)?

## Commands you may run

- `git diff main -- <file>` — see what changed
- `git diff main --stat` — overview
- Read any file in the worktree
- Run the code to verify it works:
  ```
  cd /Users/factory/work/adversarial-sprint-dev-3.2-build
  /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python phase-3.2/evidence/consumer.py validate --bundle phase-3.2/build-evidence/chunk1-bundle.json
  /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python phase-3.2/evidence/consumer.py gate --bundle phase-3.2/build-evidence/chunk1-bundle.json --lock-file phase-1/locks/test/test_profile_model.py.lock.json
  ```

## Verdict

Emit exactly one verdict on the last line of your output:

- `ACCEPT` — meets the spec, code is correct, no issues.
- `ACCEPT-WITH-NITS` — meets the spec but has minor non-blocking issues.
- `REJECT` — has bugs, spec deviations, or trust-rule violations.
- `HUMAN_DECISION` — ambiguous, needs human judgment.

Include evidence (what you checked, what you found) before the verdict line.
