# tools/conventions/commit-body-recipe.md

Recipe for the body of a code-bearing commit on a `factory/`, `codex/`, or `claude/` branch.

## Mandatory lines

```
Model: <modelId> (providerLock: <provider>, apiProviderLock: <provider>)
Role: <planner|executor|validator|reviewer>
```

- `<modelId>` is the resolved model id string passed via `--model <modelId>`. **This rule excludes silent `--auto` invocations. Compute the model id before invoking and stamp it here.**
- `<provider>` is the value of `providerLock` from the inner session, or "openai" / "google" / "xai" / "anthropic" etc. if it is not yet known.
- `Role` is which role the run played in the loop. Reviewer-passes carry `Role: reviewer`; cross-family review carries the additional `Reviewer-panel:` line below.

## Reviewer-pass additional line (mandatory)

When `Role: reviewer`, add:

```
Reviewer-panel: <comma-separated list of modelIds the panel included>
```

If the author was OpenAI-family, the panel **must** not include Codex-class. State the constraint explicitly when relevant:

```
Reviewer-panel: gemini-2.5-pro, grok-4.5 (Codex excluded — same family as author)
```

If no panel model is in the line, the run is non-compliant with `PRD.md` §17.2 and Phase 3 acceptance gates flag it.

## Mandatory trailer lines

End of the body, immediately before the Co-Authored-By trailer:

```
Telemetry-row: telemetry/runs.jsonl:<run_id>
Findings: <count>: <comma-separated finding_ids surfaced in this run>
Dispositions: <comma-separated <id>:<disposition>@<sha> tuples, if this run closes findings>
```

These trailers appear on **every** kind of body — executor, validator, and reviewer passes all carry `Telemetry-row:`. Reviewer passes additionally carry `Findings:` because every reviewer run surfaces at least zero findings (an empty `Findings:` line with count=0 is the legitimate closure). Disposition trailers appear only on commits that close prior reviewer findings.

`<run_id>` is stable per `droid exec` invocation; the same id appears in the per-run telemetry row. One line per invocation; one line per coincident dispositions or findings.

## Worked examples

### Executor commit on feature work

```
Implement the lock manifest schema: tests for locked tests, JSON manifest shape.

Model: gpt-5.4-mini (providerLock: openai, apiProviderLock: openai)
Role: executor

Added tools/manifest.py with the lock schema: SHA-256 of the test file
recorded at lock time with accepted_at + accepted_assertion.

Telemetry-row: telemetry/runs.jsonl:r-executor-2026-08-05-001

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>
```

### Reviewer pass on a feature branch

```
Review factory/phase-1-test-evidence against the Phase 1 brief exit criteria.

Model: gemini-2.5-pro (providerLock: google, apiProviderLock: google)
Role: reviewer
Reviewer-panel: gemini-2.5-pro, grok-4.5 (Codex excluded — same family as author)

Three findings against the test-locking schema and two against the valid-RED
classifier; one blocking on the test file's hash set at lock time.

Telemetry-row: telemetry/runs.jsonl:r-reviewer-2026-08-05-002
Findings: 5: F-1a2b3c, F-4d5e6f, F-7g8h9i, F-0j1k2l, F-3m4n5o

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>
```

### Disposition commit closing prior-reviewer findings

```
Implement the fixes flagged in review of factory/phase-1-test-evidence.

Model: gpt-5.4-mini (providerLock: openai, apiProviderLock: openai)
Role: executor

Lookup-the-hash fix in tools/manifest.py; valid-RED edge case handled
in tools/classifier.py. Closes all five findings from the panel review.

Telemetry-row: telemetry/runs.jsonl:r-executor-2026-08-05-014
Dispositions: F-1a2b3c:fixed@abc1234, F-4d5e6f:fixed@abc1234, F-7g8h9i:fixed@abc1234, F-0j1k2l:fixed@abc1234, F-3m4n5o:fixed@abc1234

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>
```

## Compactness

The above is the *complete* recipe; cases where parts genuinely do not apply (e.g., a docs-only commit) drop the `Role:` line and the `Telemetry-row:` line. The `Model:` line still applies — model choice is not bypassed by commit type.
