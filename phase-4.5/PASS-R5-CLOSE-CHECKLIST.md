# Cross-family pass-r5 close — checklist for the reviewer agent

This file is the operator-side handoff prompt for the cross-family
pass-r5 review agent. It is NOT a worktree-relative script; the
agent opens it on entry to the review.

## Why this file exists

The build session on `factory/phase-5-chunkadherence-enforcement`
emitted `chunk-N.token.json` for chunks **5a..5e** with placeholder
reviewer `envelope_sha256` values (KN-A-5). The cross-family
pass-r5 close is the §17.2-distinct-family agent responsible for:

1. Independently verifying OR refiring each chunk's review.
2. Either re-signing the tokens with real envelopes OR rejecting
   pass-r5 with KN-A-5 named.
3. Recording ACCEPT-WITH-NITS-or-better (or REJECT) and the
   empirical mutation-testing of the gate.

The build agent cannot do this (§17.2 author-not-validator
invariant). This file is the audit-trail handoff so the reviewer can
move on entry without re-deriving the context.

## Pre-check before you start

```sh
# 0. Pick a separate MODEL — your model family MUST differ
#    from the build session's family (openai-family for this build).
#    Recommended pair for the pass-r5 close: grok-4.5 + gemini-3.1-pro-preview.
#    Use `tools/sprint_loop/config.py:MODEL_FAMILY_MAP` to verify family.

# 1. Confirm git topology
git -C /Users/factory/work/adversarial-sprint-phase5 status -b
git -C /Users/factory/work/adversarial-sprint-phase5 log --oneline main..HEAD
# Expect ~15 commits on top of main: 5 chunks (code + token each) +
# the post-launch HEAD bump + KN-A-5 + skill rule #10 + KN-A-7.

# 2. Read the gap files FIRST.
# These came in during the build session and surface the honest gap.
cat phase-4.5/KNOWN-ISSUES.md | grep -A 100 '^### KN-A-5'
cat phase-4.5/KNOWN-ISSUES.md | grep -A 100 '^### KN-A-6'
cat phase-4.5/KNOWN-ISSUES.md | grep -A 100 '^### KN-A-7'

# 3. Read the design-doc (your second source of structural truth).
cat phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md   # the close agent design
cat phase-4.5/DESIGN-DAEMON-SIGNER.md            # not built yet; FYI

# 4. Hydrate the metas in your context (per §18 distill loop).
cat skills/adversarial-sprint/SKILL.md            # rules §1-§21 digest
cat tools/OPERATING-RULES.md                      # full rules §1-§21
cat phase-4.5/RUN-PROMPT.md                       # §15 truth-table

# 5. Verify env vars are set before any droid exec.
test -n "$EVIDENCE_SIGNING_KEY" || { echo 'set EVIDENCE_SIGNING_KEY'; exit 1; }
test -n "$DROID_MODEL_ID" || { echo 'set DROID_MODEL_ID'; exit 1; }
```

If any pre-check fails, do not start; surface to operator.

## Per-chunk re-review checklist

For each `chunk-N.token.json` in `phase-4.5/tokens/`:

```sh
chunks=(5a 5b 5c 5d 5e)
for c in "${chunks[@]}"; do
  python3 - <<PY
import json, hmac, hashlib, os, sys
import sys; sys.path.insert(0, "/Users/factory/work/adversarial-sprint-phase5/tools")
import sign_chunk_token as sct

with open("/Users/factory/work/adversarial-sprint-phase5/phase-4.5/tokens/chunk-$c.token.json") as f:
    token = json.load(f)

# 1. HMAC verifies under EVIDENCE_SIGNING_KEY?
print(f"chunk-$c HMAC verify: {sct.verify_token(token)}")

# 2. Family constraints pass?
for r in token["reviewers"]:
    print(f"  reviewer family={r['family']} model={r['model_id']} verdict={r['verdict']}")

# 3. KN-A-5 placeholder check on envelope_sha256?
for r in token["reviewers"]:
    sha = r["envelope_sha256"]
    is_placeholder = (
        len(sha) != 64
        or not all(ch in "0123456789abcdef" for ch in sha)
        or len(set(sha[:50])) == 1
    )
    print(f"  reviewer envelope placeholder? {is_placeholder}")
PY
done
```

### Decision per chunk

For each `chunk-N`:

| Hmac verifies | Family constraints | Envelope placeholder | Action |
|---|---|---|---|
| false | (any) | (any) | REJECT pass-r5 with chunk-N named |
| true | fail | (any) | REJECT pass-r5 with family-collision named |
| true | pass | yes | **Re-fire the chunk's review** (see Re-fire procedure below) |
| true | pass | no  | ACCEPT for this chunk (continue to next chunk) |

A single chunk refusing rejects pass-r5 entirely; partial close
is not a thing.

