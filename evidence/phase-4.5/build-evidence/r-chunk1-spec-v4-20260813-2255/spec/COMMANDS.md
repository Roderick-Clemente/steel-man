# Exact reviewer invocations — run r-chunk1-spec-v4-20260813-2255

Artifact under review: `planning/layout-refactor/CHUNK-1-SPEC.md` v3
Commit: `43a2ff3`
Branch: `factory/layout-refactor`
Builder model: claude-opus-5 (claude-family)
Panel: grok-4.5 (grok-family) + gemini-3.1-pro-preview (gemini-family)
§17.2: all three families distinct.

PROMPT.md sha256 is in `PROMPT.sha256` (same bytes fed to both seats).

## grok-4.5

```
bash tools/run-with-model.sh droid exec --model grok-4.5 \
  -f phase-4.5/build-evidence/r-chunk1-spec-v4-20260813-2255/spec/PROMPT.md \
  --auto low --enabled-tools Read,Grep,Glob,LS --output-format json \
  --cwd "$PWD" \
  > phase-4.5/build-evidence/r-chunk1-spec-v4-20260813-2255/spec/grok-4.5.json \
  2> phase-4.5/build-evidence/r-chunk1-spec-v4-20260813-2255/spec/grok-4.5.stderr.txt
```

## gemini-3.1-pro-preview

```
bash tools/run-with-model.sh droid exec --model gemini-3.1-pro-preview \
  -f phase-4.5/build-evidence/r-chunk1-spec-v4-20260813-2255/spec/PROMPT.md \
  --auto low --enabled-tools Read,Grep,Glob,LS --output-format json \
  --cwd "$PWD" \
  > phase-4.5/build-evidence/r-chunk1-spec-v4-20260813-2255/spec/gemini-3.1-pro-preview.json \
  2> phase-4.5/build-evidence/r-chunk1-spec-v4-20260813-2255/spec/gemini-3.1-pro-preview.stderr.txt
```

Reviewers run read-only (`--enabled-tools Read,Grep,Glob,LS`). Builder holds
no signing key. Fired sequentially, not in parallel, per the
r-chunk1-spec-v2 burn disposition.
