# Task: a design-review phase, and a referee seat that is a boundary

**Status:** proposed, not started. **Origin:** `phase-5/POSTMORTEM-REFEREE-SEAT.md`
(findings F-REF-001 … F-REF-007), run `r-drs-role-split-1`.

**Seat disclosure:** this task was drafted by `claude-opus-5`, the same family as
the author of `DESIGN-ROLE-SPLIT-AND-SIGNALS.md`. It is a proposal, not a plan of
record, until a non-Claude seat reviews it (§17.2). Treating it as approved
because it is written down would be the same class of error it exists to fix.

---

## 1. The gap

The framework can review a code change against a locked test in a pilot repo.
That is the only artifact shape it has a designed path for. `tools/orchestrate-review.py`
hard-requires `--pilot-root --pilot-python --test-file --lock-file`:

```
orchestrate-review.py: error: the following arguments are required:
  --pilot-root, --pilot-python, --test-file, --lock-file
```

Phase 5 is almost entirely design documents. Every design review so far has been
run by hand or by a one-off script, which means each one re-litigates its own
scaffolding, and none of them produce telemetry the project can compare across
rounds. §9 says if it is not scripted it did not happen; §10 says telemetry rows
are written by the script. Design reviews currently satisfy neither.

The second gap is **not** that the referee seat is unbuilt. It is built:
worktree `/Users/factory/work/adversarial-sprint-referee`, branch
`agent/referee/phase-5-chunkadherence`, identity
`Persistent Referee <referee@phase-5.local>`, five chunk-close tokens signed under
that identity at `c0ba01c`. The gap is that **entering it is opt-in and
unverified**. On `r-drs-role-split-1` an agent told "you are the ref" did referee
work from the builder's worktree, on the builder's branch, under the builder's
identity, and fired reviewers from there. Nothing compared where it was against
where the referee lives.

The third gap is that attested envelopes are written where they cannot travel:
the design specifies `phase-4.5/build-evidence/<run-id>/envelopes/`, and
`.gitignore:41` ignores `phase-*/build-evidence/`. A token's `envelope_sha256` is
therefore unverifiable from any other machine (§1, §21). The referee branch
already tracks its envelopes at the repo root instead, so two conventions are
live.

## 2. Capacity bound (§17)

**Three deliverables. Nothing else in this task.** Explicitly refused: a general
artifact-review framework, a plugin system for artifact types, a redesign of
`orchestrate-review.py`, and any change to the chunk-token schema. Those are the
unbounded-foundation shape §17 exists to stop.

| # | Deliverable | Closes |
|---|---|---|
| D1 | `--artifact-review` mode: a designed path for reviewing a non-code artifact, pinned by commit sha | F-REF-004, F-REF-007 |
| D2 | Referee **entry check** (seat occupancy verified, not intended) + productive refusal as opening move + one tracked envelope path | F-REF-001, F-REF-003, F-REF-008 |
| D3 | Fix the invocation defects that burned two seats | F-REF-005 |

Out of scope for this task but owed to the author of the design doc as review
feedback, not built here: F-REF-002 (Change A is necessary-not-sufficient) and
F-REF-006 (the convergence classifier needs a null-round state). Those are edits
to a design document by its author. A referee proposing prose for the artifact it
reviews is the leak in the other direction.

## 3. Compose, don't write (§18.1)

Existing primitives this must be built *from*, verified present:

| Primitive | Role in D1 |
|---|---|
| `tools/run-with-model.sh` | model pinning, `--mission` refusal (§14) |
| `tools/adapters/factory.py` | envelope parsing seam — do not hand-parse (§14) |
| `phase-5/scripts/envelope-manifest.py` | verdict-presence guard, `admissible_as_attestation` |
| `tools/render-blind-prompt.py` | existing spec+diff-only rendering pattern to follow for artifact pinning |
| `tools/sprint_loop/config.py:MODEL_FAMILY_MAP` | family distinctness (§17.2) |
| `tools/cross_family_review.py` | family/verdict gate at parse |

`phase-5/scripts/fire-design-review.sh` is **acknowledged debt**, not a
primitive. D1 subsumes it; the chunk that lands D1 deletes it. Leaving both is
the §18.4 failure that created it.

## 4. Chunk plan (§18.2 — committed before the chunks fire)

### Chunk A — pin the artifact

Render a review target that is fixed bytes rather than a branch name: resolve the
artifact at an explicit commit sha, emit the artifact text plus its diff against
the merge-base into a run directory, and record the sha in the run manifest.

- **Verify:** two invocations at the same sha produce byte-identical prompt
  inputs (`sha256` equal); an invocation at a dirty tree refuses.

### Chunk B — `--artifact-review` mode