## Re-fire procedure (KN-A-5 fix recipe (2a))

For each chunk whose envelope_sha256 is a placeholder:

```sh
# 1. Spawn cross-family droid exec against the chunk's diff.
#    Use the per-pilot overlay's `--unattended` for the daemon-style
#    emit; --dry-run first to verify wiring.

# 2. Capture each fired reviewer's output envelope to a canonical
#    path:
mkdir -p phase-4.5/build-evidence/$RUN_ID/$CHUNK_ID
DROID_MODEL_ID=grok-4.5 bash tools/run-with-model.sh \
    droid exec --model "$DROID_MODEL_ID" \
        -f /tmp/review-prompt.md --auto high --cwd /Users/factory/work/adversarial-sprint-phase5 \
        --envelope-out phase-4.5/build-evidence/$RUN_ID/$CHUNK_ID/grok-4.5.json
# (the --envelope-out flag is the §5 ergonomic add from
# DESIGN-DAEMON-SIGNER.md §5; not yet built in this branch.)

# 3. Compute the real envelope SHA:
sha256sum phase-4.5/build-evidence/$RUN_ID/$CHUNK_ID/grok-4.5.json

# 4. Re-emit chunk-N.token.json with the real SHA, via either:
#    a. the existing tools/sign_chunk_token.py sign subcommand
#       (still in-process; acceptable for close agent because the
#       close agent's job is to record real envelopes on disk,
#       not to defend against itself);
#    b. the future Tier-3 daemon (DESIGN-DAEMON-SIGNER.md).

# 5. Commit the new chunk-N.token.json with the chunk's commit SHA
#    OR a fresh chunk-5-{N}-retrofit commit if back-dating is the
#    closer fit for the cohort. Either way, the new commit must
#    contain: the new token.json + the on-disk envelopes under
#    phase-4.5/build-evidence/...
```

## Empirical mutation testing (§7 + design-doc §7 predicate 7)

The close agent must mutate-test the gate. Recommended mutations:

1. **Tamper the chunk-N token's `signature.value` by one char**,
   verify `chunk_sequence_gate.py` refuses. Exit 6.
2. **Replace a reviewer family with the implementer family**, verify
   refusal.
3. **Replace an envelope_sha256 with a placeholder marker** (the
   same `"5"*60 + "01"` pattern as KN-A-5), verify
   `cross_family_review.py` refuses. (Yes — this mutation RE-runs
   the producer, not the consumer; that's the design intent.)
4. **Drop the prior-token file**, verify `chunk_sequence_gate.py`
   exit 6.
5. **Mismatch `chunk_commit_sha` vs `git rev-parse HEAD`** with
   `--check-current-head`, verify ref exit 6.
6. **Re-emit a banner with the tampered token**, verify ⛔ +
   checklist pointer on stderr.

Pin each mutation as a behavioral test in a follow-up
`tests/test_pass_r5_mutations.py` (the close agent writes this
test file as part of the close).

## Operator-eye signal at close

After ACCEPT-WITH-NITS-or-better for every chunk:

```sh
# Emit the four-tone visual signature per chunk.
for c in 5a 5b 5c 5d 5e; do
  PYTHONPATH=tools:sprint_loop python3 tools/sprint_loop/chunk_close_banner.py \
    --token-path phase-4.5/tokens/chunk-$c.token.json \
    --plan-review-rendered --validation-gate-executed
done
```

Every line must show `🤺 👀 ✅`. If any line shows `⛔`, the
chunk-N's close is not yet demonstrated; re-fire or reject.

## Recorder

When pass-r5 closes, the operator (you) records

- PASS-r5 panel: which two model families (`grok-family` and
  `gemini-family` per PRD §11 Phase 5 exit criteria).
- Mutation test results: 6 tests, all pin pass.
- File-level commit: chunk-{N} retrofit commits on top of
  `f89b9c6` (or whichever commit is HEAD at session entry).
- Final branch tip after retrofit commits.
- Push (operator-side; agents don't push).

Done = branch is ready for merge-to-main per AGENTS.md
invariant #8.

## Reference commands (one-liners)

```sh
# Verify all 47 build-side tests still pass before doing anything.
PYTHONPATH=tools:test python3 -m pytest \
  tests/test_sign_chunk_token.py \
  tests/test_cross_family_review.py \
  tests/test_chunk_sequence_gate.py \
  tests/test_chunk_close_banner.py \
  tests/test_install_skill_phase5.py \
  --tb=no -q
# Expected: 47 passed.

# Verify each chunk-N token's signature is well-formed.
for c in 5a 5b 5c 5d 5e; do
  PYTHONPATH=tools python3 tools/sign_chunk_token.py verify \
      --token-path phase-4.5/tokens/chunk-$c.token.json
  echo "chunk-$c exit=$?"
done
```
