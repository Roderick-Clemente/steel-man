# chunk-`<NAME-TBD>`-wiki-linkupdate — re-anchor wiki after chunk-D5A evidence migration (operator-paste prompt)

You are running **chunk-`<NAME>`-wiki-linkupdate** on `adversarial-sprint-dev`. PR `<chunk-D5A-PR>` just landed chunk-D5A at commit `<chunk-D5A-SHA>` (you can `git log --oneline origin/main -5` to confirm). Behind you: chunk-D5A moved every artifact under `evidence/phase-4.5/build-evidence/<bundle>/roundN/...` to `evidence/reviews/<sprint>/round{N}/...`.

This chunk fixes the **wiki side** of that move. The wiki is a separate subtree (`droid-wiki/`, 62 tracked `.md` files as of chunk-D5-1b) and its own audit tool (`tools/wiki-link-audit.py`) checks for four failure classes declared at the script's docstring head. The chunk's contract is to leave the wiki **clean against that audit**.

`<NAME>` is operator-chosen. Two recommendations: `chunk-D7` (D-family continuity) or `chunk-wiki-linkupdate-1` (drops D-prefix, easier to count future wiki-link chunks). For this prompt read `<NAME>` as whatever you substituted.

## What this chunk does, what it doesn't

- **Does:** update `droid-wiki/**/*.md` so that every markdown link target resolves under the new canonical paths; re-run `tools/wiki-link-audit.py` to exit 0.
- **Doesn't:** add new wiki content unrelated to chunk-D5A's moves; touch `droid-wiki/methodology`-shaped pages that intentionally cite `phase-4.5/` as historical-context (those are fenced per PATH-REDIRECTS.md §5 rule and should be re-anchored only when the wiki says so, not because paths moved).

## Reachable context (read in order)

