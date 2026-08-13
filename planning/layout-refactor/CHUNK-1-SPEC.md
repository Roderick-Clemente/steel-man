# CHUNK-1-SPEC — path-root constants + route ALL hardcoded sites

**Parent PLAN:** `planning/layout-refactor/PLAN.md` v3 (`ed98cd3`)
**Branch:** `factory/layout-refactor`
**Chunk ID:** `chunk-D1-1`
**Predecessor:** none (first chunk of D1)
**Successor gate:** `tools/chunk_sequence_gate.py --prior-token phase-4.5/tokens/chunk-D1-1.token.json --next-chunk-id chunk-D1-2`

## 1. Problem statement (§13)

The runner, gate, and orchestrator-shell code hardcode phase-dir
prefixes across **19 inventory rows / 23 line-sites** (§2.2–§2.4,
grep-verified; see the site-count table below). Moving those dirs before the constants exist would
produce a big-bang move that no reviewer can audit. This chunk
introduces a single source of truth for the paths and routes every
live-path site through it, with the paths still pointing to their
current homes. **No directory moves happen in this chunk.** The
constants default to today's layout so behaviour is unchanged;
Chunk 2 flips them to the new taxonomy homes.

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

**Site count.** §2.2–§2.4 list **19 rows covering 23 distinct
line-sites**:

| section | rows | line-sites |
|---------|------|-----------|
| §2.2 | 13 | 13 |
| §2.3 | 4 | 8 |
| §2.4 | 2 (prose, not a table) | 2 |
| **total** | **19** | **23** |

Counted mechanically from the tables, which are authoritative.
`sign_chunk_token.py` contributes zero routable sites (both citations
are docstrings, §2.5.2) and `chunk_sequence_gate.py:9` is a docstring,
not a second site. PLAN §5's "~21" was a pre-grep estimate.

Note the **judge test reports 18 hits**, not 23, because several cited
line numbers fall inside a single multi-line string constant. The test
counts code objects; the table counts cited lines. Both are correct at
what they measure, and the test is the one that gates.

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

**Derived constants are permitted and expected.** The seven roots are
a floor, not a ceiling. `EVIDENCE_ROOT` is `""` today, so an f-string
of the form `f"{EVIDENCE_ROOT}/phase-4.5/build-evidence"` renders a
**leading slash** and changes `--help` bytes — a real behavioural
drift. The executor should therefore introduce a derived segment
constant, e.g.
`BUILD_EVIDENCE_REL = os.path.join("phase-4.5", "build-evidence")`,
reusing the same name §2.4 introduces in `paths.sh` so the Python and
shell mirrors stay legible against each other. (Note
`os.path.join("", "phase-4.5", "build-evidence")` does *not* produce a
leading slash, so `os.path.join` composition is also acceptable; the
f-string form is the one that needs the derived constant.)

**How the locked judge test exempts these (asked and answered).** In
`config.py` the residual scan exempts **any module-level ALL-CAPS
assignment**, not an enumerated list, precisely so derived constants
the executor needs are not flagged. Outside `config.py` the strict
seven-name set applies, because there a path literal is a residual
rather than a definition. So: define derived segment constants at
module level in `config.py`, in caps, and the scan will skip them.

**Declared-but-unconsumed in Chunk 1:** `PLANNING_ROOT` and
`PROMPTS_ROOT` have **no call site in §2.2–§2.4**. They are declared
now so the full root set lands in one reviewable commit; their first
consumers appear in Chunk 2 (when `phase-4.5/prompts/` moves under
`planning/`). Reviewers should **not** expect call-site rewrites for
these two, and §4.2 test 1 covers them only via the existing-dir
assertion. Every other constant has at least one §2.2–§2.4 consumer.

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

**MANDATORY import bootstrap for `local_backend.py`.**
`phase-3.2/evidence/local_backend.py` is **not** imported as a
module — it is invoked as a standalone script,
`python3 <framework_root>/phase-3.2/evidence/local_backend.py`
(from `per_chunk.py:279` and `orchestrate-review.py:78`). Verified:
the file has **no `sys.path` manipulation and no `sprint_loop`
imports at all** (stdlib only, `:25-34`). So
`from sprint_loop.config import SCRIPTS_ROOT` **fails with
ModuleNotFoundError** in that process unless `tools/` is placed on
`sys.path` first.

The executor MUST add a minimal bootstrap mirroring the existing
pattern at `tools/orchestrate-review.py:57-59`:

```python
tools_dir = os.path.join(framework_root, "tools")
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)
```

resolving `framework_root` from the script's own location (the file
sits at `phase-3.2/evidence/`, so `framework_root` is
`dirname(dirname(dirname(abspath(__file__))))`).

