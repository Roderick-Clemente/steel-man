# Plan lint

A deterministic pre-review tier that catches machine-checkable contract defects in build plans before a frontier panel round is spent. It is BLOCK-only: a PASS is never evidence of plan quality and never an approval input. The panel fires on whatever survives.

## Why it exists

Four of six PLAN-5.1 review cycles carried wholly or partially mechanical blockers -- a plan referencing a schema field that does not exist, a stub emitting one reviewer where the gate required two, three different token filename conventions across three artifacts, and a call passing family labels where the callee resolves model ids. Each was caught by a frontier reviewer at panel cost. Every one is mechanically detectable against on-disk reality. Plan lint exists to catch them first, at zero panel cost.

## The seven rules

| # | Rule | What it checks |
|---|---|---|
| 1 | field-path | Field-path references in the plan resolve against live JSON artifacts and schemas |
| 2 | cli-flag | CLI flag references resolve against the argparse definitions of the named tools |
| 3 | model-id-family | Model ids and family labels resolve against `MODEL_FAMILY_MAP`; flags id-vs-label type confusion |
| 4 | internal-consistency | Numeric contract claims agree with each other (N emitted vs N required); each referenced artifact has exactly one name |
| 5 | call-signature | Call-signature claims match the named function's actual arity and parameter names in the repo |
| 6 | required-anchors | Gate predicates declared in the contract name a resolvable schema/artifact plus field path; an unresolvable declared predicate BLOCKs |
| 7 | file-paths | File paths referenced by the plan exist in the repo or are explicitly marked to-be-created |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | PASS -- warnings allowed, printed |
| 2 | Error or fail-closed -- usage error, internal error, or missing ground-truth artifact. Distinct from BLOCK: a missing artifact is exit 2 with a reason, never a silent pass |
| 3 | BLOCK -- findings on stdout and `--json` if given |

The fail-closed distinction matters. A missing or unreadable ground-truth artifact is exit 2, not exit 0. The tool never silently passes when it cannot verify a claim.

## Contract declaration

Plans may declare their machine-checkable claims in three ways, with strict precedence: an embedded fenced CONTRACT block (JSON) beats a `--contract <path>` sidecar, which beats a companion `<plan-stem>.contract.json` auto-discovered next to the plan. Declared claims are verified strictly, and an unresolvable declared claim BLOCKs. If no contract exists at all, all rules run heuristically as warnings only -- nothing blocks on an undeclared plan, but rules 1, 3, and 5 still exercise against claim-shaped backticked strings. Lines inside revision-history or changelog sections are excluded from every heuristic check, so quoting a past REJECT verdict in prose does not trip a false positive.

## Interface

```
tools/plan-lint.py <plan.md> [--repo-root <path>] [--json <out.json>] [--contract <path>]
```

The tool is 1,470 lines of Python in `tools/plan-lint.py`, implemented per the spec at `tools/plan-lint-spec.md`. The spec is the contract; implementation choices are per section 13 of the operating rules. The spec carries two errata worth noting: heuristic mode no longer blocks (v1.0 mandated a rule-6 block on undeclared gate-predicate prose without defining a discriminator, producing 40 false positives on the first live run), and companion-tier auto-discovery was present in the implementation since v1 but only documented later.

## Telemetry

Each invocation appends one row -- tool, plan path plus content sha, verdict, finding count, duration -- following `telemetry/SCHEMA.md` conventions and the section 17.3 gitignore discipline.

## Key source files

| File | Role |
|---|---|
| `tools/plan-lint.py` | The linter (1,470 lines) |
| `tools/plan-lint-spec.md` | The spec (v1 draft, the contract for the implementation) |
| `tests/fixtures/plan-lint/` | Historical plan fixtures extracted from git history for acceptance testing |
| `telemetry/SCHEMA.md` | Telemetry row schema |

See also [features index](index.md), [sprint-loop runner](sprint-loop-runner.md), [chunk token gates](chunk-token-gates.md).
