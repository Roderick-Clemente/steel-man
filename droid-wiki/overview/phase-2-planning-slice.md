# Phase 2 — the adversarial planning slice

**Phase 1 proved the loop can review code it wrote. Phase 2 asks the earlier
question: can the loop review a *plan* before a line is written, and reach an
approval bound to that plan's exact bytes?** The answer, on one real slice, is
yes — and the interesting part is that the adversarial value showed up *before*
the panel ever ran.

The slice is a read-only `GET /profile` page for the pilot bank
(`~/work/quantum-bank--llms-txt-pilot`): render the session-authenticated user's
`username`, `email`, `full_name`, and a themed address (Jean-Luc Picard,
`jpicard@starfleet.fed`, "Captain's Quarters, Deck 9, USS Enterprise
NCC-1701-D"). Session-scoped, no `?id=` parameter (so it introduces no object
reference to enumerate), no write path. Small on purpose; the point is the
*plan*, not the feature.

The PRD §11 Phase 2 exit is verbatim: *"one real plan reaches a hash-bound
approval or a correctly escalated non-convergence state."* This run reached the
first branch.

## Two review stages, one target each

Unlike Phase 1's three rounds on a moving code tip, Phase 2 has two distinct
targets: first the **brief** (the contract for what the plan must do), then the
**plan** itself. Each got an independent, single-blind, cross-family pair. Runs
were sequential, not parallel — a deliberate budget-safety choice on a
zero-buffer token budget (observe the first call before spending the second),
which paid off immediately: the very first reviewer invocation exited
`num_turns:0` on a permission gate, and sequential execution meant that cost
~10k tokens instead of doubling it.

### Stage 1 — the brief

| reviewer | family | decision | duration | num_turns | tokens (in/out/think) | key takeaway |
|---|---|---|---|---|---|---|
| Grok (`grok-4.5`) | xAI | ACCEPT-WITH-NITS | 275s | 8 | 56898 / 13992 / 7701 | 3 majors: collision-guard must stop on `unknown` family; planner over-scoped to the full executor editor set; severity/category schema fork vs `SCHEMA.md` |
| Gemini (`gemini-3.1-pro-preview`) | google | ACCEPT | 220s | 21 | 697367 / 14955 / 4307 | 0 findings — verified schema claims against `models.py:128` / `api/login.py:16` |

All three of Grok's majors were folded into brief v2 before any paid planner
call: the collision guard now fails closed on any family that cannot be *proved*
distinct (PRD §4: `unknown` cannot satisfy a hard separation constraint); the
planner seat was scoped read-only on the pilot with write access only to its own
plan artifact; and a severity/category crosswalk (`§5.3 ⇄ telemetry/SCHEMA.md`)
replaced what would have been a silent schema fork.

### Stage 2 — the plan

The planner seat was **pinned** to `claude-opus-5` (anthropic) — family-distinct
from both reviewers, and compliant with current-`main` §17.1 without depending on
the unmerged attribution-vs-enforcement amendment. It drafted `plan-v1.md`
(`Plan-hash: sha256:72eccff5…`), reviewed single-blind by the same pair:

| reviewer | family | decision | duration | num_turns | tokens (in/out/think) | key takeaway |
|---|---|---|---|---|---|---|
| Grok (`grok-4.5`) | xAI | APPROVE | 414s | 9 | 45737 / 21072 / 15067 | 0 blocking/high; 3 medium (AC don't bind Picard; risk table missing §5.2 columns; test plan doesn't falsify DB-vs-session source-of-truth) + 3 low |
| Gemini (`gemini-3.1-pro-preview`) | google | APPROVE | 132s | 11 | 478038 / 11733 / 2805 | 0 findings — "highly accurate, well-grounded, falsifiable tests" |

Both families APPROVE with **zero blocking and zero high**, so no reconciliation
round was needed. The plan-v1 artifact is frozen at its hash to keep the approval
bound to its exact bytes; Grok's six non-blocking findings are accepted as
amendments A1–A5 in `phase-2/findings.md` and become binding acceptance criteria
for the Phase 3 executor — not re-planned, because the deltas are the reviewer's
own `recommended_change` fields (no new design).

## The adversarial value landed before the panel ran

