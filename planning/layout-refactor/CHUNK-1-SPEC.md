# CHUNK-1-SPEC — path-root constants + route ALL hardcoded sites

**Parent PLAN:** `planning/layout-refactor/PLAN.md` v3 (`ed98cd3`)
**Branch:** `factory/layout-refactor`
**Chunk ID:** `chunk-D1-1`
**Predecessor:** none (first chunk of D1)
**Successor gate:** `tools/chunk_sequence_gate.py --prior-token evidence/phase-4.5/tokens/chunk-D1-1.token.json --next-chunk-id chunk-D1-2`

## 1. Problem statement (§13)

The runner and gate code hardcode phase-dir prefixes in 21 code
sites (grep-verified inventory below). Moving those dirs before the
constants exist would produce a big-bang move that no reviewer can
audit. This chunk introduces a single source of truth for the
paths and routes every hardcoded site through it, with the paths
still pointing to their current homes. **No directory moves happen
in this chunk.** The constants default to today's layout so
behaviour is unchanged; Chunk 2 flips them to the new taxonomy
homes.

## 2. Surface touched (grounded inventory, grep-verified)

### 2.1 New constants to add to `tools/sprint_loop/config.py`

Add these module-level constants (or a `phase_path` helper +
dataclass, executor's choice) near the top of `config.py`, after
`MODEL_FAMILY_MAP`:

| Constant | Default value (TODAY's layout) | Flipped in Chunk 2 to |
|----------|-------------------------------|----------------------|
| `EVIDENCE_ROOT` | `""` (resolves to `framework_root`) | `"evidence"` |
| `PLANNING_ROOT` | `""` (resolves to `framework_root`) | `"planning"` |
| `TOKENS_ROOT` | `os.path.join(framework_root, "phase-4.5", "tokens")` | `os.path.join(EVIDENCE_ROOT, "phase-4.5", "tokens")` |
| `PROMPTS_ROOT` | `os.path.join(framework_root, "phase-4.5", "prompts")` | `os.path.join(PLANNING_ROOT, "phase-4.5", "prompts")` |
| `SCRIPTS_ROOT` | `os.path.join(framework_root, "phase-1", "scripts")` | `os.path.join(framework_root, "tools", "phase-1-scripts")` |
| `LOCKS_ROOT` | `os.path.join(framework_root, "phase-1", "locks")` | `os.path.join(framework_root, "tools", "phase-1-locks")` |
| `EVIDENCE_CODE_ROOT` | `os.path.join(framework_root, "phase-3.2", "evidence")` | `os.path.join(framework_root, "tools", "phase-3.2-evidence")` |

The constants must be **resolvable relative to `framework_root`**
(not absolute paths) so the test suite's `/tmp/fw/` pattern still
works. The helper `phase_path(kind, phase, *parts)` should compose
`os.path.join(framework_root, <root>, phase, *parts)` for kinds
that have a phase dimension, or `os.path.join(<root>, *parts)` for
kinds that don't.

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

### 2.4 Shell script + `paths.sh` shell mirror

`phase-5/scripts/fire-design-review.sh` has two hardcoded sites:
- `:87` `RUN_DIR="phase-4.5/build-evidence/${RUN_ID}"`
- `:155` `python3 phase-5/scripts/envelope-manifest.py "$RUN_DIR"`

Introduce `tools/sprint_loop/paths.sh` — a sourced shell fragment
that exports the same constants as env vars (computed from the
repo root). `fire-design-review.sh` sources it and composes:
```sh
RUN_DIR="${EVIDENCE_ROOT}/phase-4.5/build-evidence/${RUN_ID}"
ENVELOPE_MANIFEST="${TOOLS_ROOT}/phase-5-scripts/envelope-manifest.py"
```
The `paths.sh` values default to today's layout (matching the
Python constants); Chunk 2 flips both the Python and the shell
together.

## 3. What the executor MUST do

1. Add the path-root constants + `phase_path` helper to
   `tools/sprint_loop/config.py`. Constants default to today's
   layout.
2. Route every site in §2.2 and §2.3 through the constants. No
   behavioural drift — the resolved paths are identical to today.
3. Create `tools/sprint_loop/paths.sh` and route
   `fire-design-review.sh`'s two sites through it.
4. Add `tests/test_layout_paths.py` with three tests (see §4).
5. Run the full suite and confirm 197 tests green (194 + 3 new).
6. Commit with message `chunk-1: path-root constants + route hardcoded sites through them`.
7. Push to `origin/factory/layout-refactor`.

## 4. Verify (§11 exit checks — checked, not assumed)

### 4.1 Full suite green

`python3 -m pytest -q` → 197 tests, all green. The existing
`tests/test_sprint_loop.py` assertions on `default_locks_dir`
(line 414) and `default_evidence_dir` (line 419) keep passing
because the constants default to today's paths.

### 4.2 New `tests/test_layout_paths.py` (3 tests)

1. **Constant resolution test:** every constant (`EVIDENCE_ROOT`,
   `PLANNING_ROOT`, `TOKENS_ROOT`, `PROMPTS_ROOT`, `SCRIPTS_ROOT`,
   `LOCKS_ROOT`, `EVIDENCE_CODE_ROOT`) resolves to a
   currently-existing directory when composed with the real
   `framework_root` (the repo root). Asserts `os.path.isdir()`
   on each.

2. **Helper path test:** `phase_path(kind="tokens", phase="phase-4.5")`
   + `"chunk-5a.token.json"` equals the actual on-disk path
   `phase-4.5/tokens/chunk-5a.token.json` (relative to
   `framework_root`). Asserts path equality.

3. **Grep assertion test:** none of the lines listed in §2.2 still
   contain a literal `"phase-1"`, `"phase-3.2"`, or `"phase-4.5"`
   string in an `os.path.join` call. The test reads the specific
   line numbers and asserts the string is absent. This is the
   §7 reality-assertion — the constant is actually used, not just
   defined.

### 4.3 No directory moves

`git status --porcelain` shows no `git mv` operations. The
phase directories (`phase-0`…`phase-5`) are untouched. The
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
   `evidence/phase-4.5/tokens/chunk-D1-1.token.json`.
5. The next chunk (`chunk-D1-2`) MUST NOT start until
   `tools/chunk_sequence_gate.py --prior-token
   evidence/phase-4.5/tokens/chunk-D1-1.token.json --next-chunk-id
   chunk-D1-2` exits 0.