**The dirname depth is Chunk-2-safe and MUST NOT be "corrected".**
`phase-3.2/evidence/local_backend.py` is two directories below the
repo root; Chunk 2's target `tools/phase-3.2-evidence/local_backend.py`
is *also* two directories below it. Three `dirname` calls reach the
root in both layouts, so the depth does **not** change and CHUNK-2-SPEC
must **not** "fix" it — doing so would break the path. Chunk 2 owns
only the `SCRIPTS_ROOT` value flip, not this computation.

**Which `framework_root` composes the routed paths (binding).** The
bootstrap's self-relative `framework_root` exists *only* to put
`tools/` on `sys.path` before argparse runs; it MUST NOT be used to
compose `SCRIPTS_ROOT`. The routed paths at `:76` and `:375` compose
against the **runtime `--framework-root` argument**, which is the
value the caller passed and the only one that can be correct when the
framework and the pilot repo differ (the CI at `:169,191` already
distinguishes a pilot's `phase-1/locks/` from the framework's). The
two values are permitted to differ and the spec does not require them
to agree; the import path uses the self-relative one, every composed
filesystem path uses the argument.

Acceptable alternative to the bootstrap: place the constants in a
dependency-free module importable from both trees without a path
hack. Either way the choice must be explicit in the commit, and §4.2
test 3b asserts the script still runs with an unguarded module-level
import.

### 2.3 Prose / docstring / argparse help / banner text

These are not `os.path.join` sites but string literals that name
`phase-4.5/tokens/` or `phase-4.5/build-evidence/` in human-readable
text. **Only interpolatable strings are in scope here.**

**§2.3 covers (a) runtime-formatted strings only:** banner text, CLI
`--help` strings, and argparse `help=` values. These are ordinary
expressions and can become f-strings referencing a constant, so they
must be routed.

**§2.3 explicitly does NOT cover (b) module/function docstrings.**
Docstrings are static literals evaluated before any constant is in
scope; they cannot interpolate without `__doc__` rewriting, which is
not worth the churn. The docstring citations at
`tools/chunk_sequence_gate.py:9` and `tools/sign_chunk_token.py:6`
are therefore moved to the §2.5.2 fence, **not** routed. An earlier
draft of this spec listed them as routable while §2.5.2
simultaneously declared docstrings unroutable; §2.5.2 is correct and
governs. §4.2 test 3's AST scan skips docstrings for exactly this
reason, so the fence and the check now agree.

| File:lines | Current text | Route through |
|-----------|-------------|--------------|
| `tools/sprint_loop/chunk_close_banner.py:42,51,99` | banner text mentions `phase-4.5/tokens/` and `phase-4.5/build-evidence/` | `TOKENS_ROOT` / `EVIDENCE_ROOT` in f-strings |
| `tools/sprint-loop.py:1116,1118` | CLI help mentions `phase-4.5/build-evidence/` | `EVIDENCE_ROOT` in help string |
| `tools/chunk_sequence_gate.py:119` | argparse help mentions `phase-4.5/tokens/` | `TOKENS_ROOT` via f-string |

`tools/sign_chunk_token.py` has **no routable site**: both its
citations (`:6` module docstring and `:135` a `Returns:` line inside a
function docstring) are docstrings, moved to the §2.5.2 fence. Note
`:135` is a `Returns:` line, **not** argparse help — the locked judge
test's AST scan skips it as a docstring.

**Docstring rewording is AUTHORIZED (and preferred over fencing).**
The executor may reword the fenced docstring citations at
`tools/chunk_sequence_gate.py:9` and `tools/sign_chunk_token.py:6`
(and `:135`) to name the **constant** instead of the path — e.g.
`<TOKENS_ROOT>/chunk-N.token.json` in place of
`phase-4.5/tokens/chunk-N.token.json`. This is strictly better than
leaving them fenced, because a fenced docstring still holds a path
that goes stale at Chunk 2, whereas naming the constant stays true
across the flip. Verified zero behaviour change: neither tool passes
`__doc__` to argparse — both use a literal `description=`
(`chunk_sequence_gate.py:116`, `sign_chunk_token.py:265`). The locked
judge test skips docstrings either way, so rewording is permitted but
not gated.

**The locked judge test is the authoritative site enumeration.** Line
numbers in the tables above are informational and drift as the file is
edited. `tests/test_layout_paths.py` enumerates the
residual sites **mechanically at run time** over the files named here,
so the executor's worklist is the test's failure output, not these
numbers. Running
`python3 -m pytest tests/test_layout_paths.py::test_no_residual_hardcoded_phase_paths_in_routed_code`
prints the current, exact list. The tables name the *files* and the
*intent*; the test names the *sites*.
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
exporting **three shell variables**, of which only one corresponds to
a §2.1 Python constant:

