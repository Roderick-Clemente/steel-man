# plan-lint — Spec (v1 draft)

**Status:** Draft for a fresh builder seat. The cross-family panel reviews
this spec *together with* the implementation; approval of the code is
approval of the spec. Authored operator-side (Fable 5 advisor session,
operator-directed). Per §13 this spec describes behavior and acceptance,
not implementation.

## Errata

- v1.2 (2026-08-11): companion-tier auto-discovery
  (`<plan-stem>.contract.json`) documented and precedence codified
  (fence > `--contract` > companion > heuristic). Present in the
  implementation since v1 but absent from this spec; surfaced by
  operator pre-flight, confirmed by Tier-2 review. YAML contract
  bodies deferred: JSON only.

- v1.1 (2026-08-11): heuristic mode no longer blocks. v1.0 mandated rule 6
  block on undeclared "gate predicate prose" without defining a
  discriminator; the builder implemented the under-specification
  literally. First live advisory run (v6 plan, no contract): 40 rule-6
  false positives, zero rule-1/3/5 findings. Spec author's error.
  Heuristic-mode recall requirements and negative fixtures added.

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
6. **Required anchors:** gate predicates declared in the contract must
   name a resolvable schema/artifact plus field path; an unresolvable
   declared predicate BLOCKs. In heuristic mode, suspected gate-predicate
   prose warns at most and never matches revision-history / changelog
   sections.
7. **File paths** referenced by the plan exist in the repo (or are
   explicitly marked as to-be-created).

## CONTRACT block convention

Plans MAY declare their machine-checkable claims (field paths, flags,
exit codes, file paths, model ids, function signatures) as any of:
1. a fenced CONTRACT block (JSON) embedded in the plan;
2. a `--contract <path>` JSON sidecar passed on the CLI;
3. a companion `<plan-stem>.contract.json` auto-discovered next to the
   plan (`foo.md` -> `foo.contract.json`, not `foo.md.contract.json`).
Precedence: embedded fence > `--contract` flag > companion > heuristic.
Declared claims are verified strictly, and an unresolvable declared
claim BLOCKs. Contract bodies are JSON only; YAML is deferred (the
v1.0 "JSON or YAML" phrasing was never implemented).
If no contract exists, ALL rules run heuristically as warnings only;
nothing blocks on an undeclared plan. Heuristic mode MUST still exercise
rules 1, 3 and 5 against claim-shaped backticked strings (field paths,
flags, model ids, call expressions). Lines inside revision-history /
changelog sections are excluded from every heuristic check.

## Interface

```
tools/plan-lint.py <plan.md> [--repo-root <path>] [--json <out.json>] [--contract <path>]
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
- Negative fixture: narrative prose about gates and blockers (e.g. a
  revision history quoting past REJECT verdicts) produces zero findings.
  The fixture must be newly authored innocent prose, not a copy of the
  v6 text, so the fix cannot be a string-match against known sentences.
- Heuristic fixtures: the v3-v6 texts WITHOUT sidecars produce zero
  BLOCKs, and the v6 text warns on the call-signature claim.
- Companion-tier tests: a companion contract alone loads and can BLOCK
  (source reported); `--contract` beats companion; the embedded fence
  beats both.
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
