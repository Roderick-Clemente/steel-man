# tools/conventions/model-discipline.md

Operational form of `PRD.md` §17. Read this before invoking `droid exec` on a feature branch.

## Three rules

1. **Every invocation's model is recorded; separation-bearing seats are pinned.** Attribution (which model ran) is recoverable from the envelope; enforcement (guaranteeing family separation *before* the run) is not. So (per PRD §17.1): the **plan reviewer** and **validator** seats MUST pin `--model` (or a router family-exclude) before running, because a colliding family voids independence and post-hoc detection wastes the round; the **planner** and **executor** seats MAY use `--auto`, provided the resolved `modelId`/`providerLock`/`apiProviderLock` are recorded in the commit body and `telemetry/runs.jsonl`. An author seat on `--auto` runs a collision guard that swaps a same-family reviewer to the `claude-opus-4-8` fallback. This supersedes the earlier blanket "no silent `--auto`" — the rule is "always *know* the model, and pin wherever a family constraint must be guaranteed."
2. **Cross-family review is by design.** A non-author-family reviewer is required for any code that lands on `main`. Standing panel: `Gemini-Pro` + `Grok-4.5` (cross-family primary); `Claude-Opus-4.8` (fallback). `Codex-class` is excluded when the author was OpenAI-family.
3. **Telemetry data is git-ignored.** `telemetry/runs.jsonl`, `telemetry/findings.jsonl`, and `telemetry/dispositions.jsonl` never enter `git` history. Schema lives in `telemetry/SCHEMA.md`; aggregate script reads from a configurable path.

## Commit body recipe

See `tools/conventions/commit-body-recipe.md` for the exact format. Quick reference:

```
Model: gpt-5.4-mini (providerLock: openai, apiProviderLock: openai)
Role: executor
Reviewer-panel: gemini-2.5-pro, grok-4.5 (Codex excluded — same family as author)
```

## The wrapper

`tools/run-with-model.sh` is a thin bash wrap. It refuses to run unless `$DROID_MODEL_ID` is set in the environment. Use is:

```
DROID_MODEL_ID=gpt-5.4-mini bash tools/run-with-model.sh \
    droid exec --model "$DROID_MODEL_ID" \
        -f prompts/my-prompt.md \
        --auto low \
        --cwd <path> \
        > build-evidence/my-envelope.json
```

If `$DROID_MODEL_ID` is unset, the wrapper exits non-zero with a rule paragraph (the full §17.1 rule text — multi-line by design, not a one-line summary). The multi-line shape is what §17.5 requires reviewer-side transcripts to surface; failure modes should be unambiguous at the run transcript. Cheap insurance against the `--auto` foot-gun.

## Standing reviewer panel

Cross-family primary (review pass is recorded against one of these):

- **`gemini-2.5-pro`** (Google, providerLock: google)
- **`grok-4.5`** (xAI, providerLock: xai)

Cross-family fallback:

- **`claude-opus-4-8`** (Anthropic, providerLock: anthropic)

Same-family excluded when reviewing OpenAI-family-authored code:

- any Codex-class model

Reasoning captured in `droid-wiki/findings/reference-guard.md` and `tools/fixtures/rung7-reconciliation.md`.

## Migrating the data (long-term data-analysis plan)

The in-repo + `.gitignore` placement is the **build-phase shim**. It will not remain the permanent home. Migration is triggered by *any one* of:

1. Row count in any of the JSONLs exceeds ~500. (`grep -c` on `runs.jsonl`.)
2. Disposition data starts to carry identifiers that the public repo should not have (file paths, severity-coded tags tied to specific org context).
3. The §13 efficacy questions (`marginal cost per extra reviewer`, `fix rate by severity`, `family-asymmetry in defect category`) are being answered by ad-hoc scripts more than twice — that's the SQL pressure signal.

When the gate fires, choose one of two destinations — schema stays unchanged:

- **Sister private repo** (e.g., `Roderick-Clemente/adversarial-sprint-dev-telemetry`). Same `factory/...` branch convention. Git-able, shareable with collaborators. Aggregate script reads it via `$TELEMETRY_DATA_DIR` env.
- **Small data store** (DuckDB first; Postgres or SQLite next as row-counts grow). DuckDB reads JSONL with `SELECT … FROM read_json_auto('runs.jsonl')`; no ingest step. Most queries finish in milliseconds.

The aggregator script never reaches for the data path directly. It accepts the path from `$TELEMETRY_DATA_DIR` or `--data-dir`. So the move is a config change, not a code change.

## Open for review

- `telemetry/SCHEMA.md` is the schema source of truth. Suggest field additions there before changing the aggregator.
- New efficiency questions that need fresh aggregations: open a discussion in `phase-N/open-questions.md` rather than rewriting the aggregator for one query.