| shell var | §2.1 Python constant? | note |
|-----------|----------------------|------|
| `EVIDENCE_ROOT` | **yes** | same name, same value, flips in Chunk 2 |
| `BUILD_EVIDENCE_REL` | no — shell-specific segment | mirrors the derived Python constant of the same name (§2.1) |
| `PHASE5_SCRIPTS_ROOT` | no — shell-specific segment | no Python consumer; flips in Chunk 2 |

Note this is deliberately **not** a 1:1 mirror of §2.1:
`PHASE5_SCRIPTS_ROOT` is not among the seven constants and
`BUILD_EVIDENCE_REL` is derived, so the export set is neither a subset
nor a superset of §2.1. It carries exactly what
`fire-design-review.sh` composes with, no more.

**Today's values** (the defaults; Chunk 2 flips them):

```sh
# tools/sprint_loop/paths.sh — sourced by fire-design-review.sh
# Today's layout (Chunk 1 defaults). Chunk 2 flips these.
EVIDENCE_ROOT=""                        # → "evidence" in Chunk 2
BUILD_EVIDENCE_REL="phase-4.5/build-evidence"  # segment; unchanged by Chunk 2
PHASE5_SCRIPTS_ROOT="phase-5/scripts"   # → "tools/phase-5-scripts" in Chunk 2
```

`BUILD_EVIDENCE_REL` exists so the `phase-4.5/build-evidence`
literal lives in **one** place (`paths.sh`) rather than being
re-spelled inside `fire-design-review.sh`. Chunk 2 does not change
its value — the segment is preserved under the new evidence root —
but centralising it is what makes the §4.2 test 3 residual
assertion satisfiable.

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
# No phase-* literal appears in this file — both segments come from paths.sh.
RUN_DIR="${EVIDENCE_ROOT:+${EVIDENCE_ROOT}/}${BUILD_EVIDENCE_REL}/${RUN_ID}"
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

**Gate (not just text).** A `MUST` written only in Chunk 1's spec
does not stop Chunk 2 from opening without it. Therefore
`chunk-D1-2` MUST NOT open until **both** of these are committed:

1. CHUNK-2-SPEC amended to own **both** self-relative
   `dirname(dirname(abspath(__file__)))/locks` defaults, which are
   invisible to the phase-literal grep and both of which resolve to a
   nonexistent `tools/locks` after Chunk 2's moves:
   - `phase-1/hooks/locked-test-guard.py:46-49` (`DEFAULT_LOCKS_DIR`)
   - `phase-1/scripts/lock.py:42` (`--locks-dir` default). The runner
     always passes `--locks-dir` explicitly (`per_chunk.py`), so the
     sprint path is safe; direct CLI and documented usage are not.
     Same failure class, and it is the file **this spec's own judge
     tests are locked with**.

   (`local_backend.py`'s bootstrap is explicitly **excluded** — its
   dirname depth is unchanged by the move; see §2.2.)
2. CHUNK-2-SPEC's constant-flip table corrected to the
   relative-segment representation per §2.1's forward invariant.

This is a precondition on the Chunk-2 **spec**, checkable by reading
the committed CHUNK-2-SPEC before `chunk-D1-2`'s start gate fires.

### 2.5.2 `.py` docstring / comment path citations (fenced follow-on)

Roughly 25 docstring and comment citations of moving paths exist in
`.py` files. Docstrings cannot interpolate constants, so "route
through the constant" is not the fix; an explicit fence is.

Known sites: `chunk_sequence_gate.py:9` and `sign_chunk_token.py:6`
(moved here from §2.3 — module docstrings, unroutable);
`per_chunk.py:18,98,153,206,243`;
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
4. **Do NOT author `tests/test_layout_paths.py`.** It is written and
   **content-locked by the planner** before this chunk opens, and it
   is the judge of this chunk's work. Per framework invariant #3 the
   executor of a chunk must not author or modify the tests that
   grade it. The executor treats the locked file as read-only: run
   it, do not edit it. If a locked test appears wrong, that is a
   `BLOCKED:` line to the planner, not an edit. Lock manifest:
   `phase-1/locks/`, recorded via `phase-1/scripts/lock.py`.
5. Run the full suite and confirm 197 tests green (194 + 3 from the
   locked judge file).
