"""Judge tests for chunk-D1-1 (path-root constants + routing).

Authored and content-locked by the PLANNER before chunk-D1-1 opened.
The executor of chunk-D1-1 must NOT modify this file: it is the file
that grades that chunk's work, and framework invariant #3 forbids an
executor authoring its own judge. If an assertion here looks wrong,
the executor raises ``BLOCKED:`` to the planner rather than editing.

Implements CHUNK-1-SPEC.md §4.2 tests 1-3 exactly.

Every path is resolved from this file's own location, never from the
process CWD. The constants under test are relative segments by design
and pytest's CWD is the invocation directory, not rootdir, so a
CWD-relative assertion would false-fail when the suite runs from
anywhere but the repo root. Commit 7179934 ("portability: make the
suite pass from any clone") established CWD-independence as a
property of this suite.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TOOLS = os.path.join(REPO_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

def _cfg():
    """Import the config module lazily.

    Deliberately NOT a module-level ``from ... import`` of the
    constants: before chunk-D1-1 lands they do not exist, and an
    ImportError at module scope is a pytest *collection* error, which
    interrupts the entire suite and denies the executor a baseline.
    Resolving inside each test turns the pre-state into three clean
    assertion failures alongside 194 passing tests.
    """
    import sprint_loop.config as config

    return config


def _require(config, name):
    assert hasattr(config, name), f"sprint_loop.config has no {name} (CHUNK-1-SPEC §2.1)"
    return getattr(config, name)

CONSTANT_NAMES = {
    "EVIDENCE_ROOT",
    "PLANNING_ROOT",
    "TOKENS_ROOT",
    "PROMPTS_ROOT",
    "SCRIPTS_ROOT",
    "LOCKS_ROOT",
    "EVIDENCE_CODE_ROOT",
}

# CHUNK-1-SPEC §2.2 + §2.3 routed files, repo-relative.
ROUTED_PY_FILES = (
    "tools/sprint_loop/per_chunk.py",
    "tools/sprint_loop/config.py",
    "tools/sprint_loop/backends.py",
    "tools/orchestrate-review.py",
    "phase-3.2/evidence/local_backend.py",
    "tools/sprint_loop/chunk_close_banner.py",
    "tools/sprint-loop.py",
    "tools/chunk_sequence_gate.py",
    "tools/sign_chunk_token.py",
)

FIRE_SCRIPT = "phase-5/scripts/fire-design-review.sh"

# Exactly the prefixes the §2.1 constants own. Deliberately NOT a broad
# "phase-\d" match: paths like phase-4.5/KNOWN-ISSUES.md and
# phase-4.5/PLAN.md are documents with no constant to route through, so
# flagging them would make this test unsatisfiable without widening the
# constant set beyond CHUNK-1-SPEC's scope.
_FORBIDDEN_SUBSTRINGS = (
    "phase-4.5/tokens",
    "phase-4.5/build-evidence",
    "phase-4.5/prompts",
    "phase-1/scripts",
    "phase-1/locks",
    "phase-3.2/evidence",
)

# A bare phase-dir segment, e.g. "phase-1" or "phase-4.5". These appear as
# SEPARATE ast.Constant nodes in os.path.join(root, "phase-1", "scripts"),
# so a substring test against the joined form above cannot see them —
# "phase-1/scripts" in "phase-1" is False. That blindness would silently
# pass all seven per_chunk.py sites, which are the bulk of §2.2.
_BARE_SEGMENT = re.compile(r"^phase-\d+(?:\.\d+)?$")

# Bare segments are only a defect in PATH-CONSTRUCTION context. The same
# literal is legitimate as a telemetry/HMAC label (per_chunk.py:287,
# backends.py:197-198, sprint-loop.py:268,422,483, orchestrate-review.py:459),
# which CHUNK-1-SPEC §2.2 explicitly excludes from the inventory. So the
# check is scoped to os.path.join arguments and pathlib / operands rather
# than applied to every bare segment in the file.


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """ids of Expr nodes that are docstrings (module/class/function)."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    found.add(id(body[0].value))
    return found


