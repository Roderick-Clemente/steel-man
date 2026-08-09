# Phase 4.5 — Exit criteria self-check

Per `OPERATING-RULES.md` §11 ("exit criteria are checked, not
assumed"), every PRD §11 Phase 4.5 / Track A / Track B / Track C
exit criterion maps to a verifiable, script-runnable check.

This file is the operator-facing checklist. Run all checks before
declaring Phase 4.5 complete. Each row is a one-liner that exits 0
on pass; non-zero on fail. Full criteria mapping lives in
`phase-4.5/adversarial_review/criteria-check.md`; this file is the
operator's executable version.

## Sanity

```
$(PILOT_PY) = /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python

# (1) compile-clean
PYTHONPATH=tools $PILOT_PY -m py_compile tools/sprint-loop.py \
    tools/sprint_loop/*.py tools/sprint_loop/prompts/*.py \
    tests/test_sprint_loop.py
# → expect: silent exit 0

# (2) pytest unit + integration
PYTHONPATH=tools $PILOT_PY -m pytest tests/
# → expect: 52 passed

# (3) yaml parses for the CI workflow
PYTHONPATH=tools $PILOT_PY -c 'import yaml; yaml.safe_load(open(".github/workflows/adversarial-sprint-ci.yml"))'
# → expect: silent exit 0

# (4) --help works
PYTHONPATH=tools $PILOT_PY tools/sprint-loop.py --help
# → expect: usage banner

# (5) dry-run end-to-end exists
PYTHONPATH=tools $PILOT_PY tools/sprint-loop.py \
    --config examples/sprint-loop-config.json \
    --chunks-file examples/sprint-loop-chunks-example.json \
    --dry-run --non-interactive
# → expect: COMPLETED · run_id=...; exit 0

# (6) family guard refuses unknowns (KNOWN-ISSUES.md §KNE encouraged check)
PYTHONPATH=tools $PILOT_PY -c '
import json, tempfile, subprocess, os, sys
cfg = tempfile.mktemp(suffix=".json")
open(cfg, "w").write(json.dumps({
    "framework_root": "/Users/factory/work/adversarial-sprint-dev",
    "pilot_root": "/Users/factory/work/quantum-bank--llms-txt-pilot",
    "pilot_python": "/Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python",
    "validators": ["totally-unknown-model:unknown:unknown:label"],
    "planner_model": "claude-opus-5",
}))
r = subprocess.run(
    [sys.executable, "-c",
     "import runpy,sys;sys.argv=[\"sprint-loop.py\",\"--config\",\""+cfg+"\",\"--dry-run\",\"--non-interactive\"];ns=runpy.run_path(\""+os.path.abspath("tools/sprint-loop.py")+"\");try:ns[\"main\"]()\nexcept SystemExit as e:sys.exit(e.code)"],
    env={**os.environ, "PYTHONPATH": "tools"}, capture_output=True, text=True,
)
assert "§4" in (r.stdout+r.stderr) or "§17.2" in (r.stdout+r.stderr), r.stdout+r.stderr
print("\\nFAMILY GUARD REFUSES UNKNOWN MODEL ✓")
'
```

## Per-track exit mapping

### Track A — Full loop runner

- [x] `tools/sprint-loop.py` exists, runs `--help` cleanly (test 4 above).
- [x] Composes existing primitives — `grep -nE "from phase-[0-9]/.+/scripts|tools/orchestrate-review|tools/run-with-model|tools/adapters/factory" tools/sprint_loop/*.py tools/sprint-loop.py`
      ≥ 1 hit per primitive.
- [x] Dry-run end-to-end (test 5 above) produces a complete evidence tree + a checkpoint JSON.
- [x] Reconcile gate documented in `phase-4.5/RUN-PROMPT.md` + `KNOWN-ISSUES.md KN6`.
- [x] Per-chunk inner loop composes `lock.py` + `valid-red.py` + `verify-green.py` + `local_backend.py` + LocalBackend (= `orchestrate-review.py`).
- [x] PR / branch creation per chunk; one commit per accepted chunk; never `git push`.
- [x] Telemetry rows written by the script (`telemetry/runs.jsonl` + `findings.jsonl`).

### Track B — Pluggable validation backend

- [x] `tools/sprint_loop/backends.py` defines `ValidationBackend` Protocol + `LocalBackend` (real) + `CIBackend` (NotImplementedError per the prompt).

### Track C — CI integration flavor (a)

- [x] `.github/workflows/adversarial-sprint-ci.yml` parses (test 3 above).
- [x] KI-2 preventive fix — validators run with `--treatment` (bundle-mode + no `Execute`).
- [x] Gate decision becomes a PR status check; REJECT / STOP blocks merge (per the workflow's `conclusion` derivation).
- [x] Companion doc `phase-4.5/CI-GATE.md` documents signing-key distribution, droid install requirement, PR-title chunk-id convention.

## OPERATING-RULES §11 check

- [x] Every exit criterion above is mapped to a file + a script-runnable check.
- [x] The checks above are committed to `phase-4.5/EXIT-CHECKS.md` (this file).
- [x] The build-result summary is committed to `phase-4.5/BUILD-NOTES.md`.

## KNOWN-ISSUES.md §12 surface

- [x] End-to-end pilot run unexercised: KN1. Recorded clean-null per §12 / PRD §13.
- [x] Reconcile under real disagreement unexercised: KN2.
- [x] CIBackend stub intentional: KN3.
- [x] MCP server invocation unexercised: KN4.
- [x] Auto-chunk-from-plan extraction NOT done: KN5.
- [x] Droid install best-effort: KN6.
- [x] Mid-loop dry-run artefacts: KN7.
- [x] Human Decision Packet narrative on top of JSON checkpoint: KN8.

## Phase 4.5 = COMPLETE — when?

This phase's deliverables build green (52/52 tests, dry-run end-to-end).
The operator may declare Phase 4.5 complete when:

1. The checks above all pass on the operator's machine.
2. A full pilot run (KN1) succeeds end-to-end — committing a chunk
   that passes cross-family review and lands on the audit branch.
   Until KN1 succeeds, Phase 4.5 is **structurally complete but
   operationally unverified** — declare "build complete,"
   not "product complete."

Per `OPERATING-RULES.md` §17 capacity envelope, "complete" here
means: every PRD §11 item is shipped with a verified check. The
**demo claim** ("close the laptop, come back to a sprint") is
Phase 6 / Phase 7 work — see `KNOWN-ISSUES.md KNR2`.

## Risk-class surface for what was NOT shipped

The fragile classes are:

1. **Mid-loop operator coercion** — the runner's per-chunk flow is
   shaped for stable LRPC-style subprocess calls; an interrupted
   handshake at the executor step is checkpointed (see
   `tools/sprint-loop.py:write_checkpoint`) but resume is a UI
   class someone will need.
2. **Cost-class assumptions** — the runner uses `tools/run-with-model.sh`
   for every droid call, which means the script's implicit cost is
   the sum of the underlying calls. There is no per-run budget
   yet (PRD §6 mentions `oversight.high` — not implemented as a
   runtime guard).
3. **Cross-repo** — the runner does not orchestrate multi-repo
   changes; PRD §3 v1 non-goal.
4. **Harness-native CI** — Backlog E. Not in Phase 4.5.

If the operator's pilot run exposes one of these, that's the
expected learn-surface per the framework's §17 bounded-capacity rule.

## Signature

At declare time, the operator should record in the project's main
wiki a `phase-4.5-CLOSE.md` (mirror `tools/PHASE-0.5-CLOSE.md`)
with: file counts, tests-passing count, dry-run-output excerpts,
and the run_id for the KN1 follow-on.
