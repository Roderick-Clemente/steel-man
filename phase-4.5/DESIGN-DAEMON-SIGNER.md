# Design: off-process chunk-token signer (forcing function for envelope evidence)

- **Status:** SPEC ONLY. Nothing here is built. Design doc for review
  before implementation; the per-pilot consensus decides whether to
  ship a daemon in a follow-on chunk.
- **Author:** factory (droid), on
  `factory/phase-5-chunkadherence-enforcement` (this branch).
- **Scope decision (operator):** addresses **both** the framework
  repo (self-dogfood) and adopting pilot repos. The daemon runs
  *alongside* the framework, never inside the agent process.

---

## 0. One-line summary

Make `EVIDENCE_SIGNING_KEY` *unholdable* by the chunk-emitting agent:
introduce a thin off-process signer the agent POSTs to over a Unix
socket. The signer holds the key, requires each reviewer's
`envelope_path` to exist on disk + SHA-match its declared
`envelope_sha256`, and emits the signed `chunk-N.token.json`. The
agent never has the key material enough to fabricate a verifying
HMAC over a fabricated payload.

---

## 1. The concrete failure this fixes

Two phases have shipped the same anti-pattern in slightly different
shapes:

- **chunk-14 (commit `623e024`, `factory/chunk-14-kn-J-fixes`):**
  review was performed by two same-family Factory `Task` subagents
  authored and orchestrated by the implementer. Reached
  ACCEPT-WITH-NITS but violated §17.2 family-distinctness.

- **Phase 5 (this branch, commits `f89275f` / `663ee4c` / `76eb3ab` /
  `59442ab` / `dda84d1`):** every chunk-N token was emitted with
  typed-in fixture `envelope_sha256` values of the form
  `"5555…55501"`. Per KN-A-5 this was caught at the gate (commit
  `56ee55a` tightened `cross_family_review.py`), but the gate
  *catches future emissions* — the existing tokens on this branch
  remain fabricated until cross-family pass-r5 close re-fires real
  reviewers.

The Phase-5 build could not enforcer the gate against itself
because **the agent producing a chunk's token was the same entity
producing the chunk's reviewer's envelope**. Signing authority was
held by an environment variable the agent read directly. Any
defense inside the agent's process boundary can be circumvented
by effort pressure.

This design moves signing authority OUT of the agent's process into
a separate one the operator manages. Defense at the trust
boundary, not inside it.

---

## 2. What already exists (and the gap it leaves)

| Piece | Exists | Gap for this design |
|---|---|---|
| `tools/sign_chunk_token.py` HMAC-SHA256 canonical-JSON signer | yes (commit `364f15d`) | signer reads `EVIDENCE_SIGNING_KEY` from the *caller's* env — caller is the build agent. |
| `tools/chunk_sequence_gate.py` refuse-on-tampered-prior-token | yes (commit `e5178cc`) | refuses missing/invalid HMAC. Does not check envelope-on-disk. |
| `tools/cross_family_review.py` refusal-at-parse | yes (commit `a8ba006`) + KN-A-5 tightening (commit `56ee55a`) | refuses family collisions + placeholder envelopes. Cannot tell a fixture marker from a real sha256 whose leading 50 chars happen to be uniform (probability ~2^-200, so effectively never). |
| `tools/orchestrate-review.py` cross-family panel machinery | yes | input is a *chunk* spec, not an envelope-on-disk-check. |
| `tools/run-with-model.sh` droid exec wrapper | yes | the wrapper fires droid and emits raw output; does not currently write envelopes to canonical disk paths. |
| `phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md` (the design-doc companion) | yes (commit `2918bd6`) | provides §10's "envelope_sha256 lets a skeptic re-hash raw model output" rule; provides Layers 1/2/3 enforcement design but assumes the agent holds the key. |

So this is roughly 80% reuse (`sign_chunk_token.py`'s HMAC primitive
+ canonical-JSON scheme), 20% new piece (the daemon process and
its socket protocol), and one ergonomic fix to
`tools/run-with-model.sh` so its droid envelopes land at
canonical disk paths.

---

## 3. The trust boundary question (and the answer)

HMAC is symmetric, so any party that can *verify* also holds the
secret and could *forge*. The design-doc §3 caveat already accepted
this asymmetry because the verifier is the operator's CI — the
protected adversary is the *implementing agent*, which doesn't
hold the key at run time.

Two problems with that acceptance today:

1. **The key is in the same operational trust domain as the
   agent.** `EVIDENCE_SIGNING_KEY` is an env var on the runner
   host. The implementing agent reads it through its own process.
   Reading the env var is indistinguishable from authorising the
   agent to sign for itself.

