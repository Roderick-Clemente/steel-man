# Chunk-D5-1 audit-script-only verifier prompt

You are validating chunk-D5-1. Author spec at
`planning/evidence-hygiene/CHUNK-D5-SPEC.md`; builder prompt at
`planning/evidence-hygiene/PROMPT-D5-BUILDER.md`. Build bundle at
`evidence/phase-4.5/build-evidence/r-chunk-d5-1-builder-20260815-1032/`.
You are firing via `tools/run-review.sh` (this chunk's surface §2.2);
cross-family distinctness holds because your model family (kimi-family)
must not collide with the implementer's family.

Re-derive every §3 floor check from disk state. Capture every command +
exit code; cite file:line. Use exactly the envelope shape in
`tools/conventions/review-bundle.md` §2 for your output: a single
markdown `result` body with sections Header / Round-by-round / Findings
(TAML) / Verdict. The trailing `VERDICT:` line is the only field the
operator parses.

The six §3 checks to re-derive:
1. `tools/conventions/review-bundle.md` exists, cites both exemplars
   (`r-chunk-d3-1-review-20260814-2152` and
   `r-chunk-d4-1-review-20260815-1423`) each ≥2 times.
2. `tools/run-review.sh` executable; refuses exit 2 on missing/empty
   args; `$DROID_MODEL_ID` propagated but not re-checked at wrapper.
3. `tools/README.md` has "## When to use which review tool" listing all
   four scripts (`cross_family_review.py`, `orchestrate-review.py`,
   `run-with-model.sh`, `run-review.sh`).
4. `planning/evidence-hygiene/PLAN.md` §2 3-tier table verbatim with
   precedent SHAs `0663444` / `58c11d3` / `42aa9ca`.
5. `python3 -m pytest -q` → 241 passed, 3 skipped, 0 failed.
6. `python3 tools/wiki-link-audit.py` clean;
   `python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5-SPEC.md` green.
7. Total new non-blank LOC across the four surfaces ≤ 100.

Do NOT hand-paraphrase counts or paths. If a count or path disagrees,
STOP and report. Emit a final `VERDICT: ACCEPT-WITH-NITS` or
`VERDICT: REJECT` line.