The most striking result is not a panel finding. The planner, given a prompt
with three wrong file anchors, **verified and corrected them itself**:
`api/accounts.py` not `api/account.py`; `test/` not `tests/`
(`pytest.ini:2`); and the query helper is `_sql` (`models.py:52`), not the
brief's `_convert_query`. It then found the load-bearing argument the brief had
only half-seen: option (a) "add an `address` column" is not "one column in two
schemas" — both builders use `CREATE TABLE IF NOT EXISTS` and
`_apply_postgres_schema` only replays `001_initial.sql`, so **there is no
`ALTER TABLE`, no migration runner**; on any existing database the column never
appears, and the seed is count-gated (`models.py:414-416`) so it would not fill
it anyway. That single grounded fact turned the address fork from a coin-flip
into a clear least-scope call: option (b), a config constant behind the getter
with a migration TODO.

A plan review's job is to make that reasoning legible and falsifiable *before*
code is written. Here it did, and both families could then verify it against the
tree rather than argue about it.

## Cross-family divergence — the §13 calibration signal

Phase 1's headline was that each family's blind spot differed (Gemini caught
hook-security bypasses Grok missed; Grok caught valid-red gaps Gemini missed).
Phase 2 produced the *opposite-looking* data point, which is itself the signal:

| stage | Grok (panel position 1) | Gemini (panel position 2) |
|---|---|---|
| brief review | 3 majors + nits | 0 findings |
| plan review | 3 medium + 3 low | 0 findings |

Every finding this slice was `first_seen_in_panel_position = 1` (Grok). Because
the two sessions are independent and single-blind (Gemini never saw Grok's
output), this is a pure family/model divergence, not an ordering artifact: on
*specification and planning* artifacts, Grok was the finder and Gemini the
confirmer, the mirror of Phase 1 where Gemini was the security finder on *hook
code*. That is exactly the kind of task-conditioned divergence
`first_seen_in_panel_position` exists to accumulate (`telemetry/SCHEMA.md`), and
it is the input handed to Phase 5 calibration. One family alone would have
either shipped an under-specified brief (Gemini-only) or had no independent
confirmation (Grok-only).

## Operational findings (KNOWN-ISSUES)

Running paid reviewers unattended surfaced two runtime facts, both recorded in
`phase-2/KNOWN-ISSUES.md`:

1. **Autonomy floor for `Execute` in `droid exec`.** Read-only autonomy gates the
   `Execute` tool entirely (`num_turns:0`, "re-run with --auto medium"). Brief
   review worked at `--auto medium`; blind *plan* review needed `--auto high`,
   because the first verification step reached for a binary (`sqlite3` on the
   pilot DB to check the count-gated-seed claim), which `medium` gates.
2. **`--auto high` + `Execute` is a write vector even with no editor tool.**
   Gemini wrote its verdict to a file via a shell redirect. Benign here, but it
   means "no editor tools enabled" does not fully sandbox a reviewer at `high`;
   strict read-only reviewers would need `Execute` dropped or a throwaway working
   copy.

## Tokens spent

The full footprint across both stages (5 completed sessions):

- **Non-cached input:** ~1.28M tokens. **Output:** ~101k. **Thinking:** ~35k.
- **`cache_read`:** ~4.48M — dominated by the pinned planner (3.16M alone) and
  Gemini re-hitting the pilot tree. Cache reads are the cheap tokens; the planner
  spent only 88 *non-cached* input tokens.
- Two `num_turns:0` permission misfires cost ~40k total, negligible — the price
  of learning the autonomy floor live rather than at 3am.

The lever is the same as Phase 1: a cross-family panel under `--enabled-tools`
and `--model <id>` is reproducible to the byte, and it caught a schema fork and
an over-scoped planner seat in a *brief* — before a single line of the feature,
or a single dollar of executor time, was spent.

## What Phase 2 leaves for Phase 3

A hash-bound, panel-approved plan (`sha256:72eccff5…`) awaiting only the human
plan-approval gate (PRD §6 — the loop never self-approves the plan). Phase 3 is
the other half of the loop: take this approved plan, build `/profile` for real,
and run the same cross-family panel on the *code*. When that lands, the loop has
been shown end to end — plan → execute → review — on one real slice, and the
harness is usable on real work.