def _is_constant_target(name: str, is_config_module: bool) -> bool:
    """Is a module-level assignment target a path-constant definition?

    In ``config.py`` — the designated single source of truth for path
    roots — any module-level ALL-CAPS assignment is a definition. This
    deliberately admits *derived* constants the executor must introduce
    that are not among the seven §2.1 names. The motivating case:
    ``EVIDENCE_ROOT`` is ``""`` today, so an f-string like
    ``f"{EVIDENCE_ROOT}/phase-4.5/build-evidence"`` renders a leading
    slash and changes ``--help`` bytes, which forces a derived
    ``BUILD_EVIDENCE_REL`` segment constant. Enumerating such names in
    advance would make this test a guessing game about the executor's
    factoring.

    Everywhere else the strict seven-name set applies: outside
    ``config.py`` a path literal is a residual, not a definition.
    """
    if is_config_module:
        return name.isupper() and not name.startswith("_")
    return name in CONSTANT_NAMES


def _constant_definition_nodes(tree: ast.AST, is_config_module: bool) -> set[int]:
    """ids of Constant nodes inside a module-level path-constant Assign.

    This is the mechanical exemption anchor. A by-name or by-line
    exemption would be the same drift-prone class as a line-keyed
    assertion, so structure is used instead.
    """
    found: set[int] = set()
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not any(_is_constant_target(t, is_config_module) for t in targets):
            continue
        for sub in ast.walk(node.value):
            if isinstance(sub, ast.Constant):
                found.add(id(sub))
    return found


def _is_path_join_call(node: ast.AST) -> bool:
    """Is this a call to os.path.join / os.path.sep.join / posixpath.join?"""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return isinstance(func, ast.Attribute) and func.attr == "join"


def _bare_segment_constants_in_path_context(tree: ast.AST) -> list[ast.Constant]:
    """Bare phase-dir segments used to CONSTRUCT a path.

    Covers the two composition idioms in this repo:
      * ``os.path.join(root, "phase-1", "scripts", ...)``  -> Call args
      * ``Path(root) / "phase-1" / "scripts"``             -> BinOp(Div)

    Excludes bare segments used as labels, which is why the scan is
    context-scoped instead of matching every ``phase-N`` literal.
    """
    found: list[ast.Constant] = []

    for node in ast.walk(tree):
        if _is_path_join_call(node):
            for arg in node.args:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and _BARE_SEGMENT.match(arg.value)
                ):
                    found.append(arg)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            for side in (node.left, node.right):
                if (
                    isinstance(side, ast.Constant)
                    and isinstance(side.value, str)
                    and _BARE_SEGMENT.match(side.value)
                ):
                    found.append(side)

    return found


def _residual_phase_literals(abs_path: str) -> list[str]:
    """Executable-code string literals still naming a phase dir.

    Comments never appear in the AST, which exempts them mechanically.
    Docstrings and the constant definitions themselves are skipped.
    """
    with open(abs_path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=abs_path)

    is_config_module = os.path.basename(abs_path) == "config.py"
    skip = _docstring_nodes(tree) | _constant_definition_nodes(tree, is_config_module)

    hits: list[str] = []

    # (1) literals that already contain a joined path, e.g. help text and
    #     "phase-1/scripts/verify-green.py"
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or id(node) in skip:
            continue
        if not isinstance(node.value, str):
            continue
        if any(bad in node.value for bad in _FORBIDDEN_SUBSTRINGS):
            hits.append(f"line {node.lineno}: {node.value!r}")

    # (2) bare segments passed into a path composition
    for node in _bare_segment_constants_in_path_context(tree):
        if id(node) in skip:
            continue
        hits.append(f"line {node.lineno}: bare segment {node.value!r} in path composition")

    return sorted(set(hits))


