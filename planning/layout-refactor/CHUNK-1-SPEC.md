# CHUNK-1-SPEC — path-root constants + route ALL hardcoded sites

**Parent PLAN:** `planning/layout-refactor/PLAN.md` v3 (`ed98cd3`)
**Branch:** `factory/layout-refactor`
**Chunk ID:** `chunk-D1-1`
**Predecessor:** none (first chunk of D1)
**Successor gate:** `tools/chunk_sequence_gate.py --prior-token phase-4.5/tokens/chunk-D1-1.token.json --next-chunk-id chunk-D1-2`

## 1. Problem statement (§13)

The runner and gate code hardcode phase-dir prefixes in 21
runner/gate code sites (grep-verified inventory below). Moving
those dirs before the constants exist would produce a big-bang move
that no reviewer can audit. This chunk introduces a single source
of truth for the paths and routes every runner/gate site through
it, with the paths still pointing to their current homes. **No
directory moves happen in this chunk.** The constants default to
today's layout so behaviour is unchanged; Chunk 2 flips them to
the new taxonomy homes.

**Scope qualifier:** "ALL" means all **live-path** hardcoded
sites — the sites the sprint-loop runner, the gates, and the
orchestrator-seat shell script (`fire-design-review.sh`, §2.4)
construct at runtime. Frozen historical generators
(`phase-4/gen-findings.py`, `phase-4/reconstruct-telemetry.py`,
`phase-3/gen-telemetry.py`, `phase-3.1/gen-telemetry.py`,
`phase-0/evidence/probe-4/*.sh`) have internal path strings that
git-mv in Chunk 2 and go stale post-move; these are **fenced as
follow-on** (§2.5), not routed in Chunk 1, because they are
one-shot scripts that produce committed evidence bytes (immutable)
and are not on any live runtime path.

**Site count.** §2.2–§2.4 list **20 rows covering 26 distinct
line-sites** (§2.2: 13 rows / 13 sites; §2.3: 5 rows / 11 sites;
§2.4: 2 rows / 2 sites). Any prose elsewhere claiming "21" is
superseded by this count and by the tables themselves, which are
authoritative. PLAN §5's "~21" was an estimate made before the
grep; the tables are the grep output.

## 2. Surface touched (grounded inventory, grep-verified)

### 2.1 New constants to add to `tools/sprint_loop/config.py`

