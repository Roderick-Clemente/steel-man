# Validator output — Unit 4 `/sitemap.xml` (closes Grok's dangling-reference finding)

Grok's Unit 2–3 review left one material nit: `/robots.txt` and `/llms-full.txt` both
declared a `Sitemap:` URL that returned 404. Unit 4 built the real `/sitemap.xml` to close
the dangling reference, and this is the validation of that unit, verbatim.

---

Two commits on pilot/sitemap since origin/main:
8afc6314 Pilot/sitemap — Unit 4: real /sitemap.xml (closes Grok's dangling-reference
         finding) — 3 files changed, 111 insertions
a282b35b Unit 4 done — stopped per spec.

Unit 4 spec compliance:
New handler api/sitemap_xml.py with handle_sitemap_xml() returning
Response(SITEMAP_URLSET, mimetype="application/xml") — bare mimetype, Werkzeug appends
charset=utf-8 exactly once.
@app.route("/sitemap.xml") thin stub in app.py after the /llms-full.txt stub, continuing
the AI-discovery cluster.
Sitemap body: valid XML urlset at http://www.sitemaps.org/schemas/sitemap/0.9, 8 <loc>
entries (/, /about, /pricing, /demo, /hello, /time, /llms.txt, /llms-full.txt). All 14
forbidden substrings absent (/api/*, /dashboard, /account, /logout, /transactions,
/metrics, /robots.txt, and static variants).

Test test_sitemap_xml_serves_valid_urlset: 200, ct.startswith("application/xml"), exactly
1 charset=, body parses as XML, contains https://qbank.dev/ and https://qbank.dev/llms.txt,
no /api/ / /dashboard / /metrics / /robots.txt.
Test test_robots_sitemap_promise_resolves: reads Sitemap: URL straight from /robots.txt,
hits that path on the Flask test client, asserts 200 (closes Grok's loop).

Direct flask test_client invariants (assert on reality):
endpoint       Content-Type                                            charset body   notes
/robots.txt    text/plain; charset=utf-8                               1       304 B  Unit 1 lock held
/llms.txt      text/plain; charset=utf-8                               1       1996 B Unit 0 lock held
/llms-full.txt text/plain; charset=utf-8                               1       8384 B post-Kimi-cleanup size
/metrics       text/plain; version=0.0.4; charset=utf-8; charset=utf-8 2       1168 B UNCHANGED, pre-existing defect, owned by main
/sitemap.xml   application/xml; charset=utf-8                          1       500 B  new

Prove cycle for /api/ exclusion lock (true removal, not superstring mutation):
Baseline: /api/ in body = False, body length 500.
Inject <url><loc>https://qbank.dev/api/sessions</loc></url> ahead of </urlset> (truly new
<loc>, contains /api/).
RED: AssertionError: sitemap must not include /api/* routes — 1 failed in 0.12s.
/api/ exclusion lock is real.
Restore from backup; body = 500B; /api/ = False. GREEN sanity.
git diff api/sitemap_xml.py empty — no on-disk drift after the cycle.

Untouched per spec: /metrics, /llms.txt, /robots.txt, /llms-full.txt response behavior;
api/robots_txt.py; main (no merge, no PR).

Branch cleanup (per spec):
origin/pilot/ai-discovery — deleted (was merged via PR #9 → a1050a87).
origin/pilot/llms-txt — deleted (was merged earlier).
origin/pilot/sitemap — preserved (this branch, Unit 4).
origin/orchestrator/steer — preserved (read channel).
origin/main — preserved.

Out of scope and NOT started (awaiting orchestrator verify + human merge gate): homepage
rewrite, canonical content model, OpenAPI, JSON-LD, RSS/JSON feeds, AI-crawler
observability, WCAG audit.
