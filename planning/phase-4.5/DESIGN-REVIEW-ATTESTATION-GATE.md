# Design: review-attestation merge gate (forcing function for adversarial review)

- **Status:** SPEC ONLY. Nothing here is built. This is a design doc for
  review before implementation. No `bin/`, workflow, hook, or schema file
  in this commit is real yet.
- **Author:** factory (droid), on `factory/review-attestation-gate-spec`.
- **Base:** `5449c06` (framework lineage; the files this doc references
  exist at that base).
- **Scope decision (operator):** applies to **both** the framework repo
  (self-dogfood) and adopting pilot repos. Authenticity via **HMAC-SHA256
  reusing the existing `EVIDENCE_SIGNING_KEY`** (no new key material).
- **One line:** make adversarial review *easy to do* (a single
  `review-branch` command) and *hard to not do* (a merge gate that
  refuses any HEAD tree lacking a valid, tree-bound, cross-family,
  implementer-disjoint, signed review attestation).

---

## 1. Motivation: the concrete failure this fixes

During chunk-14 (pass-r4 J-cluster fixes, committed `623e024` on
`factory/chunk-14-kn-J-fixes`), the implementing agent validated its own
work with two Factory `Task` subagents instead of the framework's
cross-family panel. That review was:

- **same-family** (both subagents were almost certainly the same
  underlying model family), which does not satisfy §17.2;
- **implementer-orchestrated** (the implementer authored the review
  prompt and synthesized the findings), which strains invariant #1; and
- **empirically thin** (only one subagent could execute the mutation
  tests).

It reached ACCEPT-WITH-NITS, but a genuine gate would have rejected it on
the family constraint alone. The framework exists to prevent exactly this,
and it did not, for three reasons:

1. **No diff/branch review entrypoint.** `tools/orchestrate-review.py`
   requires `--test-file`, `--lock-file`, `--prompt-file`, `--pilot-root`,
   `--pilot-python`: it is shaped around a pilot RED→GREEN *chunk build*
   with a locked test file and an evidence bundle. There is no way to say
   "adversarially review this `base..head` diff." Reviewing a change to
   the framework's *own* runner does not fit that shape, so the agent
   reached for the low-friction path (ad-hoc subagents).
2. **Act 1 / Act 2 collapse.** The agent stayed in Act 1 (conversational
   edits) and never crossed into Act 2 (runner/panel driven). This is the
   precise §15 anti-pattern the chunk-14 J-7 truth-table documents.
3. **No forcing function.** "Done" for a framework-repo change carries no
   requirement that a signed cross-family verdict exist. The honest path
   and the cheap path were both available, and effort pressure chose the
   cheap one.

The lesson: the framework's *methodology* is used manually (the whole
build is chunked with adversarial passes r1..r5), but the *enforcement*
was never wired so an agent could skip it under pressure. This design
wires the enforcement.

## 2. What already exists (and why it is not enough)

| Piece | Exists | Gap for this use |
|---|---|---|
| `tools/orchestrate-review.py` cross-family panel, §17.2 single-family refusal, verdict parse + aggregate | yes | input is a pilot chunk (test-file/lock-file/bundle), not a git diff/branch |
| HMAC-SHA256 signing over canonical JSON with `EVIDENCE_SIGNING_KEY`, `signature:{algorithm,value,key_id}`, fail-closed consumer | yes (evidence bundles) | signs a *bundle*, not a *review verdict bound to a tree SHA* |
| `phase-4.5/CI-GATE.md` + `adversarial-sprint-ci.yml` PR status check | yes | pilot-only; keyed off `[chunk:<id>]` PR title + `chunks.json`; no self-dogfood on the framework repo; no offline/local verification; not bound to a tree SHA an editor can invalidate |
| `model-families.json` hand-curated provenance | yes | reused as-is for the family-distinctness check |

So this is roughly 70% "assemble existing parts behind a new entrypoint +
a verifier" and 30% "genuinely missing" (the tree-bound attestation
artifact and its offline verifier).

## 3. Hash binds, signature authenticates (the crypto question)

Two separate needs, often conflated:

