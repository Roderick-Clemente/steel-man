# Minimal Well-Formed Plan (GREEN fixture)

A minimal build plan with a CONTRACT block whose claims all resolve
against the ground-truth artifacts in the fixture repo.

## Deliverables

| # | Deliverable | Type | Details |
|---|-------------|------|---------|
| 1 | `tools/setup_review_scope.py` | New script | Creates review-scope.json. Validates model IDs against `MODEL_FAMILY_MAP`. |

## Rule application

- §7: tests check file existence, JSON validity — not exit codes alone.
- §18: composes existing primitives.

```contract
{
  "claims": [
    {
      "rule": 1,
      "line": 1,
      "claim": "Token has reviewers array",
      "field_path": "reviewers",
      "artifact": "phase-4.5/tokens/chunk-5a.token.json",
      "expect": "exists"
    },
    {
      "rule": 1,
      "line": 1,
      "claim": "Token reviewers have verdict field",
      "field_path": "reviewers[0].verdict",
      "artifact": "phase-4.5/tokens/chunk-5a.token.json",
      "expect": "exists"
    },
    {
      "rule": 2,
      "line": 1,
      "claim": "chunk_sequence_gate accepts --prior-token",
      "artifact": "tools/chunk_sequence_gate.py",
      "field_path": "--prior-token",
      "expect": "flag_exists"
    },
    {
      "rule": 3,
      "line": 1,
      "claim": "grok-4.5 is a valid model id",
      "artifact": "tools/sprint_loop/config.py",
      "field_path": "MODEL_FAMILY_MAP.grok-4.5",
      "expect": "model_id"
    },
    {
      "rule": 5,
      "line": 1,
      "claim": "build_token signature matches",
      "artifact": "tools/sign_chunk_token.py",
      "field_path": "build_token",
      "expect": "params:chunk_id,chunk_commit_sha,reviewers,signed_by,signing_key_env"
    },
    {
      "rule": 7,
      "line": 1,
      "claim": "tools/sign_chunk_token.py exists",
      "path": "tools/sign_chunk_token.py",
      "expect": "exists"
    },
    {
      "rule": 6,
      "line": 1,
      "claim": "Gate predicate: token file exists at chunk-{chunk_id}.token.json with reviewers[*].verdict in ACCEPT_CLASS",
      "field_path": "reviewers[*].verdict",
      "artifact": "phase-4.5/tokens/chunk-5a.token.json",
      "expect": "resolvable"
    }
  ]
}
```
