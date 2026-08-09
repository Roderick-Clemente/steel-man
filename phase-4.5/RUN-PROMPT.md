# Phase 4.5 — RUN PROMPT (ready-to-run handoff)

You are the **operator** running the Phase 4.5 sprint-loop against the
`QuantumBank` pilot. The runner is built and dry-run-tested; this
prompt is the inbound handler for any future operator session that
launches a sprint on this branch.

## §15 framing — Act 1 vs Act 2 (pd-pass-r2 G-9)

The PRD §15 names two modes of operating. They are different
deliverables, not different framings of the same work:

- **Act 1 (vibe code as usual)** — the operator + agent in a
  conversational loop. The runner is *not* invoked. Universal
  rules followed via the agent's skill layer. The agent's behavior
  is governed by good faith: §1 / §7 / §17 are aspirational,
  enforced by the agent's prompt-discipline, not by code.
- **Act 2 (runner-driven)** — `bin/run-sprint` is invoked. The
  runner *is* the §11 acceptance gate. Universal rules followed
  by code: §7 fail-closed via signing-key refusal, family-guard
  preflight (chunk 1 + chunk 10 F-1/F-2), §5.3 preconditions on
  `accept` (chunk 10 F-7), `--unattended` checkpoint-on-refusal
  (chunk 12a G-7). The agent's behavior is governed by codes.

**The transition between Act 1 and Act 2 is the demo's delta.**
§11 structural guarantees are visible only in Act 2. If you treat
the runner as "an optional overlay" you collapse the modes and
lose the difference. Per OPERATING-RULES §1 / §15: the runner
is a structural guarantee, not optional.

### Truth-table — what each mode does (pd-pass-r2 G-9)

| Operator action                  | Act 1 (no runner)         | Act 2 (live mode)         | Act 2 (`--dry-run`)        |
|----------------------------------|---------------------------|---------------------------|---------------------------|
| Agents follow universal rules    | by prompt discipline      | enforced by code          | enforced by code          |
| Family guard                     | not enforced              | enforced (SystemExit 2)   | enforced (SystemExit 2)   |
| EVIDENCE_SIGNING_KEY unset       | n/a                       | refuses closed (Stop)     | simulated ACCEPT (dry-run reality) |
| §5.3 `accept` while blocker|high | agent's choice            | refuses (SystemExit 4)     | simulated ACCEPT (no real model)     |
| Git commit                      | agent's repo              | runner `git add -f` audit-trail + per-chunk commit | simulated; no commit       |
| Push to remote                  | agent's call              | never (invariant #8)      | never                     |
| Cross-family review              | agent's prompt condition  | structural via LocalBackend→`tools/orchestrate-review.py` | simulated ACCEPT         |

The `--dry-run` column is honest about what it doesn't do: it produces
a *simulated* ACCEPT, not a demonstrated one. Operators who run
`--dry-run` and treat the output as a green-light are running on a
§7 silent-green shape. Concede ergonomics via clean banner messages,
not via "treat the simulator as the verdict."

## How to invoke — per-pilot overlay

The canonical one-command entrypoint is the per-pilot overlay, not
the runner's CLI directly. The overlay is the closed set of
artifacts the operator edits; the runner's CLI flags are for
debugging.

```
# First time (wiring test):
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --dry-run --non-interactive

# Real run (operator in the seat at the reconcile gate):
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint

# Real run, unattended (--unattended writes checkpoint on refusal):
<PILOT_REPO>/.adversarial-sprint/bin/run-sprint --unattended
```

The overlay lives at `<PILOT_REPO>/.adversarial-sprint/` and is
deployed by copying `templates/overlay/*` from the framework repo.
See `templates/overlay/README.md` for the install steps.

For runner-level CLI flags (debug, advanced), invoke directly:
`tools/sprint-loop.py --help`.

## Scope of THIS run

1. The full PRD §11 / Phase 4.5 deliverable: ``sprint-loop.py``
   composes the existing primitives (`tools/orchestrate-review.py`,
   `phase-1/scripts/{lock,valid-red,verify-green}.py`,
   `phase-3.2/evidence/{local_backend,consumer}.py`,
   `tools/run-with-model.sh`, `tools/adapters/factory.py`).
