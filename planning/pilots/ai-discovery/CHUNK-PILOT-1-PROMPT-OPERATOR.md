# chunk-`<NAME-TBD>`-pilot-qbank-discovery — first plugin run on the qbank ai-discovery pilot (operator-paste prompt)

You are running **chunk-`<NAME>`-pilot-qbank-discovery** on `adversarial-sprint-dev`. PRs `<chunk-D5A-PR>` (chunk-D5A) and `<chunk-wiki-linkupdate-PR>` (wiki re-anchor) have landed; the repo is on the post-migration tip of origin/main. The chunk-D5-1b tooling — `tools/run-review.sh <modelId> <prompt> <sprint-name>`, sprint-keyed outputs at `evidence/reviews/<sprint>/round{N}/`, family-separated reviewer gate — is in place and inherits clean state.

`<NAME>` is operator-chosen. Three candidates: `chunk-D-pl1` (D-family + `pl` plugin subletter, mirrors `chunk-D5-1a`/`chunk-D5-1b`), `chunk-pilot-1` (drops D-prefix; new letter-family for plugin runs), or `chunk-qbank-1` (project-anchored). For this prompt read `<NAME>` as your pick; `<sprint>` defaults to `qbank-ai-discovery`.

## What this chunk does

Translate the **manual** pilot at `planning/pilots/ai-discovery/` (4 units, qbank.dev, Grok + Kimi adversarial reviews, hand-run with operator-held isolation) into a **plugin run** that:
- Routes outputs through the codified tooling rather than ad-hoc dirs.
- Captures cross-family reviewer outputs under the sprint-keyed canonical root.
- Produces a measurable **plugin-baseline** that can be compared to the manual arm.

The pilot README ends with: *"This is the manual arm the plugin will later be measured against."* This chunk is the measurement-rig.

## Reachable context (read in order)

1. `planning/pilots/ai-discovery/README.md` (full) — defines the 4 units, reviews, and H1 evidence lens.
2. `planning/pilots/ai-discovery/validator-outputs/kimi-nits-and-charset.md` (full) — Kimi's verbatim review.
3. `planning/pilots/ai-discovery/validator-outputs/grok-ai-discovery-review.md` (full) — Grok's verbatim review.
4. `planning/pilots/ai-discovery/validator-outputs/sitemap-unit4-validation.md` (full) — Unit 4 close-out.
5. `tools/conventions/review-bundle.md` (full) — bundle shape you'll inherit; ≥ 2 exemplar citations floor.
6. `tools/run-review.sh` (the chip). Already verified at chunk-D5A's 5-nit-sweep round.
7. `tools/sprint_loop/config.py:59` `MODEL_FAMILY_MAP` — keep the disjointness: implementer ≠ reviewer family.
8. `planning/evidence-hygiene/PLAN.md` — three review-tier roof.
9. `droid-wiki/findings/first-h1-evidence.md` (skim; the wiki side reads this — already re-anchored by the prior chunk).

## Recipe

### Step 0 — pick the chunk's `<NAME>` placeholder

If `<NAME>` is still unset, ask operator. Default fallback: `chunk-pilot-1`. Branch: `factory/<NAME>-pilot-qbank`.

### Step 1 — preflight

```
git fetch origin
git status --short                              # clean
python3 -m pytest -q                             # 241 / 3 (chunk-D5A invariant)
python3 tools/wiki-link-audit.py                 # exit 0 (chunk-WIKI invariant)
python3 tools/plan-lint.py planning/pilots/ai-discovery/../*.md   # if applicable
```

### Step 2 — author the chunk's spec/builder pair

Two new files under `planning/pilots/ai-discovery/`:

- `<NAME>-SPEC.md` — authoritative chunk definition. Header: prior chunk SHAs (`331a7f8` chunk-D5-1b, `<chunk-D5A-SHA>`, `<wiki-SHA>`). §1 setup. §2 surface list (the 4 qbank units + validator surface + the plugin-baseline artifact matrix). §3 floor checks. §4 out-of-scope fence.
- `<NAME>-BUILDER-PROMPT.md` — the executor's instruction set. Structure: step 0 (rehydrate) → step 1 (preflight) → step 2 (branch) → step 3 (re-create the 4 units via plugin tooling — see Step 4 below) → step 4 (capture validator outputs) → step 5 (commit topology) → step 6 (push) → step 7 (fire reviewer).

### Step 3 — branch

```
git checkout -b factory/<NAME>-pilot-qbank origin/main
```

### Step 4 — re-create the 4 units via plugin tooling

The pilot README identifies the 4 units:
1. `/llms.txt` (short manifest)
2. `/robots.txt`
3. `/llms-full.txt`
4. `/sitemap.xml`

The plugin run's job is **NOT** to push to qbank.dev — that already happened. Plugin run is **shadow**: re-create each unit in a sandbox / local placeholder dir, capture reviewer findings under the sprint-keyed canonical root.

Suggested shadow setup:
- Create `evidence/sandbox/qbank-prod-2026-08-15/{llms,robots,sitemaps}/...` with stub files reflecting the post-pilot state.
- Or, if there's an off-line qbank-clone tool/spec, use that. (No such tool is documented at §1 reachable context; if you can't find one, **stop and ping operator — do not invent a sandbox.**

