# Panel input — Phase 4.5 build review (pass-r1)

**Panel seat:** Factory Droid (Anthropic/claude-family), single-family
participation via `tools/run-with-model.sh` wrapper.
**Envelope:** `phase-4.5/build-evidence/r-panel-pass1/envelope.json`
**Verdict (last line):** `REJECT_IMPLEMENTATION`

Single-family participation is named here as a **clean-null** per
PRD §13 because cross-family independence is the §17.2 the gate
depends on. Recorded per OPERATING-RULES §11 + §12.

The panel independently walked the build and surfaced findings the
build's own `stage-a` cross-perspective review did not catch.
Target of review: the four structural decisions in the build
brief. Extra findings (F-8 onwards) came from a wider audit that
the panel conducted on its own initiative; these are real and
in-scope for the build passage.

## Verbatim findings

### Decision 1 — Family guard widening (state.py)

**Verdict from panel: ACCEPT the widening. Implementation incomplete.**

- **F-1 (blocker)** — `state.py:412` overwrites the second reviewer
  in `by_role`. The `for a in assignments` loop catches collision
  via `seen_reviewer_families`, but the planner-vs-reviewer
  comparison uses `by_role.get(Role.PLAN_REVIEWER)` (single
  lookup), which only checks the last reviewer — so if reviewer 1
  collides with planner but reviewer 2 doesn't, the guard passes
  silently. Fix: iterate reviewers, compare against the planner
  family each time.

- **F-2 (high)** — `FamilyGuardOutcome`'s docstring claims a
  post-resolution re-check that doesn't exist. The runner calls
  the guard preflight once. After planner/executor resolve, no
  re-check runs. Either implement the re-check or drop the claim
  from the docstring + record the gap in KNOWN-ISSUES.

- **F-3 (medium)** — `config.to_role_assignments` and
  `sprint-loop.py:_parse_validator_inline` accept `model:provider:family`
  and take `family` verbatim, bypassing `MODEL_FAMILY_MAP`.
  Per-invocation inline declaration defeats the §4 curated-map
  rule. Fix: refuse when `model not in MODEL_FAMILY_MAP`.

### Decision 2 — Skill three-layer hybrid

**Verdict: ACCEPT-WITH-NITS.**

- **F-4 (medium)** — SKILL.md may not load at all. The skill
  asset has no YAML frontmatter; some skill loaders require it.
  Fix: add a YAML frontmatter block (`name`, `description`,
  `when-to-invoke`).

- **F-5 (low)** — sub-rule 4 prose has a stray artifact:
  `under the `OPERATING-RULES §14 (shim / wrapper present) ` plus inline`.
  Fix in-pass.

### Decision 3 — §18 OPERATING-RULES addition

**Verdict: ACCEPT-WITH-NITS on the rule; converge on
`Source:` line rather than two-tier taxonomy.**

- Panel preference: a uniform `Source:` and `Review-date:` line
  on every rule, not a badge on §18 alone. Sample-size recorded
  as "promoted from one build, phase-4.5, 2026-08-09" rather than
  a tier label.

### Decision 4 — Reconcile gate = stdin pause

**Verdict: ACCEPT-WITH-NITS. Decision right; framing overstates.**

- **F-6 (high, independent of this decision)** —
  `--skip-reconcile` is already an unconditional auto-accept
  (`sprint-loop.py:968`). It is more dangerous than the flag the
  build considered rejecting. Recommend: deprecate, replace with
  `--accept-on-dual-accept` guarded by preconditions.

- **F-7 (high)** — nothing machine-checks §5.3 convergence
  preconditions. `reviewer1 = run_plan_reviewer(...)` at
  `sprint-loop.py:958` is assigned and never used. Verdicts are
  printed and discarded. No verdict field on RunState. Fix:
  store verdicts + plan_sha256; refuse `accept` while any
  blocker/high finding is `status="open"`.

- Flag location: runner-level, alongside `oversight`.

### Additional findings

- **F-8 (high) — unbounded retry recursion in
  `tools/sprint_loop/droid.py:364-372`.** Recursion re-enters
  with `attempts = 0` (fresh local), so the guard never
  converges. Each recursion fires a fresh `droid exec` call.
  Contrast with `orchestrate-review.py` which loops correctly.
  **Fix: convert to a loop, or pass `attempts + 1` explicitly.**

- **F-9 (medium) — `tools/sprint_loop/backends.py` has three
  identical dry-run blocks at `:141`, `:216`, `:244`.** Lines
  `:216` and `:244` are unreachable; the third is past
  `subprocess.run`'s argv construction. Delete two of the three.

- **F-10 (medium) — `LocalBackend` mints a random signing key
  when `EVIDENCE_SIGNING_KEY` is unset.** Producer and verifier
  share the same per-process secret; the HMAC verifies whatever
  the process produced and proves nothing cross-process. The
  §7 fail-closed claim is wrong here. **Fix: refuse closed when
  the key is unset.**

- **F-11 (low) — dead code in `state.py:427`:** the line
  `pr2 = by_role.get(Role.PLAN_REVIEWER + "_2ND")` evaluates
  to `"reviewer_2ND"`, never matches an enum key. Remove with F-1.

## Doc drift (low)

- `KNOWN-ISSUES.md` says 52 tests; `BUILD-NOTES.md` sums to 52;
  this prompt says 56; the file defines 56.
- `BUILD-NOTES.md` says "7 chunks"; the branch has 9 commits.

## What the panel would gate on

F-1 and F-2 (widened guard does not enforce what it claims; one
gap reachable via standing fallback), F-8 (unbounded paid retry),
F-4 (skill may not load at all). F-7 (the difference between
"human in the seat" and "human in the seat and the machine
refuses to advance past a blocker") is the one the panel would
want fixed before the first real pilot run.

## Disposition target for chunk 10

- **Fix now**: F-1, F-2, F-7, F-8, F-3, F-9, F-10, F-11
- **Fix in-pass**: F-5
- **Disposition with note**: F-4 (add frontmatter — small change
  in chunk 10), F-6 (deprecate `--skip-reconcile` in chunk 10),
  Doc drift (in PASS)
- **Disposition with note**: Decision 3 §18 — record the panel's
  preference but don't rework the rule.
- **Named gap if any deferred**: F-6's flag replacement.
