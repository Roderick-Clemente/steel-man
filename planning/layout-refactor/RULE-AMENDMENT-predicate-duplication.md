# OPERATING-RULES amendment: duplicated predicates

**Status:** DRAFT for referee ruling
**Raised by:** planner seat, chunk-D1-1-spec
**Authorized by:** operator Ruling 4 item 2
**Proposed section:** §4.3 (new), amending §4.2

---

## Proposed rule

> **§4.3 No duplicated predicates.**
>
> Where a spec's prose and an executable check express the same rule,
> the prose copy MUST be deleted and replaced by a citation of the
> check. Spec prose states **intent** — what the check is for, why it
> exists, what would be wrong if it were absent. The check states the
> **predicate** — the exact condition. A spec MUST NOT restate a
> predicate that a locked test already encodes.
>
> A reviewer asked to audit a duplicated predicate MUST report it as a
> finding against the spec, not choose between the two copies.
>
> Where a spec cites a locked check, the citation MUST include the
> check's content hash, so a reviewer can tell whether the cited bytes
> are the bytes under review.

## Why

The rule generalizes a failure this framework produced four rounds in a
row on a single artifact, at real reviewer cost.

**Mechanism.** A duplicated predicate is a second implementation with
no tests. The prose copy cannot be executed, so nothing detects when it
drifts from the real check. Worse, the prose copy is what reviewers
actually read: it is earlier in the document, written in their
language, and presented as authoritative. Review effort therefore
concentrates on the copy that cannot fail, while the copy that gates
goes unexamined.

**Observed, chunk-D1-1-spec rounds 3-6:**

1. **Rounds 3-4** — the spec's §4.2 stated a residual-literal rule as
   prose. Because the rule was scoped to whole files, and because the
   spec itself contained example fences naming those files, the prose
   predicate contradicted itself. Two rounds of findings were spent on
   the wording of a check that did not exist yet. Resolved only by
   making the rule AST-scoped, which is to say: by making it code.

2. **Rounds 5-6** — with the check now executable and locked, both
   reviewer families independently found a blocker **inside the test**:
   its residual matcher compared slash-joined prefixes, so
   `os.path.join(root, "phase-1", "scripts")` — whose AST holds
   `"phase-1"` and `"scripts"` as separate constants — matched nothing.
   Seven of thirteen inventory sites were invisible. Simultaneously the
   spec's prose described a `phase-\d` regex the test did **not**
   implement.

The second round is the argument. The prose was wrong *and* the code
was wrong, in **different** ways, and each concealed the other: a
reviewer checking prose against intent saw a plausible rule, and a
reviewer checking the spec's self-consistency saw two statements that
looked equivalent. The defect was reachable only by executing the
check. Four rounds of prose review had not found it; the first round
where the predicate existed in exactly one place, as code, found it
twice.

## Cost, stated plainly

Six REJECT verdicts on one artifact. Zero of the six identified a
defect in the change chunk-D1-1 actually makes — that change is a
value-preserving no-op by construction. All six were in the
verification apparatus, and rounds 3-6 specifically were in the
relationship between two copies of one predicate.

## Interaction with existing rules

- **§4.2 (verify block must be executable).** This amendment sharpens
  it: executable *and singly-stated*. §4.2 currently permits a spec to
  describe a check it also ships, which is what went wrong.
- **§7 (locked tests).** Unchanged. The lock is what makes citation
  safe: cited bytes cannot move under the citation without a re-lock.
  The hash requirement above closes the remaining gap, since a lock
  prevents silent edits but not legitimate re-locks.
- **§21 (ledger).** Reinforced. Review history, verdicts, and
  corrections belong in the ledger. A spec that narrates its own review
  history is duplicating the ledger — the same defect in a different
  register, and a seat recording verdicts into an artifact under its own
  review also implicates §22.

## Scope note

This is not a rule against explanation. Intent, rationale, worked
examples, and the consequences of absence all belong in the spec and
cannot be recovered from reading a test. The rule targets only
restatement of the **condition** — the thing a machine decides.

## Requested ruling

1. Adopt as §4.3, or reject with reasons.
2. If adopted, confirm whether it applies retroactively to
   CHUNK-2/3/4-SPEC, which were drafted before it and have not been
   reviewed. The planner's recommendation: apply at each chunk's spec
   gate rather than as a bulk rewrite now, so the amendment is tested
   once per artifact at the moment that artifact is under review.
