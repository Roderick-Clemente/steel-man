# Validator output — Grok, `pilot/ai-discovery` (Units 2–3)

Independent cross-family review of the `/robots.txt` + `/llms-full.txt` change, run in a
fresh context. The reviewer confirmed it did not read the executor's build log, DONE notes,
or reasoning — the isolation invariant, held here by convention rather than a guard.

Verbatim as delivered; the only edit is redaction of a local worktree path (an internal
machine detail, not part of the finding).

---

VERDICT: ACCEPT-WITH-NITS

Isolation confirmed: did not read BUILD-LOG.md, DONE.md, UNIT3-DONE.md, or any *-DONE.md.

Worktree: detached 04887afd at [local worktree, removed after review]. Range:
8a10711d..origin/pilot/ai-discovery (5 commits). Diff scope: api/robots_txt.py,
api/llms_full_txt.py, app.py (+2 routes), test/test_public_routes.py (+2 tests).
api/llms_txt.py byte-identical to baseline (2398 bytes). /metrics handler block identical
to baseline.

Evidence per criterion

/robots.txt
Check         Observed
Status        200
Content-Type  text/plain; charset=utf-8
charset= count 1
Body          User-agent: *, Allow: /, llms.txt present
Implementation api/robots_txt.py:26 — Response(..., mimetype="text/plain")
              (bare mimetype; no doubled charset)

/llms-full.txt
Check         Observed
Status        200
Content-Type  text/plain; charset=utf-8
charset= count 1
Body          Quantum Bank, Split.io, demo, fictional present
Length        full=8400 / 8384 text chars > short=1996

Untouched surfaces
/llms.txt: unchanged vs baseline; CT text/plain; charset=utf-8 (1 charset)
/metrics: still doubled charset (text/plain; version=0.0.4; charset=utf-8; charset=utf-8,
count=2) — pre-existing, not copied by new routes
New routes use bare mimetype="text/plain" like /llms.txt, not the metrics pattern

Tests
  pytest test/test_public_routes.py -v  →  20 passed in 0.13s
Including test_robots_txt_serves_plain_text and test_llms_full_txt_serves_expanded_manifest
(both green with real assertions, not just exit 0).

Lock proofs (true removal, not superstring trap)
"fictional" → "imaginary": body loses fictional; restored OK
Trap demo: "fictional" → "fictionalX" still contains fictional (false-pass pattern avoided)
Same true-removal for Quantum Bank, Split.io, robots needles, and length shrink — all locks
would fail as intended; originals restored

Method / abuse lens
POST/PUT/DELETE/PATCH → 405 on both new routes
HEAD → 200, empty body, correct CT
Static constant bodies; no query/body reflection → no injection surface
Fixed small responses (304 / ~8KB) → no unbounded response
No secrets in body; only public env var names (SPLIT_API_KEY, DATABASE_URL) as setup docs
(same class as short /llms.txt)

Nits (non-blocking)
1. api/robots_txt.py:10 + api/llms_full_txt.py (~line referencing sitemap) — declares
   Sitemap: https://qbank.dev/sitemap.xml and lists /sitemap.xml, but GET /sitemap.xml
   returns 404. Spec does not require sitemap; crawler nit only (robots points at a
   missing URL).
2. api/llms_full_txt.py endpoint inventory — advertises many routes (login credential-free,
   session-gated APIs). Acceptable for a demo manifest and mostly mirrors /llms.txt;
   slightly expands attack-surface documentation for crawlers. Not a secret leak.
3. Em dash / Unicode in full body (—) is fine under charset=utf-8.

No correctness break, no doubled-charset regression, no additive security defect that
warrants REJECT.

Do not merge/PR/push (review only, as instructed).
