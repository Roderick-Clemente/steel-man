# chunk-D4-1 PR-merge checklist

Two-step fix on the GitHub side. Both surface in the GitHub web UI — no CLI needed.

## 1. Title the PR with the chunk-id tag

When opening [https://github.com/Roderick-Clemente/adversarial-sprint-dev/pull/new/factory/d4-final-cleanup](https://github.com/Roderick-Clemente/adversarial-sprint-dev/pull/new/factory/d4-final-cleanup):

- **Title:** `[chunk:D4-1] chunk-D4-1: archive deferred 13 entries + relocate pilots/ → planning/`
- **Body:** paste from `PR-BODY.md` (sibling file).

The `[chunk:D4-1]` tag is parsed by `.github/workflows/adversarial-sprint-ci.yml` line ~146 (`m = re.search(r"\[chunk:([A-Za-z0-9_-]+)\]", title)`) and exposed as `steps.chunk.outputs.chunk_id`. Without it, downstream steps reference `test/.py` (empty interpolation) and the workflow bails.

## 2. Untick the gate from required-checks before merging

The `adversarial-sprint-review/gate` check will report failure regardless of `_PR title_` correctness, because GH-hosted `ubuntu-latest` does NOT ship the `droid` CLI (workflow comment, lines 9-13). The substantive cross-family verdict is recorded locally at `evidence/phase-4.5/build-evidence/r-chunk-d4-1-review-20260815-1423/SUMMARY.md` (kimi-k3 + minimax-m3, both `ACCEPT-WITH-NITS`).

UI path:

1. Go to: `github.com/Roderick-Clemente/adversarial-sprint-dev/settings/branches`
2. Click `main` in "Branch protection rules".
3. Under "Require status checks to pass before merging", search for `adversarial-sprint-review/gate` and untick it.
4. (Optional — keep `Adversarial Sprint review` ticked if you want visibility but not blocking.)
5. Click "Save changes."

Then merge the PR.

## Why option 2 is safe despite the CI failure

| Local source of truth | Status |
|---|---|
| `evidence/phase-4.5/build-evidence/r-chunk-d4-1-builder-20260815-0916/` | build bundle, 10 files, all green |
| `evidence/phase-4.5/build-evidence/r-chunk-d4-1-review-20260815-1423/SUMMARY.md` | cross-family review, kimi-k3 + minimax-m3 both ACCEPT-WITH-NITS |
| `git diff --find-renames --numstat fee5b37..HEAD` | 24 atomic `0 0` renames + 4 content edits |
| SHA-256 byte-identity vs D2 inventory | 20/20 verified, 0 mismatches |
| pytest, wiki-link-audit, plan-lint | green |

The CI gate is a redundant automated check on top of the local review; removing the gate from *required* doesn't invalidate any of the above. It's analogous to skipping a lint rule for a specific file — the substantive verification is independent.

## Follow-up queue

If you untick the gate and merge, the *underlying* problem (droid not on GH-hosted runner) is now repo-wide for any future PR until someone either (a) installs droid on a self-hosted runner and pins it in `.github/workflows/adversarial-sprint-ci.yml:55-58`, or (b) sets `$DROID_TARBALL_URL` as a repo variable pointing at a real droid tarball. Both are chunk-D5 candidates (paired with the tooling-doc codification). Flag for the chunk-D5 spec in `planning/evidence-hygiene/PROMPT-D5-PLANNER.md`.