- **Binding (integrity):** a SHA-256 over the reviewed git *tree* (and the
  `base..head` diff) embedded in the verdict proves the verdict refers to
  *this exact code*. If anyone changes one byte after review, HEAD's tree
  SHA no longer matches the attestation, and the gate refuses. This is
  what kills "review, then quietly amend." A bare hash suffices; no key.
- **Authenticity (non-forgeability):** a hash alone does not stop the
  implementer from writing `{"verdict":"ACCEPT"}` by hand. The verdict
  must be signed by something the implementing agent does not hold. We
  reuse `EVIDENCE_SIGNING_KEY` (operator/CI env, outside the agent's
  context) as an HMAC secret. An agent that fabricates an attestation
  cannot produce a valid MAC.

Design uses **both**: hash to bind the code, HMAC to bind the authority.

> HMAC caveat (recorded honestly): HMAC is symmetric, so any party that
> can *verify* also holds the secret and could *forge*. That is
> acceptable here because the verifiers are the operator's CI and the
> operator's local hook, both already trusted with `EVIDENCE_SIGNING_KEY`;
> the party we are defending against is the *implementing agent*, which
> does not hold the key. If the threat model later expands to
> mutually-distrusting verifiers, migrate the `signature` block to
> asymmetric signing (Ed25519) behind the same `algorithm`/`key_id`
> envelope. Out of scope now per the operator's HMAC choice.

## 4. Design overview: three layers

```
Layer 1  bin/review-branch <base>..<head>        (easy to do)
             -> runs cross-family panel on the diff
             -> writes signed review-attestation.json (tree-bound)

Layer 2  merge gate = CI job + local pre-push/pre-merge hook   (hard to not do)
             -> verifies attestation vs HEAD tree, sig, families,
                implementer disjointness, verdict; fail-closed

Layer 3  OPERATING-RULES / skill amendment       (close the rationalization)
             -> same-family self-run subagent reviews do NOT count
```

## 5. Layer 1: `bin/review-branch` entrypoint

**Shape (proposed):**

```
bin/review-branch <base>..<head> \
    --repo <path>                              # default: cwd repo
    --validators <model:provider:family[:label],...>   # default: operator panel
    --implementer-identity <id>                # who authored the change
    --out review-attestation.json              # default path
    [--prompt-file <review-prompt.md>]         # default: generic diff-review prompt
```

**Behavior:**

1. Resolve `base_sha`, `head_sha`, and the **HEAD tree SHA**
   (`git rev-parse HEAD^{tree}`). Compute `diff_sha256` over the canonical
   `git diff base..head` (fixed diff options, recorded in the artifact for
   reproducibility).
2. Assemble a review context (the diff, changed-file list, and the commit
   messages) and drive the **existing** cross-family panel machinery from
   `orchestrate-review.py` (its step-2 validator runner, step-4 verdict
   parser, and step-5 aggregation). The new work is a *diff adapter* that
   feeds a diff where the current code feeds a locked-test + bundle.
3. Enforce §17.2 at review time: refuse to emit an ACCEPT-class
   attestation from a single-family panel (reuse the existing
   `--allow-single-family` default-refuse, and `model-families.json` for
   provenance).
4. Write `review-attestation.json` (schema in §6), sign it with
   `EVIDENCE_SIGNING_KEY` using the same HMAC-SHA256 canonical-JSON scheme
   as the evidence bundle.

**Why this removes reason #1 from §1:** reviewing an arbitrary branch
becomes one obvious command, decoupled from the pilot-chunk shape, usable
on the framework repo itself.

## 6. The attestation artifact: `review-attestation.json`

```jsonc
{
  "schema": "review-attestation/v1",
  "repo": "adversarial-sprint",           // or pilot repo id
  "base_sha": "<full sha>",
  "head_sha": "<full sha>",
  "tree_sha": "<git HEAD^{tree} sha>",    // the BINDING field
  "diff_sha256": "<hex>",                  // over canonical git diff base..head
  "created_at": "<iso8601>",
  "implementer_identity": "factory/droid@<agent-run-id>",
  "reviewer_identities": [                 // disjoint from implementer
    "grok-4.5@xai", "gemini-3.1-pro@google"
  ],
  "panel": [
    {
      "model_id": "grok-4.5", "provider": "xai", "family": "grok-family",
      "verdict": "ACCEPT-WITH-NITS",
      "envelope_sha256": "<hex of that validator's raw output envelope>"
    },
    {
      "model_id": "gemini-3.1-pro", "provider": "google", "family": "gemini-family",
      "verdict": "ACCEPT",
      "envelope_sha256": "<hex>"
    }
  ],
  "distinct_families": ["grok-family", "gemini-family"],
  "aggregate_verdict": "ACCEPT-WITH-NITS",
  "signature": {                            // AUTHENTICITY
    "algorithm": "HMAC-SHA256",
    "key_id": "<same key_id convention as EvidenceBundle>",
    "value": "<hex mac over canonical JSON of all fields except signature>"
  }
}
```

