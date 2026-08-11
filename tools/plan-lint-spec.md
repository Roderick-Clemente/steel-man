# plan-lint — Spec (v1 draft)

**Status:** Draft for a fresh builder seat. The cross-family panel reviews
this spec *together with* the implementation; approval of the code is
approval of the spec. Authored operator-side (Fable 5 advisor session,
operator-directed). Per §13 this spec describes behavior and acceptance,
not implementation.

## Purpose

A deterministic pre-review tier for build plans. Catches machine-checkable
contract defects before a frontier panel round is spent. BLOCK-only: a PASS
is never evidence of plan quality and never an approval input; the panel
fires on whatever survives.

## Motivation (evidence)

Four of six PLAN-5.1 review cycles carried wholly or partially mechanical
blockers (see `phase-4.5/PLAN-5.1.md` revision history and the
`phase-4.5/REVIEW-*` artifacts on the phase-5 branch):

- v3: plan referenced a top-level `verdict` field the canonical token
  schema does not carry (verdicts are per-reviewer).
- v4: stub emitted 1 reviewer while the gate required >= 2 (arity
  contradiction); contradictory `prior_*` naming.
- v5: three different token filename conventions across three artifacts.
- v6: call passed family labels where the callee resolves model ids
  (live-repro'd; every structural close would refuse).

Each was caught by a frontier reviewer at panel cost. Every one is
mechanically detectable against on-disk reality.

## Rule classes (v1 scope — exactly these, nothing else)

1. **Field-path references** in the plan resolve against live JSON
   artifacts/schemas (e.g. sample tokens, emitted bundle shapes).
2. **CLI flag references** resolve against the argparse definitions of the
   named tools.
3. **Model ids and family labels** resolve against `MODEL_FAMILY_MAP`;
   flag id-vs-label type confusion (a family label passed where a model id
   is expected, and vice versa).
4. **Internal consistency:** numeric contract claims agree with each other
   (N emitted vs N required); each referenced artifact has exactly one
   name/pattern across the plan.
5. **Call-signature claims** match the named function's actual signature
   (arity, parameter names) as found in the repo.
6. **Required anchors:** any section describing a gate predicate must name
   a resolvable schema/artifact plus field path. Vague gate prose is a
   finding, not a pass.
7. **File paths** referenced by the plan exist in the repo (or are
   explicitly marked as to-be-created).

## CONTRACT block convention

Plans MAY carry a fenced structured block (JSON or YAML) declaring their
machine-checkable claims (field paths, flags, exit codes, file paths,
model ids, function signatures). Declared claims are verified strictly.
Claim-shaped strings in prose that are not declared produce warnings.
If no CONTRACT block exists, all rules run heuristically as warnings,
except rule 6, which always blocks on an unresolvable gate predicate.

## Interface

```
tools/plan-lint.py <plan.md> [--repo-root <path>] [--json <out.json>]
```

- Exit 0: PASS (warnings allowed, printed).
- Exit 3: BLOCK, findings on stdout (and `--json` if given), each finding:
  rule class, plan line, claim, artifact checked, reason.
- Exit 2: usage or internal error. Fail-closed and distinct from BLOCK:
  a missing/unreadable ground-truth artifact is exit 2 with a reason,
  never a silent pass.

## Acceptance (RED/GREEN on the real corpus)

- BLOCKs the committed historical texts of `phase-4.5/PLAN-5.1.md` at v3
  (schema field), v4 (arity), v5 (filename), v6 (call signature), each for
  its known class. Fixtures are extracted from git history on the phase-5
  branch and committed under `tests/fixtures/plan-lint/`.
- PASSes (or warns only) on a minimal well-formed plan fixture.
- Unit tests per rule class, including the fail-closed paths.
- Full suite stays green.

## Telemetry

Each invocation appends one row (tool, plan path + content sha, verdict,
finding count, duration) following `telemetry/SCHEMA.md` conventions and
§17.3 gitignore discipline.

## Non-goals (v1)

Judgment surfaces (trust boundaries, sequencing/liveness,
composition-vs-reinvention), prose quality, auto-fix, runner integration
(the pipeline hook is a separate post-5.1 chunk), plan generation.
