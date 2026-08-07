# Phase 2 — plan-v1 review findings + dispositions

**Plan under review:** `phase-2/plan-v1.md`, `Plan-hash: sha256:72eccff570a4ff67827805dd69b1769953e4041f5549823217f365610230acd8`
**Panel (single-blind, cross-family):** `grok-4.5` (xAI) + `gemini-3.1-pro-preview` (google).
Planner seat was `claude-opus-5` (anthropic) — family-distinct from both reviewers.
**Envelopes:** `phase-2/build-evidence/plan-review-{grok-4.5,gemini-3.1-pro-preview}-envelope.json`

## Verdicts
| Reviewer | Verdict | Blocking/High | Other |
|---|---|---|---|
| gemini-3.1-pro-preview | **APPROVE** | 0 | 0 findings |
| grok-4.5 | **APPROVE** | 0 | 3 medium, 3 low |

**Outcome: plan-v1 is hash-bound APPROVED by cross-family panel — 0 blocking, 0 high.**
The Phase 2 exit criterion (PRD §11: "one real plan reaches a hash-bound
approval") is satisfied at `sha256:72eccff5…`, pending the human plan-approval
gate (PRD §6). The plan-v1 artifact is **frozen** (not mutated) to keep the
approval bound to its hash; the non-blocking findings below are dispositioned as
**accepted amendments** that travel with the approved plan into Phase 3.

## Findings + dispositions (Grok round-1; Gemini raised none)

### M1 — medium — §8 acceptance criteria don't bind the Picard identity
*Claim:* AC (ii) only requires some `username/email/full_name/address` to render;
a page still showing "Demo User" could pass while missing brief §2.5.
*Disposition:* **ACCEPT — amendment A1.** Chunk 3 + test 3 already require Picard,
but the binding observable belongs in the acceptance criteria.
**Amendment A1 (adds AC vi):** "After `POST /login {username: demo}` on a
freshly-initialized DB, `GET /profile` body contains `Jean-Luc Picard`,
`jpicard@starfleet.fed`, and the apostrophe-safe address substring
`USS Enterprise NCC-1701-D`." (Stale-local-DB caveat R3 still applies.)

### M2 — medium — risk table missing PRD §5.2 columns
*Claim:* §5 has Risk/Likelihood/Impact/Mitigation but not `severity`,
`probability`, or `review_trigger`.
*Disposition:* **ACCEPT — amendment A2.** Rename `Likelihood → probability`, add
`severity` and `review_trigger` per risk:
- R1 two-schema drift — severity high, review_trigger: **human if the panel/executor forces option (a)**.
- R2 NULL address on existing rows — severity high (only if (a)), review_trigger: human if (a).
- R3 stale local DB — severity low, review_trigger: none (dev-local cosmetic).
- R4 config address not per-user — severity medium, review_trigger: **human when a second user is seeded**.
- R5 over-exposure by later drift — severity medium, review_trigger: CI (key-set test fails).
- R6 route-registration friction — severity low, review_trigger: none.

### M3 — medium — test plan doesn't falsify "DB is source of truth, not session"
*Claim:* Post-login `session["full_name"]/["username"]` already equal the DB
(`api/login.py:16-18`), so tests 3–5 pass even if the handler renders session
values and only calls the getter for `address`.
*Disposition:* **ACCEPT — amendment A3 (adds test 8).** "Authenticate as demo,
then make session display fields diverge from the DB (mutate the users row, or
set a divergent `session['full_name']`); `GET /profile`; assert the body follows
the DB via `get_user_profile`, not the session copy." Prefer a public-interface
divergence test over white-box mocking.

### L1 — low — Chunk 1 leaves the address constant under-specified
*Disposition:* **ACCEPT — amendment A4.** Pin in the Chunk 1 interface: constant
default = the brief's Picard address string; single env override
`PROFILE_DEMO_ADDRESS` (matching the `os.environ.get(NAME, default)` pattern at
`db_flags.py:17`, `app.py:46-48`).

### L2 — low — stale-session test lacks a concrete suite-local mechanism
*Disposition:* **ACCEPT — amendment A5.** test 7 obtains the state via the Flask
test client session API (`with client.session_transaction() as s: s['user_id'] =
<nonexistent id>`), or by deleting the seeded row then setting the session.
Outcome-level, not full code.

### L3 — low — citation precision on `.gitignore`
*Disposition:* **ACCEPT (noted).** `.gitignore:33` is the general `*.db` pattern
(which does ignore `quantum_bank.db`), not a file-specific entry. No behavior
change; recorded for accuracy. Grok's spot-check otherwise found **0 material
citation falsehoods** across the load-bearing claims.

## Reconciliation decision
All findings are non-blocking (medium/low) and the panel APPROVED. Per the
zero-buffer budget and to preserve the hash-bound approval, plan-v1 is **not
re-planned**; amendments A1–A5 are accepted verbatim from the panel's own
`recommended_change` fields and become **binding acceptance criteria for the
Phase 3 executor**. A re-review round is not spent because the deltas are the
reviewers' own recommendations (no new design). If the human gate prefers a
re-reviewed `plan-v2`, that is a cheap single round to add.

**Status: awaiting human plan-approval gate (PRD §6).**