def test_path_root_constants_have_expected_values_and_exist():
    """§4.2 test 1 — exact segment values, plus existence where meaningful.

    The value assertions carry the weight. ``os.path.join(root, "")``
    returns ``root + os.sep``, so an isdir() check on the two empty
    roots is unconditionally true: it would pass if those constants
    held the wrong value or were silently emptied, and it would grow
    stronger after Chunk 2's flip. Existence is corroboration only,
    and only for the five non-empty roots.
    """
    config = _cfg()

    assert _require(config, "EVIDENCE_ROOT") == ""
    assert _require(config, "PLANNING_ROOT") == ""

    expected = {
        "TOKENS_ROOT": os.path.join("phase-4.5", "tokens"),
        "PROMPTS_ROOT": os.path.join("phase-4.5", "prompts"),
        "SCRIPTS_ROOT": os.path.join("phase-1", "scripts"),
        "LOCKS_ROOT": os.path.join("phase-1", "locks"),
        "EVIDENCE_CODE_ROOT": os.path.join("phase-3.2", "evidence"),
    }
    for name, want in expected.items():
        assert _require(config, name) == want, f"{name} != {want!r}"

    for name in expected:
        composed = os.path.join(REPO_ROOT, getattr(config, name))
        assert os.path.isdir(composed), f"missing: {composed}"


def test_phase_path_helper_signature_and_composition():
    """§4.2 test 2 — framework_root is positional; there is no phase= kwarg."""
    config = _cfg()
    phase_path = _require(config, "phase_path")

    want_token = os.path.join(REPO_ROOT, "phase-4.5", "tokens", "chunk-5a.token.json")
    assert phase_path(REPO_ROOT, "tokens", "chunk-5a.token.json") == want_token
    assert os.path.isfile(want_token), f"missing: {want_token}"

    assert phase_path(REPO_ROOT, "scripts", "lock.py") == os.path.join(
        REPO_ROOT, "phase-1", "scripts", "lock.py"
    )

    # The phase segment is embedded in the constant, so a phase= kwarg
    # must not exist.
    import inspect

    params = inspect.signature(phase_path).parameters
    assert "phase" not in params
    assert list(params)[0] == "framework_root"


def test_no_residual_hardcoded_phase_paths_in_routed_code():
    """§4.2 test 3 — AST-scoped residual scan + shell wiring + bootstrap shape.

    Not line-keyed: line-keyed assertions read the wrong lines once the
    executor's edits shift them, letting a missed site pass silently.
    This is the chunk's only anti-missed-site check.
    """
    # --- main body: routed Python files, executable code only ---
    failures: dict[str, list[str]] = {}
    for rel in ROUTED_PY_FILES:
        abs_path = os.path.join(REPO_ROOT, rel)
        assert os.path.isfile(abs_path), f"missing: {abs_path}"
        hits = _residual_phase_literals(abs_path)
        if hits:
            failures[rel] = hits
    assert not failures, f"unrouted phase literals in executable code: {failures}"

    # --- 3a: shell residuals + real source line ---
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

    # Comment lines carry phase- literals in the header and usage block
    # (:8, :34-36) which §2.4 does not put in the edit surface, so only
    # executable lines are scanned.
    code_lines = [ln for ln in fire_lines if not ln.lstrip().startswith("#")]
    code = "\n".join(code_lines)

    assert "phase-4.5/build-evidence" not in code, "build-evidence literal still in shell code"
    assert "phase-5/scripts" not in code, "phase-5/scripts literal still in shell code"

    run_dir_lines = [ln for ln in code_lines if "RUN_DIR=" in ln]
    assert run_dir_lines, "no RUN_DIR assignment found"
    assert any("BUILD_EVIDENCE_REL" in ln for ln in run_dir_lines), "RUN_DIR does not use BUILD_EVIDENCE_REL"

    manifest_lines = [ln for ln in code_lines if "envelope-manifest.py" in ln]
    assert manifest_lines, "no envelope-manifest.py invocation found"
    assert any(
        "PHASE5_SCRIPTS_ROOT" in ln or "ENVELOPE_MANIFEST" in ln for ln in manifest_lines
    ), "envelope-manifest invocation does not use the shell root"

    # --- 3b: local_backend.py runs, with an UNGUARDED module-level import ---
    lb_rel = "phase-3.2/evidence/local_backend.py"
    lb_abs = os.path.join(REPO_ROOT, lb_rel)
    assert subprocess.run(
        [sys.executable, lb_rel, "--help"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0, "local_backend.py --help did not exit 0"

    # Exit 0 alone is insufficient: a lazy import inside main(), or a
    # try/except ImportError with a hardcoded fallback, also exits 0 and
    # fails only at sprint runtime.
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