2. Track B validation-backend abstraction (LocalBackend + CIBackend
   stub per the prompt's "interface only").
3. Track C CI flavor (a) workflow file (`.github/workflows/adversarial-sprint-ci.yml`).

**Out of scope:** Backlog E (Harness backend / 3.3 visual tier /
framework-repo dogfood), Phase 5 (generalisation), Phase 6
(hardening), Phase 7 (human-in-the-loop compression).

## Open questions — recommended defaults (operator may override)

- **Validation backend:** local, the working path. CIBackend is a stub.
- **Signing key:** set `$EVIDENCE_SIGNING_KEY` before running.
- **Validator panel:** `grok-4.5` + `gemini-3.1-pro-preview` (default
  cross-family primary); `claude-opus-4-8` is the standing fallback
  per `tools/conventions/model-discipline.md`.
- **`--max-review-rounds`:** 2 (PRD §5.3 default).
- **`--retry-threshold`:** 1 (PRD §5.7 default).
- **`--chunks-file`:** REQUIRED. The runner does not yet
  auto-extract chunks from the plan document; this is the named gap
  in `KNOWN-ISSUES.md`.
- **Reconciliation gate:** human-pause via stdin. `--skip-reconcile`
  or `--dry-run --non-interactive` opt out.

## Guardrails (per PRD + OPERATING-RULES.md)

1. **Family separation** — the §17.2 family guard runs as a preflight
   before any droid call. Unknown families cause `SystemExit(2)`. The
   curated map is `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`.
2. **Assert on reality** — bundle signature + locked-test SHA +
   pytest results are checked before a chunk is marked ACCEPTED.
   Silent-green eraser is the §1 / §7 defect shape; never trust exit
   codes alone.
3. **Telemetry rows are git-ignored** — `telemetry/runs.jsonl`,
   `telemetry/findings.jsonl`, `telemetry/dispositions.jsonl` are
   `phase-N/KNOWN-ISSUES.md` — listed in `.gitignore`. The runner
   appends rows but never `git add`s them.
4. **No `git push` from the runner** — invariant #8 / safety guidance:
   the runner creates a branch + per-chunk commit bundle; merging is
   human. `--create-pr` is opt-in (default off).
5. **No `droid exec --mission`** — `tools/run-with-model.sh` refuses
   it (Phase 0 GO-NO-GO closed the path); `DROID_ALLOW_MISSION=1` is
   the documented exception for re-probing only.
6. **Edit-time commit granularity** — one commit per accepted chunk
   on the sprint branch. Conventional commit bodies per
   `tools/conventions/commit-body-recipe.md`.
7. **Run with `pytest tests/` first** — the runner is not the only
   guarantee. The unit tests in `tests/test_sprint_loop.py` are the
   foundation.

## Steps (operator-facing)

1. Hydrate the docs: `PRD.md` §11 (Phase 4.5) + §17 (model
   discipline), `tools/OPERATING-RULES.md` §1–§18,
   `tools/conventions/model-discipline.md`, this file,
   `tools/sprint-loop.py --help`, `phase-4.5/KNOWN-ISSUES.md`.
2. Sanity:
   `PYTHONPATH=tools /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python -m py_compile tools/sprint-loop.py tools/sprint_loop/*.py`
   `PYTHONPATH=tools /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python -m pytest tests/`
3. Dry-run end-to-end:
   ```
   PYTHONPATH=tools /Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python \
     tools/sprint-loop.py \
     --config examples/sprint-loop-config.json \
     --chunks-file examples/sprint-loop-chunks-example.json \
     --dry-run --non-interactive
   ```
4. Set `$EVIDENCE_SIGNING_KEY` to a non-empty hex string (random).
   Best-effort: `python3 -c "import secrets; print(secrets.token_hex(32))"`.
5. Real run (interactive; pauses at reconcile):
   `tools/sprint-loop.py --config <cfg>.json --chunks-file <chunks>.json`
6. After-run review: read `phase-4.5/build-evidence/<run-id>/checkpoint.json`
   + the per-chunk `c1/reviews/review-summary.json` to confirm what
   landed.
7. The runner has produced a `factory/sprint-<ts>` branch with one
   commit per accepted chunk. **Human gate the merge.** Run
   `git log factory/sprint-<ts> --oneline` to inspect.

## Definition of done

- The full PRD §11 / Phase 4.5 deliverable runs from one command.
- Cross-family validation happens at every PRD §5.7 gate.
- A `factory/sprint-<ts>` branch exists with one conventional commit
  per accepted chunk.
- `telemetry/runs.jsonl` has at least 1 row per droid invocation
  (planner + reviewer(s) + executor + N validators).
- `phase-4.5/build-evidence/<run-id>/checkpoint.json` is committed
  to the audit branch.
- The runner has *not* auto-merged; a human approves the merge.

## Anti-pattern references

If you find yourself wanting to:

- man-paste-protocol a `droid exec` to bypass the runner → don't.
  OPERATING-RULES §9: the script is the default.
- skip the family guard by editing `tools/sprint_loop/state.py` → don't.
  §14 holds; the rule is structural, not advisory.
- `git push` from the runner → don't. The runner never pushes
  per invariant #8.
- claim "Mission cosplay" worked → don't. Phase 0 GO-NO-GO is the
  authoritative answer (PRD §3.2).