6. Commit with message `chunk-1: path-root constants + route hardcoded sites through them`.
7. Push branch `factory/layout-refactor` to the **dev** repo:
   `git@github.com:Roderick-Clemente/adversarial-sprint-dev.git`.

   **Do not rely on the name `origin`.** It resolves differently across
   clones — at least one working clone has `origin` pointing at
   `Roderick-Clemente/adversarial-sprint`, which does not carry this branch.
   Verify before pushing with
   `git remote -v` and `git ls-remote --heads <remote> factory/layout-refactor`,
   and add a named remote if `origin` is not the dev repo. The referee
   resolves review-request SHAs against the dev repo, so a push
   elsewhere makes the commit unreachable for review.

## 4. Verify (§11 exit checks — checked, not assumed)

### 4.1 Full suite green

`python3 -m pytest -q` → 197 tests, all green. The existing
`tests/test_sprint_loop.py` assertions on `default_locks_dir`
(line 414) and `default_evidence_dir` (line 419) keep passing
because the constants default to today's paths.

### 4.2 Judge tests — `tests/test_layout_paths.py` (3 tests, LOCKED)

**This section states intent only. It deliberately does NOT restate the
predicates.** The executable check is
`tests/test_layout_paths.py`, authored and content-locked by the
planner. Where this spec and that file would express the same rule,
the file is authoritative and the prose copy is deleted rather than
maintained.

**Why (this is the lesson of rounds 3-6).** Four consecutive review
rounds found defects created by prose and code stating the same
predicate in two places. Reviewers read the prose, the prose drifted
from the check, and in one case the prose described a `phase-\d` regex
the check did not implement while the check had a silent-green hole the
prose could not reveal. A duplicated predicate is not documentation, it
is a second implementation with no tests. See the OPERATING-RULES
amendment drafted at `planning/layout-refactor/RULE-AMENDMENT-predicate-duplication.md`.

**Read the test for the predicates. Read this for the intent.**

| # | Test | What it is FOR (intent) |
|---|------|------------------------|
| 1 | `test_path_root_constants_have_expected_values_and_exist` | The seven §2.1 roots exist and hold today's layout, so Chunk 1 provably changes no resolved path. Value-asserted, not existence-asserted, because an existence-only check cannot distinguish a correct empty root from a wrongly-emptied one. |
| 2 | `test_phase_path_helper_signature_and_composition` | The helper's contract is pinned so Chunk 2 cannot quietly change its shape: `framework_root` leading positional, no `phase=`. |
| 3 | `test_no_residual_hardcoded_phase_paths_in_routed_code` | The routing actually happened everywhere §2.2/§2.3 claims, in both composition idioms, plus the shell wiring is real and `local_backend.py` still runs with an unguarded import. This is the chunk's only anti-missed-site check. |

**Scope of test 3, in intent terms only:** it must see *both* ways this
repo builds a path — a joined literal, and bare segments passed into a
composition — and it must not fire on a bare segment used as a
telemetry or HMAC label, which §2.2 excludes by design. The mechanism
that achieves this lives in the test.

**Locked file identity.** sha256 `82035450590bdb81ec63a988e22bb02835f1f9e94e7d6d4e3d628be85a9bf753`,
manifest `phase-1/locks/tests/test_layout_paths.py.lock.json`. The
executor runs it read-only and raises `BLOCKED:` rather than editing it;
only the planner may re-lock, and only before freeze.

**Current state:** valid RED, 3 failed / 194 passed. The three failures
name the missing constants, the missing helper, and the unrouted sites.
The executor's worklist is that failure output.

**Rootdir anchoring** is a property of the test file (paths derived from
`__file__`, `cwd=REPO_ROOT` on subprocesses) preserving the
CWD-independence established by commit `7179934`. Stated here because it
constrains how the executor may invoke the suite, not as a restatement
of an assertion.

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

### 6.1 Fence enforcement (§11 — fences must be checked, not just stated)

Prose fences are unenforceable. Each fence above maps to a
post-commit check the chunk-close referee runs on the chunk commit:

| Fence | Check |
|-------|-------|
| no directory moves | `git show --name-status <sha>` has no `R` entries (§4.3) |
| constants not flipped | §4.2 tests 1–2 assert today's resolved paths |
| no evidence bytes edited | `git show --name-only <sha>` lists no path under `phase-*/build-evidence/` or `evidence/`; the only `phase-3.2/evidence/` entry permitted is `local_backend.py` (producer code) |
| allowlist / config untouched | `git show --name-only <sha>` does not list `tests/test_repo_layout.py`, `.gitignore`, `pytest.ini`, `tools/plan-lint.py`, or `.github/workflows/*` |
| builder did not sign | `git show --name-only <sha>` lists nothing under `phase-4.5/tokens/` |

A single command produces the evidence for all five:
`git show --name-status <chunk-sha>`. If any row fails, the chunk
does not close.

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
