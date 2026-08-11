# Negative Fixture — Innocent Gate-and-Blocker Prose

This plan contains narrative prose about gates, blockers, verification,
and rejection verdicts. It is intentionally free of machine-checkable
claims (no backticked field paths, no backticked call expressions, no
backticked model ids). The linter must produce zero findings on this
text in heuristic mode.

## Revision history

- v1: initial draft. REJECT: the verification step was underspecified.
  The reviewer noted the gate predicate was too vague to implement.
- v2: added gate semantics. REJECT: close-loop had a hard gate with no
  await path, creating a deadlock when the referee was slow to sign.
- v3: this revision. Addresses the deadlock by adding a timeout with
  human-decision fallback. The gate still verifies the token exists
  and the verdict is acceptable before proceeding.

### Sub-heading within revision history

This sub-heading exists to test that the heading discriminator does not
reset the changelog-exclusion state for sub-headings that are still
within the revision-history section. The content here mentions the
gate and verdict but must not produce any findings because it is
inside the excluded section.

## Design rationale

The trust boundary places all cryptographic weight in the referee. The
runner checks structure only: does the token file exist, does the
reviewer panel satisfy the family-distinctness invariant, does the
commit SHA match. Anyone who can write a plausible token to the token
directory can satisfy the runner gate. The operational defense is that
only the referee writes there. This is a deliberate trade-off: the
runner never holds a signing key, so it cannot be coerced into emitting
fraudulent tokens.

The verification flow is: build, commit, post a review request, wait
for the token to appear, then structurally verify it. If the token is
missing or invalid, the runner pauses for a human decision rather than
proceeding. A skip-with-banner path was considered and rejected because
a skip path is a bypass path.

## What this plan does NOT do

Does not add a liveness watchdog. Does not enforce TTLs on review
request lines. Does not add runner-side cryptographic verification.