Add the mode to the designed harness so `--test-file` / `--lock-file` /
`--pilot-python` are not required when reviewing an artifact, and the pipeline
runs: pin (Chunk A) → fire operator-selected seats via `run-with-model.sh` →
capture raw envelopes → parse through `adapters/factory.py` → run the
`envelope-manifest.py` guard → write `runs.jsonl` + `findings.jsonl` (§10).

- **Verify:** `--artifact-review` with no code-review flags exits 0 on a
  dry-run; the run refuses to report success when any envelope lacks a verdict
  (assert by feeding the `r-drs-role-split-1` envelopes as a fixture — a burned
  run is now a regression test); `findings.jsonl` parses and carries one row per
  emitted finding.

### Chunk C — referee entry check, not a new boundary

The infrastructure exists; occupying it must become a precondition. A referee
preflight that refuses to proceed unless it is actually in the seat:

- refuse unless `cwd` resolves to the referee worktree, the branch matches
  `agent/referee/*`, and `git config user.email` matches the referee identity —
  the check that would have stopped `r-drs-role-split-1` at tool call one;
- refuse if `EVIDENCE_SIGNING_KEY` is readable while the process is also about to
  fire, and vice versa (§24 fire-XOR-sign, enforced rather than coincidental);
- on `no envelopes on disk`, emit the **productive refusal**: a
  `REFUSED: chunk=X reason=no-envelopes` line plus a precondition checklist
  artifact naming each missing input, so the referee's opening move produces a
  file instead of a vacuum (F-REF-003);
- settle the envelope path on one **tracked** location so a token's
  `envelope_sha256` is recomputable on another machine (F-REF-008), and update
  `DESIGN-PERSISTENT-REFEREE.md` §4.3/§4.4/§5.2 to match whichever wins.

- **Verify:** invoked from the builder worktree, preflight exits non-zero and
  fires nothing — proven by asserting zero new files under the run dir, not by
  reading the exit code (§7); invoked from the referee worktree with no
  envelopes, the refusal artifact exists and names every missing precondition;
  `git check-ignore` reports the chosen envelope path is **not** ignored.

### Chunk D — invocation fixes

`--auto medium` plus `git worktree` isolation so elevated autonomy cannot reach
the artifact under review; resolve the `stream-json` vs `json` contradiction in
one direction and update whichever docs then disagree.

- **Verify:** a cheap-model smoke call (`gpt-5.4-mini`, trivial prompt) produces
  an envelope that `adapters/factory.py` parses without exception — the check
  that would have caught F-REF-005 before two frontier calls; `git diff --stat`
  in the primary worktree is empty after a reviewer runs at `--auto medium`.

## 5. Acceptance criteria (§11 — mechanically checkable)

- [ ] Reviewing `phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md` runs end to end
      through the designed harness with no hand-written script, and no
      placeholder `--test-file` / `--lock-file` anywhere in the command
- [ ] `phase-5/scripts/fire-design-review.sh` is deleted in the same chunk that
      lands D1
- [ ] The prompt names the artifact by commit sha; two runs at that sha hash
      identically
- [ ] Every reviewer envelope is parsed by `adapters/factory.py`; no inline
      `json.loads` of envelope bytes anywhere in the new code
- [ ] A verdict-less run cannot be reported as a review: the
      `r-drs-role-split-1` envelopes are a committed fixture and the pipeline
      fails on them
- [ ] Referee preflight refuses when run outside the referee worktree/branch/
      identity, and when a signing key is present in a firing process; both
      refusals proven by absence of fired envelopes rather than by exit code
- [ ] `no envelopes` produces a refusal artifact, not silence
- [ ] `git check-ignore` confirms the attested envelope path is tracked, and the
      design doc's example paths match it
- [ ] `runs.jsonl` gains one row per artifact-review invocation, written by the
      script (§10)
- [ ] A reviewer at `--auto medium` provably cannot modify the artifact under
      review
- [ ] This task document has a non-Claude review verdict on record before any
      chunk lands

## 6. Sequencing note

Chunk D is the cheapest and unblocks re-firing the review that started this, so
it goes first if the operator wants the design review completed before the
tooling is built. Chunk C should land before any chunk-close token is signed by
a referee process, since until it exists the §22/§24 separation remains what it
was on `r-drs-role-split-1`: contingent on an environment variable happening to
be unset, and on the agent happening to run `git worktree list`.

Its cheapest half — the cwd/branch/identity check — is worth landing on its own
even if the rest of the task is deferred. It is a few lines of preflight, and it
is the single check that would have prevented every downstream error in this
session.

## 7. Explicit non-goal

This task does not claim to make the framework catch the class of error that
motivated it. Both the design doc's `n=1` and this session's `n=2` were caught by
the operator asking a skeptical question. D1–D3 remove the *specific* holes that
were walked through; they do not establish that an agent in the referee seat
would have stopped itself. Claiming otherwise would repeat §16 — binding a demo
claim to a capability nobody verified.