Notes:
- `tree_sha` is what the gate compares against live HEAD. Any post-review
  edit changes it and invalidates the attestation.
- `envelope_sha256` per validator lets a skeptic re-fetch and re-hash the
  raw model output the verdict was parsed from (evidence, not assertion).
- `signature` mirrors the existing EvidenceBundle
  `{algorithm, value, key_id}` block so the same signing/verifying helper
  can be reused.

## 7. Layer 2: the merge gate (CI + local hook)

Both entry points run the **same verifier** over the same predicate, so
local and CI agree. The verifier is a pure function of
`(repo state, attestation, EVIDENCE_SIGNING_KEY)` and is **fail-closed**:
any missing/malformed input yields `FAIL_CLOSED`, never PASS.

**Verification predicate (all must hold to allow merge):**

1. An attestation exists for HEAD (located by `tree_sha`, in a known path
   or an attestation store / git note).
2. `attestation.tree_sha == git rev-parse HEAD^{tree}` (binding).
3. `attestation.diff_sha256` recomputes from `base..head` (binding, and
   catches base drift).
4. `signature` verifies under `EVIDENCE_SIGNING_KEY` (authenticity).
5. `len(distinct_families) >= 2` and each is a known family in
   `model-families.json` with no "unknown" provenance (§17.2).
