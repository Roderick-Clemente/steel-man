# Cross-family chunk-spec review: CHUNK-1-SPEC

You are a **cross-family reviewer** in the 4-actor review topology.
A build agent has drafted a chunk spec for the first chunk of a
repo layout refactor, and needs an independent verdict before any
code lands. Your job is to audit the spec honestly.

Repo root: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/layout-refactor` (main is FROZEN).
Commit under review: `43a2ff3` (CHUNK-1-SPEC.md).

## What to read

**The artifact under review:**
- `planning/layout-refactor/CHUNK-1-SPEC.md` — the spec for Chunk 1
  (path-root constants + route ALL hardcoded sites).

**The parent PLAN:**
- `planning/layout-refactor/PLAN.md` — v3 at `ed98cd3`. The spec
  should be consistent with the PLAN's §5 Chunk 1 description.

**For grounding (verify the spec's inventory against the repo):**
- `tools/sprint_loop/config.py` — where the constants will live
- `tools/sprint_loop/per_chunk.py` — 7 hardcoded `os.path.join` sites
- `tools/sprint_loop/backends.py:125` — the fallback site
- `tools/orchestrate-review.py:78` — the local_backend.py path
- `phase-3.2/evidence/local_backend.py:76` — the FUNCTIONAL subprocess
- `tools/sprint_loop/chunk_close_banner.py` — banner text
- `tools/sprint-loop.py:1116,1118` — CLI help
- `tools/chunk_sequence_gate.py:9,119` — docstring
- `tools/sign_chunk_token.py:6,135` — docstring
- `phase-5/scripts/fire-design-review.sh:87,155` — shell sites

## What to challenge

### 1. Is the inventory complete and grep-verified?

The spec lists 21 hardcoded sites in §2.2-§2.4. Run your own grep
(`rg "phase-[0-9]" --type py --type sh` in `tools/` and `phase-*/`)
and compare. Any site the spec still misses? Any false positive?

### 2. Are the constants well-designed?

The spec proposes 7 constants + a `phase_path` helper. Are they:
- Resolvable relative to `framework_root` (not absolute)?
- Defaulting to today's layout (so behaviour is unchanged)?
- Going to flip cleanly in Chunk 2?

### 3. Are the verify checks real §11 checks?

The spec proposes 3 new tests in `tests/test_layout_paths.py`. Are
they asserting on reality (§7) or on plausible strings? Will they
actually catch a missed routing site?

### 4. Is the chunk boundary clean?

Does this chunk touch anything that should be Chunk 2's job (dir
moves, allowlist changes, linter fixes)? Does it touch anything
that should be Chunk 3's job (living-doc citations)?

### 5. Are the fences real?

§6 "What NOT to do" — are the fences enforceable, or just prose?

## Output format

End with EXACTLY one of:
```
VERDICT: ACCEPT
VERDICT: ACCEPT-WITH-NITS
VERDICT: REJECT
```

Before the verdict, list findings in the shape:
```
- severity: {blocker|high|medium|low|nit}
  category: {factual|scope|sequencing|process|omission|spec-deviation|correctness}
  section: CHUNK-1-SPEC.md §X.Y
  claim: <the spec claim you challenge>
  evidence: <path:line or specific observation>
  recommended_change: <what should change>
```

## Rules of engagement

- Cross-family reviewer. Your family is distinct from the build
  agent's. Produce your own independent read.
- You do NOT sign tokens. You emit a raw stdout envelope.
- Be honest. End with the exact `VERDICT: ...` line.