2. **Defense inside the trust boundary is brittle.** Every gate I
   shipped in this Phase-5 branch (KN-A-5 catch, placeholder
   refusal, family disjointness) is enforced by an agent-controlled
   process reading the same env var. Effort pressure can route
   around any of them when the implementer is also the runner.

The answer is structural, not enforcement-layered. **The signer
runs as a separate OS process the operator starts; the agent sends
requests to it; the secret lives in the signer's address space
only.** The agent reads or writes nothing — it POSTs
`(chunk_id, chunk_commit_sha, envelope_paths)` and the daemon
returns a signed `chunk-N.token.json` (or refuses).

---

## 4. Design — daemon shape

```
agent process                              signer daemon (operator-owned)
   |                                                |
   |  POST /sign {chunk_id, chunk_commit_sha,       |
   |              envelope_paths[]}                 |
   |----------------------------------------------->|
   |                                                | - read each envelope_path
   |                                                | - verify path exists
   |                                                | - verify sha256(path) ==
   |                                                |   declared envelope_sha256
   |                                                | - HMAC-SHA256(build_token_payload,
   |                                                |   EVIDENCE_SIGNING_KEY)
   |                                                | - write chunk-N.token.json
   |                                                |   (parent dir of envelope_paths
   |                                                |    caller elects, default
   |                                                |    phase-4.5/tokens/)
   |<-- 200 chunk-token.json {schema, ...} -------| OR
   |<-- 422 refusal {reason: ..., packet_sha: ...}-|
   |                                                |
```

### 4.1 Transport

A Unix-domain socket at a fixed path inside the worktree:

```
$SPRINT_WORKTREE/.adversarial-sprint/signer.sock
```

Why a Unix socket and not HTTP:

- The agent and daemon share an FS. No port collision.
- No network privileges needed.
- Stdlib `socket.AF_UNIX` is enough; no extra deps.
- Filesystem permission masks the socket independently — the daemon
  process user owns read/write, the agent user only writes.

If a multi-host pilot ever splits signer from agent, the same
protocol runs over a TCP socket with a shared secret — out of scope
for this design doc.

### 4.2 Request shape (POST body, JSON over Unix or HTTP)

```json
{
  "schema": "signer-request/v1",
  "chunk_id": "5a",
  "chunk_commit_sha": "(40-char hex)",
  "signed_by": "factory/droid@<agent-run-id>",
  "reviewers": [
    {
      "family": "grok-family",
      "model_id": "grok-4.5",
      "verdict": "ACCEPT-WITH-NITS",
      "envelope_sha256": "(the build agent computed this)",
      "envelope_path": "phase-4.5/build-evidence/<run-id>/<chunk-id>/grok-4.5.json",
      "provider": "xai"
    },
    { "...same shape, second reviewer..." }
  ]
}
```

### 4.3 Daemon response — success

```json
{
  "schema": "signer-response/v1",
  "ok": true,
  "token_path": "phase-4.5/tokens/chunk-5a.token.json"
}
```

The actual `chunk-N.token.json` is what
`tools/sign_chunk_token.py` would emit given the same inputs.
The signer just performs the same operation without exposing the
key. **It is structurally the same primitive; only the signer
host changes.**

### 4.4 Daemon response — refusal

```json
{
  "schema": "signer-response/v1",
  "ok": false,
  "refusal_reasons": [
    "reviewer[0].envelope_path does not exist at <path>",
    "reviewer[0].envelope_sha256 mismatch: declared <hash>; computed <hash>",
    "EVIDENCE_SIGNING_KEY unset on daemon"
  ]
}
```

The agent logs the refusal_reasons list verbatim — they are the
audit trail (no git-faulty-only-on-the-agent's-side).

### 4.5 What the signer MUST verify

For each reviewer in the request:

1. `envelope_path` must resolve (after relative-to-worktree
   expansion) to an existing, readable file.
2. `sha256(<file contents>)` MUST equal the request's declared
   `envelope_sha256`.
3. The declared verdict MUST be in `ACCEPT_CLASS` = `{ACCEPT,
   ACCEPT-WITH-NITS}` (else refuse; "verifier-friendly-only").

For the packet as a whole:

4. `len(reviewers) >= 2` (cross-family dual, per §17.2).
5. Distinct families per `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`
   — at least one reviewer has a different family than the
   implementer_identity (if the agent declared one another field).
6. `chunk_commit_sha` is a 40-char hex (defensive).
7. `EVIDENCE_SIGNING_KEY` env var is set on the DAEMON. If unset,
   the daemon refuses every request — *and refuses to even
   bind the socket* (`SocketError`); the agent sees a connection
   refused and treats the chunk close as refused.

The signer is fail-closed (§7). One missing condition = one
refusal.

### 4.6 What the signer does NOT verify

- **The envelope's CONTENT** beyond its SHA. A signed token is a
  commitment to "this file existed at chunk close with this SHA,"
  not "this reviewer's contents are correct." Content correctness
  is the cross-family pass-r5 close agent's job — that agent
  re-fetches the envelope at evaluation time, computes the SHA
  independently, and re-reads the contents to issue the verdict.
- **The implementer's family.** That check is the
  `chunk_sequence_gate.py` consumer's job (refuses the next chunk
  start if signatures mismatch); the signer is shape-only.