### Step 5 — capture cross-family validator outputs

Two validators per the manual arm: **Kimi** (moonshot/kimi-family) and **Grok** (xai / `grok-4.5`-equivalent). Fire them via `tools/run-review.sh`:

```
bash tools/run-review.sh kimi-k3 <gv-prompt-file> <sprint>
bash tools/run-review.sh grok-4.5 <gv-prompt-file> <sprint>
```

`<gv-prompt-file>` is a per-validator prompt — `prompts/<validator>-ai-discovery.md` — that the chunk's BUILDER-PROMPT writes. It should reproduce the manual arm's "fresh context, no executor build-log read" invariant (the manual arm relied on operator convention; the plugin arm enforces it by giving the validator a literal statement "do not read the executor's reasoning").

Round-derive allocates `round1/` for the first call, `round2/` if you re-fire within the same sprint.

### Step 6 — write the plugin-baseline matrix

At `evidence/reviews/<sprint>/round1/`, write `baseline-matrix.md`. Cols: validator (Kimi, Grok); rows: 4 units + 1 cross-unit row. Cells: finding material/overlap/none. Compare against the manual arm (`validator-outputs/`) cell-by-cell.

This is the chunk's primary artifact. The original manual arm's findings are the "arm 1" baseline; this chunk produces "arm 2" (plugin run). The matrix shows agreement / divergence / unique-only.

### Step 7 — commit topology

Three commits on `factory/<NAME>-pilot-qbank`:

1. **Planner** — `<NAME>-SPEC.md` + `<NAME>-BUILDER-PROMPT.md` (and per-validator prompts). Subject: `chunk-<NAME>: scaffold plugin-run spec + builder prompt`.
2. **Executor — pilot re-run** — sandbox files + reviewer outputs at `evidence/reviews/<sprint>/round1/` + `baseline-matrix.md`. Subject: `chunk-<NAME>: run 4 units + capture cross-family validators + baseline matrix`.
3. **(Optional) Executor — wiki cross-link** if the wiki side needs to reference the matrix. Skip unless explicitly needed.

Use appropriate model declarations on each commit's footer. Pick the model for the implementer role from the project's `tools/sprint_loop/config.py:MODEL_FAMILY_MAP` disjoint from the validator families (kimi-k3, grok-4.5). Probably `<claude-opus-5>` or `<anthropic-family>` shared with chunk-D5A's commits is fine.

### Step 8 — push

```
git push -u origin factory/<NAME>-pilot-qbank
```

### Floor checks

- ✓ 4 units present in sandbox.
- ✓ At least 2 cross-family validators fired (kimi, grok).
- ✓ Round-derive produced `round1/` first; re-fires → `round2/`.
- ✓ `baseline-matrix.md` cell-count = `2 validators × 5 rows` = 10 cells; each is `material | overlap | none`.
- ✓ Direct `git ls-files evidence/phase-4.5/ | grep -v legacy-duplicates` returns nothing.
- ✓ `python3 -m pytest -q` 241 / 3 unchanged.
- ✓ `python3 tools/wiki-link-audit.py` exit 0 (wiki invariant preserved).

### Reviewer

Benchmark-tier per `planning/evidence-hygiene/PLAN.md §2`. This means: 2 reviewers (one per family; signature-rule applies — disjoint from implementer family). Suggest:

| Role | Model | Family |
|---|---|---|
| Implementer | `claude-opus-5` (or whatever the project uses for chunk planning) | anthropic / claude-family |
| Reviewer-A | `kimi-k3` | moonshot / kimi-family |
| Reviewer-B | `grok-4.5` | xai / grok-family |

Fire one at a time:

```
bash tools/run-review.sh kimi-k3 <chunk-prompt> <sprint>
bash tools/run-review.sh grok-4.5 <chunk-prompt> <sprint>
```

If `--auto medium` fails for either, use `--auto high` via `bash tools/run-with-model.sh --auto high <model> <prompt> <sprint>` (alternate invocation pattern from chunk-D5A signal).

### Surface

1. Python-level write `baseline-matrix.md` to `evidence/reviews/<sprint>/round1/`.
2. Write `SUMMARY.md` per `tools/conventions/review-bundle.md §3`: matrix cell counts + per-validator nits + cross-family overlap cell highlighted (material findings both caught vs neither caught vs unique-to-one).
3. Hand off to operator: verdict + per-validator envelope SHA + baseline matrix summary + PR URL `https://github.com/Roderick-Clemente/adversarial-sprint-dev/pull/new/factory/<NAME>-pilot-qbank`.

## Out of scope — explicit fence

This chunk does NOT do:

- Wiki updates (chunk-WIKI does that).
- Migration (chunk-D5A does that).
- Push live changes to qbank.dev.
- A second `evidence/phase-4.5/`-flavored pilot. Phase-4.5 is fenced.
- New reviewer models beyond Kimi/Grok (manual-arm parity keeps cross-family lens at 2).

End operator-prompt.
