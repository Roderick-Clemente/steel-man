# CHUNK-3-SPEC — living-doc citations + planning/PATH-REDIRECTS.md

**Parent PLAN:** `planning/layout-refactor/PLAN.md` v3 (`ed98cd3`)
**Branch:** `factory/layout-refactor`
**Chunk ID:** `chunk-D1-3`
**Predecessor:** `chunk-D1-2` (must have verified signed token)
**Successor gate:** `tools/chunk_sequence_gate.py --prior-token evidence/phase-4.5/tokens/chunk-D1-3.token.json --next-chunk-id chunk-D1-4`

## 1. Problem statement (§13)

~150 md citations across PRD, OPERATING-RULES, skills, wiki, and
phase docs point at the old `phase-N/...` paths. Living docs get
updated to the new `evidence/`, `planning/`, `tools/phase-N-*/`
paths. **Evidence bytes are immutable** (§21) — citations inside
committed envelopes, manifests, raw/stream files stay as-is and
are covered by a redirects file. This chunk updates the living docs
and creates the redirects file.

## 2. Surface touched

### 2.1 Living-doc allowlist (bounded — per §17 capacity envelope)

The executor updates path citations in EXACTLY these files, and
no others. If a file not on this list surfaces a citation, it is
NOT in scope for D1 (record as follow-on).

- `PRD.md`
- `tools/OPERATING-RULES.md`
- `AGENTS.md`
- `skills/adversarial-sprint/SKILL.md`
- `skills/sprint-invocation/SKILL.md`
- `README.md`
- `tools/conventions/*.md`
- `tools/README.md`
- `tools/KNOWN-ISSUES.md`
- `tools/PHASE-0.5-CLOSE.md`
- `tools/RUN-LEDGER.md`
- `tools/REPRODUCE.md`
- `tools/sprint_loop/prompts/*.md`
- `droid-wiki/*.md` **— path tokens only** (content freshness is D3, not D1)
- `planning/ROADMAP-REVIEW*.md`
- **All docs moved into `planning/<phase>/`** by Chunk 2 (READMEs,
  RUN-PROMPTs, KNOWN-ISSUES, RUN-LEDGER, design docs including
  `DESIGN-PERSISTENT-REFEREE.md`, postmortems, BUILD-NOTES, etc.)

### 2.2 `planning/PATH-REDIRECTS.md` (new file)

A table of old-prefix → new-prefix, with a specified matching
algorithm. Two audiences: (a) a human reader following a stale
citation in an envelope, (b) `tools/wiki-link-audit.py` (teaching
it to consult the redirects is a stretch — not required for D1).

**Matching algorithm (specified, not hand-waved):**
1. Strip an optional absolute repo-root prefix
   (`/Users/factory/work/adversarial-sprint-dev/`) from the
   cited path.
2. Match the longest old-prefix in the table against the
   resulting relative path.
3. Apply only to path-shaped tokens (regex:
   `(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry|evidence|planning)/[\w/.-]+`).
4. Leave prose mentions ("Phase 1 built…") untouched.

**Example entry:**
```
phase-4.5/build-evidence/ → evidence/phase-4.5/build-evidence/
```
So `phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`
→ `evidence/phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`
(segment-preserving).

### 2.3 Citation update rule

For each path-shaped token in a living doc:
- If the token is a `phase-N/...` path that moved to
  `evidence/phase-N/...`, `planning/phase-N/...`, or
  `tools/phase-N-*/...`, update it to the new prefix.
- If the token is a historical narrative ("Phase 1 built
  `phase-1/scripts/lock.py`"), leave it as-is and add a same-line
  redirect note: `(now at tools/phase-1-scripts/lock.py)` OR record
  it in `planning/PATH-REDIRECTS.md` as a historical-narrative
  exception.

## 3. What the executor MUST do

1. Create `planning/PATH-REDIRECTS.md` with the old→new prefix
   table and the matching algorithm specified in §2.2.
2. For each file in the §2.1 allowlist, grep for path-shaped
   `phase-N/...` tokens and update them to the new prefixes per
   §2.3.
3. For residual citations that are historical narrative, add a
   same-line redirect note or record them in
   `planning/PATH-REDIRECTS.md`.
4. Run the full suite and confirm 197 tests green.
5. Run the citation grep (§4.2) and confirm only intentional
   historical-narrative citations remain.
6. Commit with message `chunk-3: update living-doc citations + create PATH-REDIRECTS.md`.
7. Push to `origin/factory/layout-refactor`.

## 4. Verify (§11 exit checks)

### 4.1 Full suite green

`python3 -m pytest -q` → 197 tests, all green.

### 4.2 Citation grep returns only intentional hits

```
grep -rn --include='*.md' 'phase-[0-9]' \
  PRD.md AGENTS.md README.md tools/ skills/ droid-wiki/ planning/
```
returns only intentional historical-narrative citations, each
accompanied by a same-line redirect note OR recorded in
`planning/PATH-REDIRECTS.md` as a historical-narrative exception.

### 4.3 PATH-REDIRECTS covers evidence-internal citations

```
grep -rn --include='*.json' --include='*.raw.txt' --include='*.stream.json' \
  'phase-[0-9]' evidence/
```
Each hit's prefix is in the redirects table in
`planning/PATH-REDIRECTS.md`.

### 4.4 wiki-link-audit green

`python3 tools/wiki-link-audit.py` → green (no dead links
introduced by the citation updates). If the audit tool gets a
new false positive from the move, fix it in the same chunk under
the same guard rail (§14: through the constant).

## 5. Hard stop (capacity bound, per §17)

The verify step greps for residual `phase-[0-9]` citations in the
allowlisted living docs. If residual hits are only historical
narrative, STOP — document them in `planning/PATH-REDIRECTS.md`
rather than rewriting the narrative. The bullet list in §2.1 is
the file allowlist; if a file not on the list surfaces a citation,
it is NOT in scope for D1 (record as follow-on).

**Do not pull D3 (wiki freshness content) into D1.** `droid-wiki/`
gets path-token updates only, not content rewrites.

## 6. What NOT to do (fences)

- **Do NOT edit evidence bytes.** Everything under `evidence/` is
  immutable. Citations inside committed envelopes stay as-is;
  `planning/PATH-REDIRECTS.md` carries the delta.
- **Do NOT touch `main`.**
- **Do NOT hold `EVIDENCE_SIGNING_KEY` or write tokens.**
- **Do NOT update files outside the §2.1 allowlist.** If a file
  not on the list surfaces a citation, record it as a follow-on.
- **Do NOT rewrite historical narrative.** Add a redirect note or
  record in PATH-REDIRECTS, but do not rewrite the narrative.
- **Do NOT pull D3 (wiki content freshness) into D1.** Path
  tokens only in `droid-wiki/`.

## 7. Rule application

| Rule | Where |
|------|-------|
| §7 | §4 exit checks assert on reality (grep, wiki-link-audit) |
| §11 | §4 exit checks are real greps + tool runs |
| §13 | this spec states the problem + constraints; the executor chooses the citation-update mechanics |
| §17 | §5 hard stop bounds the chunk |
| §18.2 | one chunk, one commit |
| §18.3 | per-chunk verify block (§4) |
| §21 | evidence bytes untouched; PATH-REDIRECTS carries the delta |

## 8. Chunk-close protocol

Same as CHUNK-1-SPEC §8, with `chunk=chunk-D1-3`.