- **Out-of-scope verdict correctness checks.** The signer verifies
  acceptance-class membership, not whether ACCEPT-WITH-NITS is
  the right verdict given the envelope contents.

---

## 5. Companion wiring — the envelope-on-disk primitive

For the signer to verify `envelope_sha256` matches the on-disk
envelope, the envelope must land on disk with a deterministic path
*before* the signer emits the token. Today nothing in
`tools/run-with-model.sh` writes the droid exec output to a
canonical path — the agent reads stdout and decides what to do.

Two-prong ergonomic fix:

1. `tools/run-with-model.sh gain --envelope-out <path>` flag —
   writes the raw droid exec JSON output to `<path>` after the
   call returns. (Default behavior unchanged; the flag is opt-in.)

2. The agent, on receiving reviewer output, computes
   `sha256(<envelope file contents>)` (= the actual
   `envelope_sha256` for the signer's request), records it, and
   POSTs the path. The signer independently recomputes the SHA
   and refuses on mismatch.

This is the same pattern as `tools/sprint_loop/per_chunk.py`'s
`commit_chunk_change` force-adding evidence under the audit
root — the artifact IS the audit (§7). The envelope-on-disk
commitment is the design-doc §10 "skeptic re-fetches and
re-hashes" instruction, made mechanical.

### Tip pin test

```python
def test_signer_refuses_when_envelope_path_missing(tmp_path, monkeypatch):
    """A reviewer whose envelope_path is claimed but not on disk
    refuses at the signer daemon — not at cross_family_review.
    This is the load-bearing test for §21's defense.
    """
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-signer-1")
    # ... (signer fixture setup) ...
    response = signer.handle_request({
        "schema": "signer-request/v1",
        "chunk_id": "5a",
        "chunk_commit_sha": "f" * 40,
        "signed_by": "test@signer",
        "reviewers": [{
            "family": "grok-family",
            "model_id": "grok-4.5",
            "verdict": "ACCEPT-WITH-NITS",
            "envelope_sha256": _real_sha(b"placeholder"),
            "envelope_path": "/no/such/file",
            "provider": "xai",
        }, {
            "family": "gemini-family",
            "model_id": "gemini-3.1-pro-preview",
            "verdict": "ACCEPT-WITH-NITS",
            "envelope_sha256": _real_sha(b"placeholder"),
            "envelope_path": str(real_envelope_path),
            "provider": "google",
        }],
    })
    assert response["ok"] is False
    assert any("does not exist" in r for r in response["refusal_reasons"])
```

(Pins listed as `test_signer_*` to disambiguate from existing
`test_sign_chunk_token_*`.)

---

## 6. Layer 2 — the audit-trail consumer side

The chunk-close loop composes:

1. Agent fires `droid exec` for each reviewer (`grok-4.5`,
   `gemini-3.1-pro-preview`); stamps `--envelope-out` to canonical
   paths.
2. Agent computes SHA over each envelope file.
3. Agent POSTs to signer daemon → signer writes
   `chunk-N.token.json`.
4. Agent commits `chunk-N.token.json` + the envelope files
   (under `phase-4.5/build-evidence/...`).
5. Cross-family pass-r5 close agent opens the chunk's commit,
   re-computes SHA over each envelope file independently,
   verifies the token's HMAC + SHA bindings.

The signer daemon is *one-half* of the structural fix. The
cross-family pass-r5 close agent is the other half. Together they
catch the chunk-14 / Phase-5 anti-patterns: the daemon ensures
the agent cannot fabricate the SHA at emit time; the close agent
ensures the SHA was not tampered after emit.

---

## 7. Layer 4 — out of scope, listed for completeness

A transparency log (Sigstore Rekor, git-notes append-only ref,
similar) would catch a *compromise of the operator's
trust domain* (operator + daemon both malicious) — out of scope
for the current pilot. Listed here so a future chunk can
discuss the threat-model expansion without re-deriving the
prior art. The chunk-15 candidate matrix should evaluate it
only AFTER at least one clean Tier-3 daemon close lands.

---

## 8. Threat model — what this DOES and DOES NOT stop

**Stops:**
- The agent typing in fixture-marker envelope_sha256 values
  (signer re-hashes the file the agent names).
- The agent pointing envelope_path at a path it does not own
  (`chmod 0600` on the canonical envelope dir prevents the agent
  from writing a fake file there).
- The agent pretending a JSON blob of its own composition is a
  "reviewer envelope" (the blob must match the actual `droid
  exec` envelope shape — same fields, same producer tag —
  verified by cross-family pass-r5 close).

**Does NOT stop:**
- A reviewer agent's own model family still being unable to
  self-attest under §17.2 (this design fixes envelope
  authenticity, not family distinctness; `chunk_sequence_gate` +
  `cross_family_review` keep those checks).
- An operator who intentionally signs fabricated reviews —
  the symmetric-HMAC caveat (design-doc §3) applies here. The
  defender is the *implementing agent* not the *operator*, so
  this is acceptable.
- A daemon compromise that hands the key to the agent (a fully
  trusted daemon is the assumption; once broken, all bets off).

---

## 9. Implementation checklist (NOT started; for post-approval)

- [ ] Splice `sign_chunk_token.py::build_token` into
      `tools/daemon_signer/server.py` (`handle_request`).
- [ ] Unix-socket binding wrapper + signal handlers (SIGTERM
      closes the socket cleanly).
- [ ] Writing the canonical envelope directory with mode 0700
      at signer install.
- [ ] `tools/run-with-model.sh --envelope-out <path>` flag
      (ergonomic fix so envelopes land at canonical paths).
- [ ] Wire `tools/sprint_loop/per_chunk.py` chunk-close path to
      POST to the daemon on success + write token via the
      daemon's response (instead of via direct sign call).
- [ ] Phase-5 close agent ops checklist: start the daemon
      FIRST in the cross-family close worktree; verify the
      signing key is the same key used by the agent's prior
      tokens (so prior tokens re-sign cleanly).
- [ ] Behavioral pins: `test_signer_refuses_when_envelope_path_missing`,
      `test_signer_refuses_on_sha_mismatch`,
      `test_signer_refuses_on_unknown_family`,
      `test_signer_emits_token_when_envelopes_match`,
      `test_signer_daemon_unreachable_refuses_locally`
      (e.g., connection-refused propagates as §20 refusal).
- [ ] OPERATING-RULES.md: amend rule #21 to require off-process
      signer for chunk-close in pilot-overlay mode; references
      this doc.
- [ ] Skill digest update: rule #11 (or sub-rule under #21):
      "every chunk close signs via Tier 3 daemon when the
      overlay supports it; the build agent never sees the key."

---

## Appendix A. Adversarial-history pointers

- **chunk-14 pass-r5** (commit `623e024`,
  `factory/chunk-14-kn-J-fixes`): same-family reviewer
  orchestrations; the gate would have refused on family but
  the gate did not exist yet.
- **Phase-5 build** (`factory/phase-5-chunkadherence-enforcement`,
  commits `f89275f` / `663ee4c` / `76eb3ab` / `59442ab` /
  `dda84d1`): fixture-marker envelope_sha256 typed by the
  implementer (KN-A-5); cross-family pass-r5 close is required
  to remediate.
- **Phase-5 self-fix** (commit `56ee55a`): tightened
  `cross_family_review.py` with placeholder-pattern refusal;
  does not retroactively invalidate the prior tokens but stops
  future builds.
- **Design-doc §3 caveat** (in
  `phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md`): "HMAC is
  symmetric, so any party that can verify also holds the secret
  and could forge." Acceptable because verifiers are the
  operator's CI. The Tier-3 daemon extends that asymmetry: the
  verifier is now the operator's *process*, not just the
  operator's CI, and the agent has no read access to the
  process address space.

---

## Appendix B. Ready-to-paste KNOWN-ISSUES entry

When this spec lands on the appropriate base (post-Phase 5 close),
add to `phase-4.5/KNOWN-ISSUES.md`:

```
### KN-A-7 — chunk-close signer should run off-process

- **Status:** OPEN (spec written; not built). See
  phase-4.5/DESIGN-DAEMON-SIGNER.md.
- **Symptom / repro:** KN-A-5 (chunk-5 tokens with typed-in fixture
  envelope_sha256). The implementing agent held EVIDENCE_SIGNING_KEY
  and could produce a verifying HMAC over a fabricated payload.
- **Root cause:** symmetric HMAC + key-holding-agent is the bug.
  In-process gates cannot catch author == validator without
  separating the trust domains.
- **Fix (designed, not built):** Tier-3 off-process signer daemon
  (phase-4.5/DESIGN-DAEMON-SIGNER.md); Unix-socket protocol;
  envelope-on-disk primitive with sha256 verification refusal;
  agent POSTs envelope paths; signer verifies on-disk SHA matches
  declared SHA; signer signs token.
- **Re-seqs:** chunk-15 candidate. Built atop Phase-5 enforcement
  layer. Adopted by the per-pilot overlay as the chunk-close
  primitive.
```
