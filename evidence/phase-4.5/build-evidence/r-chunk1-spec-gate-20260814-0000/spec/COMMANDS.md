# Reviewer invocations — spec gate on CHUNK-1-SPEC v5

Artifact: `planning/layout-refactor/CHUNK-1-SPEC.md`
Artifact sha256: `558f9956a4f029ad23b9c516ce8f49e5035da9e5f220e6f21ebbf5f26998beea`
Repo commit: `d3c8005`
Branch: `factory/layout-refactor`
PROMPT.md sha256: `8c44a29d9b94e2b6971bc7f688d63fca18c4420f6fb9efd4f67ab0fe5861f654`

Both seats receive the SAME prompt bytes and review the SAME artifact bytes,
per the gate rule (ACCEPT / ACCEPT-WITH-NITS from two distinct families on the
same bytes).

Panel: grok-4.5 (grok-family), gemini-3.1-pro-preview (gemini-family).
Planner/orchestrator: claude-opus-5 (claude-family). All three distinct, §17.2.

grok-4.5 here is a REGRESSION check — it authored the v3 and v4 findings, so it
is verifying its own findings were fixed correctly. gemini-3.1-pro-preview is
the INDEPENDENCE pass: it has not seen this artifact since PLAN v1.

```
bash tools/run-with-model.sh droid exec --model grok-4.5 \
  -f phase-4.5/build-evidence/r-chunk1-spec-gate-20260814-0000/spec/PROMPT.md \
  --auto low --enabled-tools Read,Grep,Glob,LS --output-format json --cwd "$PWD" \
  > .../grok-4.5.json 2> .../grok-4.5.stderr.txt

bash tools/run-with-model.sh droid exec --model gemini-3.1-pro-preview \
  -f phase-4.5/build-evidence/r-chunk1-spec-gate-20260814-0000/spec/PROMPT.md \
  --auto low --enabled-tools Read,Grep,Glob,LS --output-format json --cwd "$PWD" \
  > .../gemini-3.1-pro-preview.json 2> .../gemini-3.1-pro-preview.stderr.txt
```

Reviewers are read-only. The planner holds no signing key and writes no token.
