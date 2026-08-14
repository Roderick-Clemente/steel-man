# Phase 2 — KNOWN-ISSUES (operational findings during the slice)

## KI-1 — reviewer/planner autonomy floor for `Execute` in `droid exec`
- **Read-only autonomy gates the `Execute` tool entirely.** A reviewer invoked
  with `--enabled-tools Read,Glob,Grep,LS,Execute` at the default (read-only)
  autonomy exits immediately: `num_turns:0`, `is_error:true`, "insufficient
  permission to proceed. Re-run with --auto medium". (First brief-review Grok
  attempt.)
- **Brief review worked at `--auto medium`.** Both brief reviewers completed at
  `medium`.
- **Blind plan review required `--auto high`.** At `medium` the plan reviewers
  again exited `num_turns:0` ("Re-run with --auto high"). Cause: the first
  verification step reached for a binary (`sqlite3` on the pilot DB to check the
  count-gated-seed claim), which `medium` gates and `high` allows.
- **Mitigation used:** reviewers run at `--auto high` with only
  `Read,Glob,Grep,LS,Execute` enabled — no editor tool, so they cannot call
  Edit/Create/ApplyPatch/MultiEdit.

## KI-2 — at `--auto high`, a reviewer can still write files via `Execute` shell
- Even with no editor tool enabled, Gemini wrote its verdict to
  `phase-2/reviews/plan-review.md` via a shell redirect during the plan review.
- **Impact:** benign here (a duplicate of its envelope `result`), but it means
  "no editor tools" does **not** fully sandbox a reviewer at `high`; `Execute`
  is a write vector.
- **Implication for future runs:** if strict read-only reviewers are required,
  either (a) drop `Execute` and rely on native `Read/Grep/Glob/LS` (loses shell
  verification like `sqlite3`), or (b) run reviewers in a throwaway working copy
  / sandbox so stray writes cannot touch the audited tree.

## KI-3 — planner pinned this run (not auto-routed)
- The §17.1 attribution-vs-enforcement amendment (auto-router at author seats)
  is on `factory/convention-model-discipline-v2`, **not merged to `main`**. To
  stay compliant with current `main` §17.1, the planner was **pinned** to
  `claude-opus-5` this run rather than auto-routed. The collision guard was
  therefore not exercised; it remains the documented future default once the
  amendment lands.
