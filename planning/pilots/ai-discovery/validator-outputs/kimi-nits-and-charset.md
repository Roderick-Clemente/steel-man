# Validator output — Kimi (content lens) and the shared charset catch

Two distinct contributions from the Kimi validator across the pilot:

1. **The doubled-charset catch on Unit 1 (`/llms.txt`)** — flagged blind, and independently
   flagged by Grok on the same review. This is the *overlapping* finding: two different model
   families converged on the same RFC-malformed `Content-Type`. Recorded from the shipping
   commit message rather than a pasted report.
2. **Three content nits on Unit 2 (`/llms-full.txt`)**, of which the material one is a
   process-narrative leak into a machine artifact.

---

## 1. Doubled-charset — the overlapping catch (Grok + Kimi, blind)

From QuantumBank commit `308aaa70` ("Fix doubled charset in /llms.txt Content-Type
(validator nit, Grok+Kimi)"), verbatim body:

> The pilot/llms-txt handler built in commit 3f847d22 used
>     Response(body, mimetype="text/plain; charset=utf-8")
> which on this Werkzeug produces a response header of
>     Content-Type: text/plain; charset=utf-8; charset=utf-8
> (charset duplicated). Both Grok and Kimi flagged the same shape in
> their post-build reviews.
>
> Change the handler so Werkzeug appends charset exactly once:
>     Response(body, mimetype="text/plain")
> After:
>     Content-Type: text/plain; charset=utf-8
>         (one charset=, no duplication)
>
> Verified by direct Flask test_client assertion on /llms.txt:
>     raw Content-Type bytes : 'text/plain; charset=utf-8'
>     charset values present : 1
>     ASSERT PASSED.

Hardened by `8a10711d` ("Harness /llms.txt test: assert exactly one charset param"):

> Locks the doubled-charset fix (308aaa70). The prior assertion only checked Content-Type
> startswith text/plain, which a regression to the malformed
> 'text/plain; charset=utf-8; charset=utf-8' would still pass. Now asserts exactly one
> charset= param. Verified: fails when the doubled charset is reintroduced.

Both commits call it a **"nit."** That matters for the record: a defect flagged by both
reviewers that both graded low-severity is exactly the kind the H1 precision metric is meant
to weigh — it counts as a real, RFC-malformed finding, not as noise, but it was not a
correctness break either.

## 2. Three content nits on `/llms-full.txt` (Unit 3 fixes)

Kimi flagged three; all three shipped in commit `2395315b`. Reported by the executor:

> FIX 1 — internal process-narrative removed from manifest closing. Body now ends
> "Last updated: 2026-08-03.\n\nFor the short manifest, see /llms.txt." Audit clean:
> 'worker', 'pilot', 'human-gated', 'canonical content model', 'in-memory' all False on
> the body.
>
> FIX 2 — /metrics doc line in endpoint inventory: parenthetical
> (text/plain; charset=utf-8) dropped. Now reads "GET /metrics Prometheus text exposition."
>
> FIX 3 — assert "fictional" in body.lower() added to
> test_llms_full_txt_serves_expanded_manifest, matching the sibling /llms.txt test.
> Prove-cycle shipped in commit body: GREEN → broke body (both 'fictional' occurrences
> rewritten) → RED on the new assertion → restored → GREEN.

**FIX 1 is the material one:** the expanded manifest had leaked internal process narrative
(words like "worker", "pilot", "human-gated") into a served, machine-facing artifact. That
is a content-lens finding a security/abuse lens would not have surfaced, and it is the
non-overlapping half of the two-reviewer story.

Content-Type invariants after Unit 3 (direct test_client assertion, not exit code):

| endpoint       | Content-Type                                             | charset= | notes |
|----------------|----------------------------------------------------------|----------|-------|
| /robots.txt    | text/plain; charset=utf-8                                | 1        | Unit 1 lock held |
| /llms.txt      | text/plain; charset=utf-8                                | 1        | Unit 0 lock held |
| /llms-full.txt | text/plain; charset=utf-8                                | 1        | body now 8384 B (was 8552, −168 by cleanup) |
| /metrics       | text/plain; version=0.0.4; charset=utf-8; charset=utf-8  | 2        | unchanged, pre-existing defect, owned by main |

Full suite: `20 passed`. `len(llms-full)=8384 / len(llms)=1996 = 4.20x` — the expanded
invariant (> 4× the short manifest) still holds.
