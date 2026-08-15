# Cross-family PLAN review: layout-refactor D1 (v3)

You are a **cross-family reviewer** in the 4-actor review topology
(`OPERATING-RULES §22 + §23 + §24`,
`phase-4.5/DESIGN-PERSISTENT-REFEREE.md`). A build agent
(Factory/Claude family) revised its formal PLAN for a repo layout
refactor after two REJECT rounds, and needs an independent
verdict on v3 before it fires any code chunks. Your job is to audit
the revised PLAN honestly and return a load-bearing verdict.

Repo root: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/layout-refactor` (do NOT operate on `main`;
`main` is FROZEN for the duration of this run).
Commit under review: `ed98cd3` (PLAN v3).

## What to read

**The artifact under review:**
- `planning/layout-refactor/PLAN.md` — the 510-line D1 plan v3.

**The prior REJECT verdicts this revision responds to (read to
judge whether v3 actually fixes the findings):**
- `phase-4.5/build-evidence/r-layout-refactor-20260813-142900/plan/grok-4.5.json`
  (v1 REJECT — Chunk 1 inventory lie, dry-run blind, locks/fixtures
  misclassified, plan-lint regex, §7 overclaim, success criterion)
- `phase-4.5/build-evidence/r-layout-refactor-20260813-142900/plan/gemini-3.1-pro-preview.json`
  (v1 REJECT — same blockers, fewer findings)
- `phase-4.5/build-evidence/r-layout-refactor-v2-20260813-2007/plan/kimi-k3.json`
  (v2 REJECT — 4 missed sites incl local_backend.py:76, Chunk 4 exit
  check structurally broken, evidence-target contradictory,
  phase-3.1/locks unmapped, prompt templates swept into evidence)
- `phase-4.5/build-evidence/r-layout-refactor-v2-20260813-2007/plan/minimax-m3.json`
  (v2 ACCEPT-WITH-NITS — "PLAN is sound, ship it")

**The operator brief (machine-local, gitignored):**
- `CLEANUP-PLAN.md` — sections "Target taxonomy", "D1", "Hard
  constraints".

**For grounding:**
- `tools/OPERATING-RULES.md` — §5, §11, §13, §17, §18, §20–§24.
- `tests/test_repo_layout.py` — the current top-level allowlist.
- `tools/sprint_loop/config.py` — home of the proposed path-root
  constants (lines 157/162 are the `default_locks_dir`/`default_evidence_dir`).
- `tools/sprint_loop/per_chunk.py` — 7 hardcoded `os.path.join` sites.
- `tools/sprint_loop/backends.py:125` — the fallback `os.path.join`
  v3 claims to route.
- `tools/orchestrate-review.py:78` — the `local_backend.py` path.
- `phase-3.2/evidence/local_backend.py:76` — the FUNCTIONAL
  subprocess call to `verify-green.py` (not the cosmetic `:375`
  string). v3 claims to route this; verify.
- `tools/plan-lint.py:903,1151` — the path-prefix regexes.
- `pytest.ini` — the `norecursedirs`.
- `.github/workflows/adversarial-sprint-ci.yml:165,169,191,192,245`
  — the hardcoded phase paths.
- `phase-5/scripts/fire-design-review.sh:87,155` — the two
  hardcoded sites.
- `phase-4.5/DESIGN-PERSISTENT-REFEREE.md` §4.3 for the
  fire-XOR-sign topology.

## What to challenge

### 1. Did v3 actually fix the v2 REJECT findings?

The v2 kimi-k3 REJECT findings were:

a. **Chunk 1 inventory still missed 4 sites**: `local_backend.py:76`
   (the functional subprocess, not the cosmetic `:375`),
   `backends.py:125`, `fire-design-review.sh:155`, CI `yml:192`.
b. **Chunk 4 "real run" structurally cannot exit 0**: reconcile gate
   reads stdin → EOF → SystemExit(1); `invalid-red/` fixtures are
   invalid (exit 3); `produce_evidence` raises RuntimeError without
   EVIDENCE_SIGNING_KEY; `commit_chunk_change` would checkout -b
   off the branch.
c. **Evidence-target layout contradictory**: Chunk 1/2 flattened
   `build-evidence/`, Chunk 3 PATH-REDIRECTS preserved it.
d. **`phase-3.1/locks/` unmapped** (3 committed lock manifests).
e. **`phase-3.2/reviews/review-prompt.md`** swept into evidence (it
   is a prompt template, code-consumed).
f. **`tools/sprint_loop/prompts/`** on no chunk surface.
g. **Chunk 3 allowlist** phrasing excluded non-README moved docs.
h. **Nits**: line numbers (config.py:157/162), arithmetic (198),
   vacuous "phase-4/demo/ evidence", decorative cross_family_review.py
   row.

For each, verify whether v3 actually addresses it — by checking
the grounded inventory in v3 §5 Chunk 1 against a fresh grep, by
tracing the Chunk 4 exit-check control flow, and by checking the
evidence-target shape consistency across §4, §5 Chunk 2, and the
PATH-REDIRECTS example.

### 2. Is the v3 Chunk 1 inventory now complete?

v3 §5 Chunk 1 lists 21 hardcoded sites in a table. Run your own
grep (e.g. `rg "phase-[0-9]" --type py --type sh --type yml --type
ini` in `tools/` and `phase-*/`) and compare. Any site v3 still
misses? Any false positive?

### 3. Is the v3 Chunk 4 exit check now real?

v3 replaces the full-runner invocation with direct real invocations
of the 4 moved scripts (lock.py, valid-red.py, verify-green.py,
local_backend.py) against a valid-RED fixture + path-existence test.
Does this actually work? Trace:
- Does `lock.py` accept the arguments v3 specifies?
- Does `valid-red.py` classify a valid RED correctly (exit 0)?
- Does `verify-green.py` work post-fix?
- Does `local_backend.py` with a test EVIDENCE_SIGNING_KEY produce a
  signed bundle?
- Is the `tests/fixtures/phase-1/valid-red/test_valid_red.py` fixture
  specified enough to land, or under-specified?

### 4. Is the evidence-target shape now consistent?

v3 picks segment-preserving
(`evidence/phase-4.5/build-evidence/r-...`). Check:
- Does `config.py:162`'s `default_evidence_dir` compose this shape?
- Does `tests/test_sprint_loop.py:419` expect this shape?
- Does the PATH-REDIRECTS example use this shape?
- Does `.gitignore`'s scratch pattern match this shape?

### 5. Are the taxonomy rehomings in v3 correct?

- `phase-3.1/locks/` → `tools/phase-3.1-locks/` (code side). Correct?
- `phase-3.2/reviews/review-prompt.md` → `planning/phase-3.2/reviews/`
  (planning, code-consumed). Correct? The envelope JSONs in
  `phase-3.2/reviews/` stay in `evidence/phase-3.2/reviews/` — is
  that split clean, or is there a file that could be misclassified?
- `phase-4/demo/*.md` → `planning/phase-4/demo/` (planning, not
  evidence). Correct?

### 6. What did v3 still miss?

- Anything the v2 reviewers named that v3 silently dropped.
- Any new risk introduced by v3's revisions.
- Any interaction between chunks that v3's per-chunk verify blocks
  miss.

## Output format

End your review with EXACTLY one of these verdict lines, on its
own line:

```
VERDICT: ACCEPT
VERDICT: ACCEPT-WITH-NITS
VERDICT: REJECT
```

Before the verdict, list findings in the shape:

```
- severity: {blocker|high|medium|low|nit}
  category: {factual|scope|sequencing|process|omission|spec-deviation|correctness}
  section: PLAN.md §X.Y (or specific file)
  claim: <the PLAN claim you challenge>
  evidence: <path:line or specific observation>
  recommended_change: <what should change>
```

Then a one-paragraph verdict rationale citing the load-bearing
finding(s).

## Rules of engagement

- You are a **cross-family reviewer**. Your family (kimi-k3 or
  minimax-m3) is distinct from the build agent's (Factory/Claude).
  Produce your own independent read; do not paraphrase the PLAN or
  the prior reviews.
- You do NOT sign chunk-close tokens. You emit a raw stdout envelope;
  the persistent referee reads it and signs (§22, §24).
- You do NOT fire other reviewers. One envelope per session (§23).
- Be honest. `ACCEPT` when the PLAN is sound; `REJECT` when a
  load-bearing claim is wrong. `ACCEPT-WITH-NITS` when directional
  and the findings are improvements, not corrections.
- End with the exact `VERDICT: ...` line above so the referee's
  parser can bind your verdict without ambiguity.