Add these module-level constants (or a `phase_path` helper +
dataclass, executor's choice) near the top of `config.py`, after
`MODEL_FAMILY_MAP`. **Representation: relative path segments**
(not `os.path.join(framework_root, ...)`) because `framework_root`
lives on the `Config` dataclass, not at module level. The helper
takes an explicit `framework_root` argument at call time.

| Constant | Default value (relative segments) | Flipped in Chunk 2 to |
|----------|-----------------------------------|----------------------|
| `EVIDENCE_ROOT` | `""` (empty — resolves to `framework_root` itself) | `"evidence"` |
| `PLANNING_ROOT` | `""` (empty — resolves to `framework_root` itself) | `"planning"` |
| `TOKENS_ROOT` | `os.path.join("phase-4.5", "tokens")` | `os.path.join("evidence", "phase-4.5", "tokens")` |
| `PROMPTS_ROOT` | `os.path.join("phase-4.5", "prompts")` | `os.path.join("planning", "phase-4.5", "prompts")` |
| `SCRIPTS_ROOT` | `os.path.join("phase-1", "scripts")` | `os.path.join("tools", "phase-1-scripts")` |
| `LOCKS_ROOT` | `os.path.join("phase-1", "locks")` | `os.path.join("tools", "phase-1-locks")` |
| `EVIDENCE_CODE_ROOT` | `os.path.join("phase-3.2", "evidence")` | `os.path.join("tools", "phase-3.2-evidence")` |

The helper `phase_path(framework_root, kind, *parts)` composes
`os.path.join(framework_root, <constant>, *parts)`. There is **no
`phase=` parameter** — the phase segment is already embedded in the
constant (e.g. `TOKENS_ROOT` carries `phase-4.5`). For example:
`phase_path(cfg.framework_root, "scripts", "lock.py")` returns
`<framework_root>/phase-1/scripts/lock.py` today, and
`<framework_root>/tools/phase-1-scripts/lock.py` after Chunk 2's
flip. The `Config.default_locks_dir()` and `default_evidence_dir()`
methods call `phase_path(self.framework_root, "locks")` and
`phase_path(self.framework_root, "evidence", "phase-4.5", "build-evidence", run_id)`
respectively (segment-preserving).

**Forward invariant (binding on Chunk 2).** Chunk 2 flips constant
**values only**. The relative-segment representation is invariant
across the flip: no constant may be rewritten as
`os.path.join(framework_root, ...)`, because `framework_root` is
not available at module level (it lives on the `Config` dataclass)
and such a form would `NameError` at import. If CHUNK-2-SPEC's flip
table contradicts this, **this spec governs** and CHUNK-2-SPEC must
be corrected before `chunk-D1-2` opens. (Known: CHUNK-2-SPEC §2.2
currently drafts `SCRIPTS_ROOT → os.path.join(framework_root,
"tools", "phase-1-scripts")`, which violates the invariant; flagged
to the planner.)

### 2.2 Hardcoded sites to route through the constants

Every `os.path.join(...)` or string literal that constructs a
`phase-N/...` path must be replaced by a call to the constant /
helper. The executor must NOT change behaviour — the constants
default to today's paths, so the resolved path is identical.

| File:line | Current hardcoded path | Route through |
|-----------|------------------------|--------------|
| `tools/sprint_loop/per_chunk.py:108` | `os.path.join(framework_root, "phase-1", "scripts", "lock.py")` | `SCRIPTS_ROOT / "lock.py"` |
| `tools/sprint_loop/per_chunk.py:112` | `os.path.join(framework_root, "phase-1", "locks")` | `LOCKS_ROOT` |
| `tools/sprint_loop/per_chunk.py:124` | `os.path.join(framework_root, "phase-1", "locks", ...)` | `LOCKS_ROOT / ...` |
| `tools/sprint_loop/per_chunk.py:136` | `os.path.join(framework_root, "phase-1", "locks", ...)` | `LOCKS_ROOT / ...` |
| `tools/sprint_loop/per_chunk.py:164` | `os.path.join(framework_root, "phase-1", "scripts", "valid-red.py")` | `SCRIPTS_ROOT / "valid-red.py"` |
| `tools/sprint_loop/per_chunk.py:213` | `os.path.join(framework_root, "phase-1", "scripts", "verify-green.py")` | `SCRIPTS_ROOT / "verify-green.py"` |
| `tools/sprint_loop/per_chunk.py:279` | `os.path.join(framework_root, "phase-3.2", "evidence", "local_backend.py")` | `EVIDENCE_CODE_ROOT / "local_backend.py"` |
| `tools/sprint_loop/config.py:157` | `os.path.join(self.framework_root, "phase-1", "locks")` (`default_locks_dir`) | `LOCKS_ROOT` (composed with `self.framework_root`) |
| `tools/sprint_loop/config.py:162` | `os.path.join(self.framework_root, "phase-4.5", "build-evidence", run_id)` (`default_evidence_dir`) | `EVIDENCE_ROOT / "phase-4.5" / "build-evidence" / run_id` (segment-preserving) |
| `tools/sprint_loop/backends.py:125` | `os.path.join(framework_root, "phase-4.5", "build-evidence", ...)` (fallback in `LocalBackend.validate`) | `EVIDENCE_ROOT / "phase-4.5" / "build-evidence" / ...` |
| `tools/orchestrate-review.py:78` | `os.path.join(args.framework_root, "phase-3.2", "evidence", "local_backend.py")` | `EVIDENCE_CODE_ROOT / "local_backend.py"` (composed with `args.framework_root`) |
| `phase-3.2/evidence/local_backend.py:76` | `script = os.path.join(framework_root, "phase-1", "scripts", "verify-green.py")` (the FUNCTIONAL subprocess in `run_verify_green()`) | `SCRIPTS_ROOT / "verify-green.py"` |
| `phase-3.2/evidence/local_backend.py:375` | `"verify_green": "phase-1/scripts/verify-green.py"` (path string in producer's runtime output JSON — code, not an evidence byte) | `str(SCRIPTS_ROOT / "verify-green.py")` or the relative form |

### 2.3 Prose / docstring / argparse help / banner text

These are not `os.path.join` sites but string literals that name
`phase-4.5/tokens/` or `phase-4.5/build-evidence/` in human-readable
text. Route them through the constant so the prose cannot drift
from the path:

| File:lines | Current text | Route through |
|-----------|-------------|--------------|
| `tools/sprint_loop/chunk_close_banner.py:42,51,99` | banner text mentions `phase-4.5/tokens/` and `phase-4.5/build-evidence/` | `TOKENS_ROOT` / `EVIDENCE_ROOT` in f-strings |
| `tools/sprint-loop.py:1116,1118` | CLI help mentions `phase-4.5/build-evidence/` | `EVIDENCE_ROOT` in help string |
| `tools/chunk_sequence_gate.py:9,119` | docstring + argparse help mention `phase-4.5/tokens/` | `TOKENS_ROOT` in prose |
| `tools/sign_chunk_token.py:6,135` | docstring mentions `phase-4.5/tokens/` | `TOKENS_ROOT` in prose |
| `tools/sprint_loop/config.py:275,277` | `--evidence-output-dir` argparse help in `build_config`'s parser names `<framework-root>/phase-4.5/build-evidence/<run-id>/` (:275) and `phase-4.5/build-evidence dir stays clean` (:277) | `EVIDENCE_ROOT` in help string |

**Why `config.py:275,277` is in scope:** `--evidence-output-dir` is
defined in **two** parsers — `sprint-loop.py` (rows above, :1116,1118)
and `config.py`'s `build_config` (:275,277). Both print a
`--help` surface. Routing only the first leaves the second printing a
stale path after Chunk 2's flip, which is exactly the drift this
section exists to prevent. Both must be routed.

**Fenced in this section (comments, NOT routed):**
`tools/sprint_loop/config.py:87,88` — the dataclass field comments
`# defaults to phase-1/locks/` and
`# defaults to phase-4.5/build-evidence/<run-id>/`. These are
comments, not runtime strings; they cannot interpolate a constant.
They are covered by the §2.5 docstring/comment fence, in a file this
chunk otherwise edits. Naming them here so their omission is a
stated decision rather than an oversight.

### 2.4 Shell script + `paths.sh` shell mirror

`phase-5/scripts/fire-design-review.sh` has two hardcoded sites:
- `:87` `RUN_DIR="phase-4.5/build-evidence/${RUN_ID}"`
- `:155` `python3 phase-5/scripts/envelope-manifest.py "$RUN_DIR"`

Introduce `tools/sprint_loop/paths.sh` — a sourced shell fragment
exporting **the subset of roots the shell surface needs** (2 of the
7 Python constants; the other 5 have no shell consumer). **Today's
values** (the defaults; Chunk 2 flips them):

```sh
# tools/sprint_loop/paths.sh — sourced by fire-design-review.sh
# Today's layout (Chunk 1 defaults). Chunk 2 flips these.
EVIDENCE_ROOT=""                    # → "evidence" in Chunk 2
PHASE5_SCRIPTS_ROOT="phase-5/scripts"  # → "tools/phase-5-scripts" in Chunk 2
```

`fire-design-review.sh` sources it and composes. **The source path
must be anchored to `REPO_ROOT`, which the script already computes
at `:41` and `cd`s into at `:42`:**

```sh
# fire-design-review.sh lives at phase-5/scripts/ — insert AFTER the
# existing REPO_ROOT computation (currently line 41-42):
#   REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
#   cd "$REPO_ROOT"
. "$REPO_ROOT/tools/sprint_loop/paths.sh"

# EVIDENCE_ROOT is empty today, so RUN_DIR starts with "phase-4.5/..."
# After Chunk 2: EVIDENCE_ROOT="evidence", so RUN_DIR starts with "evidence/phase-4.5/..."
RUN_DIR="${EVIDENCE_ROOT:+${EVIDENCE_ROOT}/}phase-4.5/build-evidence/${RUN_ID}"
ENVELOPE_MANIFEST="${PHASE5_SCRIPTS_ROOT}/envelope-manifest.py"
```

**Do NOT use `$(dirname "$0")/../sprint_loop/paths.sh`** — the
script lives at `phase-5/scripts/`, so that resolves to
`phase-5/sprint_loop/paths.sh`, which does not exist. The script
runs under `set -euo pipefail` (`:39`), so a bad source path is a
hard failure at source time, and no existing test executes this
file. §4.2 test 4 exists to catch exactly this.

The `${EVIDENCE_ROOT:+${EVIDENCE_ROOT}/}` idiom handles the empty-
default case (today) and the non-empty case (Chunk 2) without
producing a leading slash. The `paths.sh` values match the Python
constants; Chunk 2 flips both together.

### 2.5 Frozen historical generators (fenced — follow-on, NOT routed in Chunk 1)

These scripts have internal `phase-N/...` path strings but are
**one-shot generators** that produce committed evidence bytes
(immutable per §21). They are not on any live runtime path —
`gen-findings.py` and `reconstruct-telemetry.py` were run once to
produce `telemetry/findings.jsonl` and `telemetry/runs.jsonl`;
`gen-telemetry.py` (phase-3 and phase-3.1) produce phase-3/3.1
telemetry rows; `phase-0/evidence/probe-4/*.sh` are probe scripts.
Chunk 2 git-mvs them to `tools/phase-N-gen/` and
`tools/phase-1-probes/`; their internal path strings go stale
post-move. They are **fenced as follow-on** — not routed in Chunk 1,
not edited in Chunk 2. If a future re-run is needed, the generator
is updated then (the committed evidence bytes it produced are
immutable regardless).

| File:lines | Status |
|-----------|--------|
| `phase-4/reconstruct-telemetry.py:31-32,172,180` | fenced follow-on |
| `phase-4/gen-findings.py:153,190,235,271` | fenced follow-on |
| `phase-3/gen-telemetry.py:101` | fenced follow-on |
| `phase-3.1/gen-telemetry.py:106` | fenced follow-on |
| `phase-0/evidence/probe-4/run_probe.sh:5,10` | fenced follow-on |
| `phase-0/evidence/probe-4/setup_probe.sh:5` | fenced follow-on |

### 2.5.1 `locked-test-guard.py` — self-relative break that Chunk 2 MUST own

`phase-1/hooks/locked-test-guard.py:46-49` computes:

```python
DEFAULT_LOCKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locks"
)
```

This contains **no `phase-[0-9]` literal**, so the grep methodology
behind §2.2–§2.4 structurally cannot see it. It resolves correctly
today (`phase-1/hooks/` → `phase-1/` → `phase-1/locks`).

**After Chunk 2 it breaks, and it fails CLOSED.** Chunk 2 moves
hooks → `tools/phase-1-hooks/` and locks → `tools/phase-1-locks/`.
The self-relative computation then yields `tools/locks`, which will
not exist. `LOCKS_REQUIRED` defaults to `"1"` (`:56`), and per the
F1 fix an absent locks dir means *inability to enforce → deny*.
The guard would therefore **deny every writer tool call** in any
sprint run using the hook.

Verified: no test in `tests/` exercises this hook, and CHUNK-2-SPEC
does not currently mention it — **no chunk owns this break**.

**Disposition:** not routed in Chunk 1 (no literal to route; the fix
is a path recomputation, which belongs with the move). **CHUNK-2-SPEC
MUST add `locked-test-guard.py`'s `DEFAULT_LOCKS_DIR` to its edit
surface** and its verify block must assert the hook resolves to the
moved locks dir. Recorded here so the break is owned by name before
`chunk-D1-2` opens rather than discovered after the move.

### 2.5.2 `.py` docstring / comment path citations (fenced follow-on)

Roughly 25 docstring and comment citations of moving paths exist in
`.py` files. Docstrings cannot interpolate constants, so "route
through the constant" is not the fix; an explicit fence is.

Known sites: `per_chunk.py:18,98,153,206,243`;
`orchestrate-review.py:21,29-36`; `local_backend.py:6,14-23`;
`consumer.py:17-23`; `token_accounting.py:18-21`; `lock.py:5,8`;
`valid-red.py:10`; `verify-green.py:9`; `locked-test-guard.py:7`;
`envelope-manifest.py:24`; `test_envelope_manifest.py:10`;
`sprint_loop/__init__.py:14-15`; `sprint-loop.py:12,885`;
`persistent_referee_stub.py:11,20-21`; `plan-lint.py:901`; plus
`config.py:87,88` (§2.3).

Chunk 3's living-doc allowlist is **markdown-only**, so these fall
between chunks unless named. **Disposition:** fenced as a named
follow-on — either a Chunk 2 text refresh or a
`planning/PATH-REDIRECTS.md` note. Not in Chunk 1's surface. Stated
here so the boundary is declared, not discovered at Chunk-2 review.

## 3. What the executor MUST do

1. Add the path-root constants + `phase_path` helper to
   `tools/sprint_loop/config.py`. Constants default to today's
   layout.
2. Route every site in §2.2 and §2.3 through the constants. No
   behavioural drift — the resolved paths are identical to today.
3. Create `tools/sprint_loop/paths.sh` and route
   `fire-design-review.sh`'s two sites through it.
4. Add `tests/test_layout_paths.py` with four tests (see §4.2).
5. Run the full suite and confirm 198 tests green (194 + 4 new).
6. Commit with message `chunk-1: path-root constants + route hardcoded sites through them`.
7. Push to `origin/factory/layout-refactor`.

## 4. Verify (§11 exit checks — checked, not assumed)

### 4.1 Full suite green

`python3 -m pytest -q` → 198 tests, all green. The existing
`tests/test_sprint_loop.py` assertions on `default_locks_dir`
(line 414) and `default_evidence_dir` (line 419) keep passing
because the constants default to today's paths.

### 4.2 New `tests/test_layout_paths.py` (4 tests)

1. **Constant resolution test:** every constant (`EVIDENCE_ROOT`,
   `PLANNING_ROOT`, `TOKENS_ROOT`, `PROMPTS_ROOT`, `SCRIPTS_ROOT`,
   `LOCKS_ROOT`, `EVIDENCE_CODE_ROOT`) resolves to a
   currently-existing directory when composed with the real
   `framework_root` (the repo root). Asserts `os.path.isdir()`
   on each.

2. **Helper path test:** matches the §2.1 signature exactly —
   `framework_root` is a required positional and there is no `phase=`
   parameter:
   ```python
   assert phase_path(framework_root, "tokens", "chunk-5a.token.json") == \
       os.path.join(framework_root, "phase-4.5", "tokens", "chunk-5a.token.json")
   ```
   `phase-4.5/tokens/chunk-5a.token.json` exists on disk today, so
   the test also confirms the composed path is real. A call of the
   form `phase_path(kind=..., phase=...)` would raise `TypeError`
   against the §2.1 signature and MUST NOT be written.

3. **File-wide no-residual-literal test (NOT line-keyed):** for each
   file in §2.2, assert that **no line anywhere in the file** matches
   `os.path.join` combined with a `"phase-` literal. Line-keyed
   assertions are forbidden here: if the executor's edits shift line
   numbers (import additions, rewraps), a line-keyed test reads the
   wrong lines and a missed routing site passes silently. Since this
   is the chunk's only anti-missed-site check (§7), it must be
   drift-proof. Implement as a file-wide regex scan (or an AST walk
   over `Call` nodes, executor's choice) over the 5 files named in
   §2.2. Files whose only remaining `"phase-` literals are the
   §2.1 constant definitions themselves are exempted by excluding
   the constant-definition block in `config.py` explicitly by name.

4. **Shell mirror source test:** the §2.4 composition is unexercised
   by any existing test, and `set -euo pipefail` makes a bad source
   path fatal at run time rather than at lint time. Assert both:
   ```sh
   bash -n phase-5/scripts/fire-design-review.sh
   bash -c '. tools/sprint_loop/paths.sh && test -n "$PHASE5_SCRIPTS_ROOT" && test -f "$PHASE5_SCRIPTS_ROOT/envelope-manifest.py"'
   ```
   plus a grep assertion that the literals `phase-4.5/build-evidence`
   and `phase-5/scripts/envelope-manifest.py` no longer appear in
   `fire-design-review.sh` outside the sourced defaults. This makes
   the test count **198** (194 + 4), which §3 and §4.1 also state.

### 4.3 No directory moves

Two forms, because `git status` only works before the commit and is
clean after it:

- **Pre-commit:** `git status --porcelain` shows no `R` (rename)
  entries.
- **Post-commit (the enforceable form for a chunk-close referee):**
  `git show --name-status <chunk-commit>` contains no `R` entries.

The phase directories (`phase-0`…`phase-5`) are untouched. The
layout allowlist (`tests/test_repo_layout.py`) is unchanged.

## 5. Ergonomic friction fixed inline (§18.4)

- `chunk_close_banner.py` prints the token path in prose; replace
  with the constant so the banner cannot drift.
- `sprint-loop.py`'s CLI help mentions the path in two places;
  fold both to reference the constant.
- The shell/Python constant split (`paths.sh`) is the friction
  fix for `fire-design-review.sh` — without it, Chunk 2 would
  rewrite the shell path anyway, and the rewrite would own the
  debt.

## 6. What NOT to do (fences)

- **Do NOT move any directories.** That is Chunk 2's job. This
  chunk is constants + routing only.
- **Do NOT flip the constants to the new taxonomy paths.** The
  constants default to today's layout; Chunk 2 flips them.
- **Do NOT edit evidence bytes.** The `phase-3.2/evidence/`
  schema JSONs and any committed bundles are immutable. The
  `local_backend.py:375` change is to the producer CODE (which
  emits the path string), not to a committed bundle JSON.
- **Do NOT touch `tests/test_repo_layout.py`'s allowlist.** That
  is Chunk 2's surface.
- **Do NOT touch `.gitignore`, `pytest.ini`, `plan-lint.py`, or
  the CI workflow.** Those are Chunk 2's surface.
- **Do NOT hold `EVIDENCE_SIGNING_KEY` or write to
  `phase-4.5/tokens/`.** The referee signs; the builder does not.

## 7. Rule application

| Rule | Where |
|------|-------|
| §7 | grep assertion test (§4.2 test 3) asserts on reality, not exit code |
| §11 | §4 exit checks are real pytest assertions + grep, not assumptions |
| §13 | this spec states the problem + constraints; the executor chooses how to factor the constants (module-level vs dataclass vs helper) |
| §14 | `run-with-model.sh` + `adapters/factory.py` untouched; `paths.sh` mirrors the Python constant |
| §18.2 | one chunk, one commit, one verifiable unit |
| §18.3 | per-chunk verify block (§4) |
| §18.4 | banner + CLI help + `paths.sh` friction fixed inline |
| §21 | no evidence bytes edited |
| §22 | builder does not sign; referee audits and signs |

## 8. Chunk-close protocol

After the code lands, the suite is green, and the branch is pushed:
1. The builder fires Tier-2 validators (kimi-k3 + minimax-m3) as
   orchestrator per §24 (operator-selected models, no signing key
   held by builder).
2. The builder captures raw stdout to
   `phase-4.5/build-evidence/<run-id>/chunk-D1-1/<model>.json`.
3. The builder posts `VALIDATE COMPLETE:` + `REVIEW REQUEST:
   chunk=chunk-D1-1 commit=<sha> paths=<envelope-paths>` to
   `STEER.md`.
4. The referee audits §21/§17.2/§23 and signs
   `phase-4.5/tokens/chunk-D1-1.token.json` (the tokens dir does NOT
   move to `evidence/phase-4.5/tokens/` until Chunk 2; Chunk 1's
   close uses today's path).
5. The next chunk (`chunk-D1-2`) MUST NOT start until
   `tools/chunk_sequence_gate.py --prior-token
   phase-4.5/tokens/chunk-D1-1.token.json --next-chunk-id
   chunk-D1-2` exits 0.
