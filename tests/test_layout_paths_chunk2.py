"""Judge tests for chunk-D1-2 (git mv phase dirs + flip constants).

Authored and locked by the PLANNER before chunk-D1-2 opens.
The executor of chunk-D1-2 must NOT modify this file: framework
invariant #3. If an assertion looks wrong, the executor raises
``BLOCKED:`` to the planner.

These tests verify the POST-FLIP state: constants have the new taxonomy
values, files are at their new locations, and no residual old-layout or
unrouted new-layout paths remain in executable code.

Pre-flip state (EVIDENCE_ROOT == ""): all 3 tests SKIP. The Chunk-1
judge (tests/test_layout_paths.py) covers the pre-flip state and itself
skips post-flip. Suite count is constant: 197 passed + 3 skipped either
way.

The strengthened residual matcher is imported from the Chunk-1 judge
(authored blind, compared with builder probe bd70d10, full agreement on
all 12 synthetic cases). The Chunk-2 judge extends the forbidden
substring set to include the NEW joined roots, so that a site hardcoding
``"evidence/phase-4.5/tokens"`` instead of routing through TOKENS_ROOT
is caught as well as a residual ``"phase-4.5/tokens"``.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TOOLS = os.path.join(REPO_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

_TESTS = os.path.dirname(os.path.abspath(__file__))
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

# Import the strengthened matcher and helpers from the Chunk-1 judge.
from test_layout_paths import (  # noqa: E402
    _residual_phase_literals,
    _cfg,
    _require,
)

# ── Chunk-2 routed files (post-move locations) ───────────────────────────

ROUTED_PY_FILES = (
    "tools/sprint_loop/per_chunk.py",
    "tools/sprint_loop/config.py",
    "tools/sprint_loop/backends.py",
    "tools/orchestrate-review.py",
    "tools/phase-3.2-evidence/local_backend.py",
    "tools/sprint_loop/chunk_close_banner.py",
    "tools/sprint-loop.py",
    "tools/chunk_sequence_gate.py",
    "tools/sign_chunk_token.py",
)

FIRE_SCRIPT = "tools/phase-5-scripts/fire-design-review.sh"

# Old roots (catch residual old-layout references after the move) PLUS
# new roots (catch hardcoded new paths that should go through constants).
# The constant definitions in config.py are exempted by
# _constant_definition_nodes, and the individual os.path.join arguments
# ("evidence", "phase-4.5", "tokens") are separate Constants that do not
# contain the joined forbidden form, so this does not false-positive on
# the constants themselves.
_FORBIDDEN_SUBSTRINGS = (
    # Old layout — must not appear after the move
    "phase-4.5/tokens",
    "phase-4.5/build-evidence",
    "phase-4.5/prompts",
    "phase-1/scripts",
    "phase-1/locks",
    "phase-3.2/evidence",
    # New layout — must be routed through constants, not hardcoded
    "evidence/phase-4.5/tokens",
    "evidence/phase-4.5/build-evidence",
    "planning/phase-4.5/prompts",
    "tools/phase-1-scripts",
    "tools/phase-1-locks",
    "tools/phase-3.2-evidence",
)


def _skip_if_not_flipped():
    """Skip these Chunk-2 tests when the constants have NOT been flipped."""
    config = _cfg()
    if _require(config, "EVIDENCE_ROOT") == "":
        pytest.skip("constants not yet flipped; chunk-D1-2 has not run")


def test_chunk2_constants_have_flipped_values_and_resolve():
    """Chunk-2 §2.2 — constants have the new taxonomy values and resolve."""
    _skip_if_not_flipped()
    config = _cfg()

    assert _require(config, "EVIDENCE_ROOT") == "evidence"
    assert _require(config, "PLANNING_ROOT") == "planning"

    expected = {
        "TOKENS_ROOT": os.path.join("evidence", "phase-4.5", "tokens"),
        "PROMPTS_ROOT": os.path.join("planning", "phase-4.5", "prompts"),
        "SCRIPTS_ROOT": os.path.join("tools", "phase-1-scripts"),
        "LOCKS_ROOT": os.path.join("tools", "phase-1-locks"),
        "EVIDENCE_CODE_ROOT": os.path.join("tools", "phase-3.2-evidence"),
    }
    for name, want in expected.items():
        assert _require(config, name) == want, f"{name} != {want!r}"

    # All seven roots must resolve to existing directories.
    for name in ["EVIDENCE_ROOT", "PLANNING_ROOT"] + list(expected):
        composed = os.path.join(REPO_ROOT, getattr(config, name))
        assert os.path.isdir(composed), f"missing: {composed}"


def test_chunk2_phase_path_composes_new_paths():
    """Chunk-2 §2.2 — phase_path composes against the new root values."""
    _skip_if_not_flipped()
    config = _cfg()
    phase_path = _require(config, "phase_path")

    want_token = os.path.join(
        REPO_ROOT, "evidence", "phase-4.5", "tokens", "chunk-5a.token.json"
    )
    assert phase_path(REPO_ROOT, "tokens", "chunk-5a.token.json") == want_token
    assert os.path.isfile(want_token), f"missing: {want_token}"

    assert phase_path(REPO_ROOT, "scripts", "lock.py") == os.path.join(
        REPO_ROOT, "tools", "phase-1-scripts", "lock.py"
    )

    # The phase segment is embedded in the constant, so a phase= kwarg
    # must not exist.
    import inspect

    params = inspect.signature(phase_path).parameters
    assert "phase" not in params
    assert list(params)[0] == "framework_root"


def test_chunk2_no_residual_paths_in_moved_code():
    """Chunk-2 §4 — residual scan + shell wiring + bootstrap at new homes.

    Scans for both old-layout residuals (phase-N/... paths that should
    have moved) and new-layout hardcoded paths (evidence/... or tools/...
    that should go through constants, not appear as literals).
    """
    _skip_if_not_flipped()

    # --- routed Python files: residual scan with extended forbidden set ---
    failures: dict[str, list[str]] = {}
    for rel in ROUTED_PY_FILES:
        abs_path = os.path.join(REPO_ROOT, rel)
        assert os.path.isfile(abs_path), f"missing: {abs_path}"
        hits = _residual_phase_literals(abs_path, forbidden=_FORBIDDEN_SUBSTRINGS)
        if hits:
            failures[rel] = hits
    assert not failures, f"unrouted path literals in executable code: {failures}"

    # --- shell wiring at new location ---
    fire_abs = os.path.join(REPO_ROOT, FIRE_SCRIPT)
    assert os.path.isfile(fire_abs), f"missing: {fire_abs}"

    assert subprocess.run(
        ["bash", "-n", FIRE_SCRIPT], cwd=REPO_ROOT
    ).returncode == 0, "fire-design-review.sh failed bash -n"

    assert subprocess.run(
        [
            "bash",
            "-c",
            '. tools/sprint_loop/paths.sh && test -n "$PHASE5_SCRIPTS_ROOT" '
            '&& test -n "$BUILD_EVIDENCE_REL" '
            '&& test -f "$PHASE5_SCRIPTS_ROOT/envelope-manifest.py"',
        ],
        cwd=REPO_ROOT,
    ).returncode == 0, "paths.sh did not export usable shell roots"

    with open(fire_abs, "r", encoding="utf-8") as fh:
        fire_lines = fh.read().splitlines()

    assert any(
        '. "$REPO_ROOT/tools/sprint_loop/paths.sh"' in line for line in fire_lines
    ), "fire-design-review.sh does not source paths.sh via $REPO_ROOT"

    code_lines = [ln for ln in fire_lines if not ln.lstrip().startswith("#")]
    code = "\n".join(code_lines)

    assert "phase-4.5/build-evidence" not in code, "old build-evidence literal still in shell code"
    assert "phase-5/scripts" not in code, "old phase-5/scripts literal still in shell code"

    run_dir_lines = [ln for ln in code_lines if "RUN_DIR=" in ln]
    assert run_dir_lines, "no RUN_DIR assignment found"
    assert any("BUILD_EVIDENCE_REL" in ln for ln in run_dir_lines), "RUN_DIR does not use BUILD_EVIDENCE_REL"

    manifest_lines = [ln for ln in code_lines if "envelope-manifest.py" in ln]
    assert manifest_lines, "no envelope-manifest.py invocation found"
    assert any(
        "PHASE5_SCRIPTS_ROOT" in ln or "ENVELOPE_MANIFEST" in ln for ln in manifest_lines
    ), "envelope-manifest invocation does not use the shell root"

    # --- local_backend.py at new location, bootstrap still resolves ---
    lb_rel = "tools/phase-3.2-evidence/local_backend.py"
    lb_abs = os.path.join(REPO_ROOT, lb_rel)
    assert os.path.isfile(lb_abs), f"missing: {lb_abs}"

    proc = subprocess.run(
        [sys.executable, lb_rel, "--help"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    stderr = proc.stderr or ""

    assert "sprint_loop" not in stderr or not any(
        exc in stderr for exc in ("ModuleNotFoundError", "ImportError")
    ), f"sprint_loop bootstrap import failed to resolve:\n{stderr}"

    if sys.version_info >= (3, 10):
        assert proc.returncode == 0, (
            f"local_backend.py --help did not exit 0:\n{stderr}"
        )
    else:
        assert "TypeError" in stderr and "|" in stderr, (
            "on Python < 3.10 the only tolerated failure is the pre-existing "
            f"PEP-604 annotation TypeError; got:\n{stderr}"
        )

    with open(lb_abs, "r", encoding="utf-8") as fh:
        lb_tree = ast.parse(fh.read(), filename=lb_abs)

    def _imports_sprint_loop(node: ast.AST) -> bool:
        if isinstance(node, ast.ImportFrom):
            return bool(node.module and node.module.startswith("sprint_loop"))
        if isinstance(node, ast.Import):
            return any(a.name.startswith("sprint_loop") for a in node.names)
        return False

    module_level = [n for n in lb_tree.body if _imports_sprint_loop(n)]
    assert module_level, "local_backend.py has no module-level sprint_loop import"

    guarded = [
        n
        for n in ast.walk(lb_tree)
        if isinstance(n, ast.Try)
        for sub in ast.walk(n)
        if _imports_sprint_loop(sub)
    ]
    assert not guarded, "sprint_loop import is wrapped in try/except; must be unguarded"