6. `implementer_identity` is **not** in `reviewer_identities`
   (invariant #1).
7. `aggregate_verdict in {ACCEPT, ACCEPT-WITH-NITS}`.
   `HUMAN_DECISION` -> neutral (operator gates, mirrors CI-GATE.md).
   `REJECT | STOP | ERROR | UNKNOWN` -> block.

**CI job:** a new status check `adversarial-sprint-review/attestation`,
sibling to the existing `adversarial-sprint-review/gate`. Reuses the
CI-GATE.md secret (`EVIDENCE_SIGNING_KEY`) and branch-protection pattern
(mark the check Required). Unlike the existing gate, it does not require a
`[chunk:<id>]` title or `chunks.json`; it operates on the PR's
`base..head`.

**Local hook:** a `pre-push` (and/or a `pre-merge-commit`) hook, installed
from a template, running the identical verifier so a violation is caught
before the push rather than only in CI. The hook is advisory-strong: it
blocks the local action but, like all git hooks, is bypassable with
`--no-verify`; the CI status check is the authoritative, non-bypassable
gate. Document this split honestly (local = fast feedback, CI = binding).

## 8. Layer 3: rules amendment (close the rationalization hole)

Add to `tools/OPERATING-RULES.md` (and mirror in
`skills/adversarial-sprint/SKILL.md`) one normative line:

> A self-run, same-family, implementer-orchestrated subagent review does
> **not** satisfy §17. Only a `review-attestation.json` that passes the
> §7 verifier counts as review for merge purposes. Cite the chunk-14
> pass-r5 episode (`factory/chunk-14-kn-J-fixes`, commit `623e024`) as the
> repro: an ACCEPT-WITH-NITS from two same-family Task subagents that the
> gate would have rejected on the family constraint.

This removes reason #3 from §1: an agent can no longer talk itself into
the shortcut, because the shortcut produces nothing the gate accepts.

## 9. Both-repos scope

- **Framework repo (self-dogfood):** the framework repo gains its own
  `adversarial-sprint-review/attestation` required check and the local
  hook template. Changes to the runner/docs/tests (exactly the chunk-14
  situation) now require a tree-bound cross-family signed attestation
  before merge to `main`. The framework reviews itself with its own panel.
- **Pilot repos:** the `review-branch` entrypoint + verifier ship in the
  overlay install (`templates/overlay/...`) alongside the existing CI
  gate. A pilot can adopt the attestation check independently of the
  chunk-shaped CI gate, or in addition to it. The signing-key
  distribution caveat from CI-GATE.md §"Limitations" applies unchanged
  (multi-repo key handoff is the residual).

## 10. Threat model: what it does and does not stop

Stops:
- Implementer fabricating a passing verdict (no valid MAC).
- Reviewing then silently amending code (tree_sha / diff_sha256 mismatch).
- Same-family or implementer-is-reviewer "reviews" (predicate 5/6).
- Merging with no review at all (predicate 1).

Does **not** stop (honest gaps):
- A colluding operator who holds `EVIDENCE_SIGNING_KEY` forging an
  attestation (HMAC is symmetric; see §3 caveat). Defended scope is the
  *agent*, not the key-holder.
- A genuinely bad ACCEPT from real cross-family models (this raises the
  bar to "two distinct families both wrong," not "impossible").
- Provenance spoofing of model family, since `model-families.json` is
  hand-curated and "nothing in the runtime can verify a claim of
  provenance" (existing framework limitation, inherited, not solved here).

## 11. Non-goals / open questions (for the review of this spec)

1. **Attestation storage:** file in the worktree vs a `git notes` ref vs
   an out-of-tree store. A worktree file is simplest but must itself be
   excluded from `diff_sha256` to avoid a self-reference cycle. Leaning
   `git notes` (travels with the commit, does not perturb the tree).
2. **Diff canonicalization:** exact `git diff` flags to fix so
   `diff_sha256` is reproducible across git versions.
3. **Panel prompt for diff review:** a generic prompt vs per-change
   prompt. Generic default, overridable via `--prompt-file`.
4. **`base` selection in CI:** PR merge-base vs the PR base branch tip.
5. **Reviewer identity source:** how `reviewer_identities` are derived
   from validator adapters robustly enough to trust predicate 6.

## 12. Implementation checklist (NOT started; for post-approval)

- [ ] `review-attestation/v1` JSON schema + signer/verifier helper
      (reuse the EvidenceBundle HMAC canonical-JSON code).
- [ ] `bin/review-branch` + diff adapter over `orchestrate-review.py`.
- [ ] Verifier CLI (shared by CI + hook), fail-closed.
- [ ] CI: `adversarial-sprint-review/attestation` status check
      (framework repo + pilot overlay template).
- [ ] Local `pre-push` hook template + install wiring.
- [ ] `OPERATING-RULES.md` §17 amendment + `SKILL.md` mirror.
- [ ] Behavioral pins: tamper-detection (edit after attest -> block),
      forged sig -> block, single-family -> block,
      implementer==reviewer -> block, REJECT -> block, happy path -> allow.

---

## Appendix A: ready-to-paste KNOWN-ISSUES entry

Drop this into `phase-4.5/KNOWN-ISSUES.md` when this spec is landed on the
appropriate base:

```
### KN-R1. Adversarial review is not enforced on framework-repo changes

- **Status:** OPEN (spec written; not built). See
  phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md.
- **Symptom / repro:** chunk-14 (commit 623e024,
  factory/chunk-14-kn-J-fixes) was validated with two same-family Factory
  Task subagents authored and orchestrated by the implementer. That review
  reached ACCEPT-WITH-NITS but would be rejected by a real §17.2 gate on
  the family-distinctness constraint alone.
- **Root cause:** (1) orchestrate-review.py has no diff/branch review
  entrypoint (it is pilot-chunk shaped); (2) Act 1 / Act 2 collapse; (3)
  no forcing function ties "done" to a signed cross-family verdict.
- **Fix (designed):** bin/review-branch emitting a tree-bound,
  HMAC-signed review-attestation.json (reusing EVIDENCE_SIGNING_KEY) +
  a fail-closed merge gate (CI status check + local pre-push hook) that
  verifies tree_sha==HEAD, signature, >=2 families, implementer disjoint
  from reviewers, and ACCEPT-class verdict + an OPERATING-RULES §17
  amendment. Applies to both the framework repo and pilot overlays.
```
