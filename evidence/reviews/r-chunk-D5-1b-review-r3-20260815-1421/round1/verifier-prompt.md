# Chunk-D5-1b audit-script-only verifier prompt

You are validating chunk-D5-1b, the sprint-keyed follow-on to
chunk-D5-1. Author spec at
`planning/evidence-hygiene/CHUNK-D5-SPEC.md`; builder prompt at
`planning/evidence-hygiene/PROMPT-D5-BUILDER.md`. Branch
`factory/d5-tooling-docs-1b`; commits `4422ff0` (planner) +
`07a8c6c` (executor). Your role fires via
`tools/run-review.sh kimi-k3 <prompt> <sprint-name>` — the new
chunk-D5-1b signature.

Re-derive §3 floor checks from disk state. Capture every command +
exit code; cite file:line. Concretely verify all four §3 item 2
refusal cases (no-args → exit 2; empty args → exit 2 ×3; mkdir
failure → exit 3). Verify cwd-isolation: from a subdirectory,
fire the wrapper with a test sprint-name; verify cwd is empty
post-run; verify evidence/reviews/<sprint>/round1/ contains
`review-kimi-k3-envelope.json` + `review-kimi-k3-stderr.log`.

Re-verify §6 (cross-family separation): the implementer's family
in the executor commit body is anthropic (claude-opus-5, executor
session overran in the planner session per invariant #1 caveat);
your family is kimi/moonshot; distinct.

Use exactly the envelope shape in §2: a single markdown `result`
body with sections Header / Round-by-round / Findings (TAML) /
Verdict. Trailing `VERDICT:` line is the only field the operator
parses.