1. `tools/wiki-link-audit.py` (full file) — the four failure classes are: `dead` (target absent), `anchor` (matching heading missing), `absolute` (http(s):// in wiki — house-rule forbidden), `escaping` (wiki page links outside `droid-wiki/` subtree, edits resolve in git, 404 in published).
2. `planning/PATH-REDIRECTS.md` (full file) — keeps the §5 hard-stop rule citationally safe.
3. `tools/conventions/review-bundle.md` (skim §1 only).
4. `planning/evidence-hygiene/PLAN.md` — check tier assignment for **docs-only chunks**.
5. The chunk-D5A PR DESCRIPTION (find at `evidence/reviews/chunk-D5A-<...>/SUMMARY.md` or `git log -1 --format=%B <chunk-D5A-SHA>`) — confirms exactly which artifact bundles moved and where they landed; this is your source-of-truth for new paths.

## Recipe

### Step 1 — preflight

```
git fetch origin
git status --short                                     # clean
```

Confirm origin/main is the post-chunk-D5A tip. If chunk-D5A still hasn't merged, **stop and ping operator**.

### Step 2 — run the audit, capture the diff

```
python3 tools/wiki-link-audit.py 2>&1 | tee /tmp/wikilinks-before.txt
```

Expect a non-empty findings block (mostly `dead` class) because of D5A's `git mv`s. Capture the count by class.

### Step 3 — branch

```
git checkout -b factory/<NAME>-wiki-linkupdate origin/main
```

(matches chunk-D5A's `factory/<name>-sweep-and-migrate` shape; substitute `<NAME>` throughout.)

### Step 4 — list the `dead`-class findings and project targets

For each `dead` finding, the target file did not exist at audit time because chunk-D5A moved it. The new path is `evidence/reviews/<sprint-name>/<rest>` where `<sprint-name>` is the new bundle's name (chunk-D5A's prompt enumerated the rule). Recompute the mapping once and write it to `/tmp/wiki-pre/`:

```sh
# Per `evidence/phase-4.5/build-evidence/<bundle>` → `evidence/reviews/<sprint>/<rest>`
# Use the same routine chunk-D5A used:
sprint=$(printf '%s' "$bundle" \
  | sed -E 's/^r-//' \
  | sed -E 's/-[0-9]{8}-[0-9]{4,6}$//' \
  | sed -E 's/-[0-9]{8}$//')
```

### Step 5 — open each affected wiki page and edit

For every path in `/tmp/wikilinks-before.txt` of class `dead`, `anchor`, or `escaping`:

- Open `droid-wiki/<page>.md`.
- Substitute `evidence/phase-4.5/build-evidence/<bundle>` → `evidence/reviews/<sprint>`.
- If `escaping` (links outside `droid-wiki/`), do NOT rewrite — those are publish-boundary failures, not migration artifacts. Log them for operator review.

For `absolute` findings (http(s) URLs in the wiki): do NOT auto-fix. Those were scrubbed once and should not creep back; surface them for operator decision.

### Step 6 — re-run the audit; expect clean

```
python3 tools/wiki-link-audit.py
echo $?                                              # expect 0
```

If non-zero, **inspect the remaining failures class by class.** Migration-class should be zero. `absolute` and `escaping` are pre-existing policy issues, not yours to silently fix.

### Step 7 — capture the wiki-chunk-D5A cross-link addendum

If the wiki has a "what changed" page (often `droid-wiki/by-the-numbers.md` or `droid-wiki/background/open-questions.md`), append a note explaining: "Wiki re-anchored after chunk-D5A's evidence migration (PR `<chunk-D5A-PR>`, SHA `<chunk-D5A-SHA>`). The audit currently produces 0 findings."

If no such page exists, do not create one. Operator decoration, not yours to construct.

### Step 8 — commit topology

Two commits acceptable; one is acceptable too if the migration-to-wiki fallout is minimal:

| Option | Commits |
|---|---|
| A | (1) "wiki-linkupdate: plan + compat inventory for D5A migration" (planner), (2) "wiki-linkupdate: re-anchor pages to post-D5A canonical paths" (executor) |
| B | single commit "wiki-linkupdate: re-anchor pages after D5A" |

Use `claude-opus-5` in commit footers (mirrors chunk-D5A).

### Step 9 — push

```
git push -u origin factory/<NAME>-wiki-linkupdate
```

### Floor checks

- ✓ `python3 tools/wiki-link-audit.py` exit 0.
- ✓ Wiki tracked file count unchanged (62 → 62, or whatever the post-D5A count is if D5A also moved wiki).
- ✓ Migration-class (`dead` from chunk-D5A move) coverage = 100%.
- ✓ No `absolute` URLs introduced.
- ✓ No `escaping` links introsduced; pre-existing escaping findings surfaced, not auto-fixed.
- ✓ `python3 -m pytest -q` → 241 passed / 3 skipped (unchanged from chunk-D5A).

### Reviewer

Docs-only tier. Two paths the operator has approved historically; pick whichever is most fit:

(A) **Audit-script-only with kimi-k3** — wrap the chunk via `bash tools/run-review.sh kimi-k3 <prompt> chunk-<NAME>-wiki-linkupdate`. kimi-k3 reads the wiki diff and runs `tools/wiki-link-audit.py` itself to confirm PASS.

(B) **Mixed: peer-review by kimi-k3 on the wiki side, validate via audit-only.** The audit-script checks carry the contract; kimi-k3 looks for *semantic* regressions only (i.e., did a page stop referring to a specific finding because the path moved?).

Either path fires `bash tools/run-review.sh kimi-k3 <prompt> chunk-<NAME>-wiki-linkupdate`. If `--auto medium` errors, fall back to `bash tools/run-with-model.sh --auto high kimi-k3 <prompt>` per chunk-D5-1b / chunk-D5A signal.

### Surface

1. Copy `/tmp/wikilinks-before.txt` and the post-edit audit output to the bundle as `audit-before.txt` and `audit-after.txt`.
2. Write `SUMMARY.md` with: verdict table + floor-check column + nits (TAML) + the four-class count delta.
3. Hand off to operator with: verdict, envelope SHA, nits, PR URL `https://github.com/Roderick-Clemente/adversarial-sprint-dev/pull/new/factory/<NAME>-wiki-linkupdate`.

## Out of scope — explicit fence

This chunk does NOT do:

- Pilot chunk (`<NAME>-pilot-qbank`).
- New wiki content (only re-anchoring of existing content).
- Reformatting the wiki (no fence-post changes; preserve style).
- `planning/evidence-hygiene/` or `tools/` source-of-truth changes.
- Pulling `evidence/phase-4.5/build-evidence/legacy-duplicates/` paths into the wiki even with a redirect — they're fenced.

End operator-prompt.
