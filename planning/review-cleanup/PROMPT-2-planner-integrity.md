# Operator prompt — review-cleanup stack, PR 2: planner integrity + seat reachability

Repo: /Users/factory/work/adversarial-sprint-dev (all work stays local; do NOT push, do NOT open a PR, do NOT touch untracked *.orig files or untracked evidence/ dirs).

Goal: PR 2 of a stacked split of branch factory/schema-v3-and-subagent-executor. Base: branch factory/v3-telemetry-schema (must exist; stop and report if it doesn't).

Note: tests/test_telemetry_v3.py contains enum tripwire tests that pin SCHEMA.md's phase_step and reached_phase_step lists. Your cherry-picks introduce new emitted values, so those tests WILL fail mid-stack — that is by design. Update SCHEMA.md and the tripwire lists together as part of finding (e); do not delete or weaken the tests.

## Steps

1. `git checkout -b factory/planner-integrity factory/v3-telemetry-schema`
2. Cherry-pick in order: `9a52ed2 031a63c b911a38 da4b02f` (test-designer reachable + §7 guard; KI-7 plan gate; KI-8 authored chunk contract; plan-review loop iteration)
3. Fix these verified review findings, each as its own commit with a regression test:

   a. **[P2] Checkpoint restore drops fields.** tools/sprint-loop.py `load_checkpoint` (~lines 224-246) hand-restores a curated field subset while `write_checkpoint` serializes everything via `asdict`. It drops `rs.chunks_file` (a resumed planner loop then renders "(none supplied)" and reintroduces KI-8) and `rs.pilot_spec_file` (test-designer prompt degrades). Root-cause fix preferred: make restore field-driven (iterate dataclass fields, special-case enums/nested types) so any future RunState/ChunkState field round-trips automatically. Add a round-trip test: populate every field, write, load, assert equality.

   b. **[P2] Plan-review loop overwrites prior-round evidence.** Now that the loop truly iterates (da4b02f), round N overwrites round N-1's plan.md, planner-envelope.json, plan-reviewer-N-* files while `plan_sha256_at_time_of_review` still references the destroyed text. Apply the same rule the chunk loop uses (`archive_superseded_test`: "renamed, never deleted"): round-index the plan-loop evidence paths so every round survives. Test: run two review rounds, assert round 1 artifacts still exist and hashes remain verifiable.

   c. **[P2] planner.md false tool-policy claim.** tools/sprint_loop/prompts/planner.md (~lines 72-73) claims "You have no file-writing tool" but `DEFAULT_ENABLED_TOOLS[Role.PLANNER]` includes Execute (tools/sprint_loop/state.py:61) — the original KI-7 vector. Decide and implement ONE: strip Execute from the planner allowlist (check nothing in the planner flow needs it), or reword the prompt to "the runner only reads your final message; anything written to disk is ignored and treated as a KI-7 violation". Prefer stripping Execute if tests stay green.

   d. **[P3] test-designer.md documents an unimplemented parse.** tools/sprint_loop/prompts/test-designer.md (~lines 92-107) promises the runner parses the designer's ACCEPTED_ASSERTION line and passes it as --accepted-assertion; no such parse exists (per_chunk.py ~507 comment describes unwritten code; the pipeline only uses chunk.accepted_assertion, always pre-filled by _chunks_from_file). Either implement the parse (extract from designer result text, thread into lock_test/validate_red, with test) or delete the fallback branch and the stale comment. Prefer implementing it — it closes a real silent-ignore gap.

   e. **SCHEMA.md enum updates for values introduced by these cherry-picks.** `phase_step` gains `test-design-rerun` and `reached_phase_step` gains `test-design` (verify with grep against the emitters). Update SCHEMA.md AND the tripwire test lists in tests/test_telemetry_v3.py together.

4. Validation: `/usr/bin/python3 -m pytest -q` must pass, ignoring ONLY the known environmental failure tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds (duplicated local git history; pre-existing).
5. Commit style: conventional, lowercase, imperative, matching repo history; reference KI-7/KI-8 where relevant.

Constraints: follow AGENTS.md (treat repo as public; technical, sourced, fair). Keep scope strictly to this package.

Final report: branch name, commit list, which option you chose for (c) and (d) and why, test results. When done, report back to the operator; the supervising session reviews the branch before anything is pushed.
