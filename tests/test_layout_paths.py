"""Judge tests for chunk-D1-1 (path-root constants + routing).

Authored and content-locked by the PLANNER before chunk-D1-1 opened.
The executor of chunk-D1-1 must NOT modify this file: it is the file
that grades that chunk's work, and framework invariant #3 forbids an
executor authoring its own judge. If an assertion here looks wrong,
the executor raises ``BLOCKED:`` to the planner rather than editing.

Implements CHUNK-1-SPEC.md §4.2 tests 1-3 exactly.

Matcher revision (planner, pre-chunk-D1-2): the original residual scan
had 5 blind spots — split-segment f-strings (D), bare-segment
concatenation (F), segments held in variables (I), os.sep.join with a
list arg (J), and PurePath constructors (L).  Chunk 1 was safe under
the weak scan because no files moved; a missed site still resolved.
Chunk 2 runs ``git mv``, so a missed site BREAKS.  The matcher is
strengthened here to close all 5 blind spots while preserving
false-positive control on the 6 legitimate telemetry-label sites.
Authored blind (before comparing with the builder's independent probe
at bd70d10); see the commit message for the comparison result.

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

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TOOLS = os.path.join(REPO_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)


def _skip_if_flipped():
    """Skip these Chunk-1 tests when chunk-D1-2 has flipped the constants.

    After the flip, EVIDENCE_ROOT is ``"evidence"`` (not ``""``), so the
    old value assertions and old file paths no longer hold.  The Chunk-2
    judge (tests/test_layout_paths_chunk2.py) covers the post-flip state.
    """
    config = _cfg()
    if _require(config, "EVIDENCE_ROOT") != "":
        pytest.skip("constants flipped by chunk-D1-2; see test_layout_paths_chunk2.py")

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
# check is scoped to path-construction contexts rather than applied to
# every bare segment in the file.

# pathlib constructors whose positional args are path segments.
_PATHLIKE_CONSTRUCTORS = frozenset({"PurePath", "Path", "PosixPath", "WindowsPath"})


def _eval_static_string(node: ast.AST) -> str | None:
    """Best-effort static evaluation of a string-producing expression.

    Returns the string value if *node* is a constant string, an f-string
    whose formatted values are themselves constant, or a ``+``
    concatenation of constant strings.  Returns ``None`` when the value
    cannot be determined at compile time (e.g. a variable, a non-constant
    formatted value, or a non-string expression).

    Recursive so nested concatenations and f-strings-inside-f-strings
    are handled.  When a FormattedValue's inner expression is
    non-constant, the inner value is treated as the empty string — the
    remaining literal parts are still concatenated, which is sufficient
    to catch a forbidden substring that lives entirely in the literal
    parts (the common split-segment f-string case).
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for val in node.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                parts.append(val.value)
            elif isinstance(val, ast.FormattedValue):
                inner = _eval_static_string(val.value)
                if inner is not None:
                    parts.append(inner)
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _eval_static_string(node.left)
        right = _eval_static_string(node.right)
        if left is not None and right is not None:
            return left + right
        return None
    return None


def _track_bare_segment_vars(tree: ast.AST) -> dict[str, str]:
    """Map variable names to bare-segment values they were assigned.

    Scans every ``Assign`` in the tree (module-level and function-level)
    for a target whose value is a string constant matching
    ``_BARE_SEGMENT``.  Returns ``{var_name: segment_value}``.

    Conservative by design: a variable that is ever assigned a bare
    segment is tracked, even if it is reassigned elsewhere.  This only
    matters when the variable is subsequently found in a
    path-construction context (check 2), so a label assignment that is
    never used in a path context produces no hit.
    """
    seg_vars: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        if not (isinstance(val, ast.Constant) and isinstance(val.value, str)
                and _BARE_SEGMENT.match(val.value)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                seg_vars[target.id] = val.value
    return seg_vars


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
    """ids of ALL nodes inside a module-level path-constant Assign.

    This is the mechanical exemption anchor. A by-name or by-line
    exemption would be the same drift-prone class as a line-keyed
    assertion, so structure is used instead.

    Collecting *all* node ids (not just Constants) means f-strings
    and concatenations that form a constant's value are also skipped
    by the forbidden-substring check, preventing a JoinedStr or
    BinOp(Add) inside a ``TOKENS_ROOT = ...`` definition from being
    double-flagged as a residual.
    """
    found: set[int] = set()
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not any(_is_constant_target(t, is_config_module) for t in targets):
            continue
        for sub in ast.walk(node.value):
            found.add(id(sub))
    return found


def _is_path_join_call(node: ast.AST) -> bool:
    """Is this a call to os.path.join / os.sep.join / posixpath.join?"""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return isinstance(func, ast.Attribute) and func.attr == "join"


def _is_pathlike_constructor(node: ast.AST) -> bool:
    """Is this a call to PurePath / Path / PosixPath / WindowsPath?"""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _PATHLIKE_CONSTRUCTORS
    )


def _check_arg_for_bare_segment(
    arg: ast.AST,
    seg_vars: dict[str, str],
    skip: set[int],
) -> list[str]:
    """Check one argument (or list/tuple element) for bare-segment hits.

    Handles three shapes:
      * ``ast.Constant`` — a literal bare segment (skip if inside a
        constant definition).
      * ``ast.Name`` — a variable that was tracked as holding a bare
        segment.
      * ``ast.List`` / ``ast.Tuple`` — descend into elements (needed
        for ``os.sep.join(["phase-1", "scripts"])`` where the segments
        sit in a list literal, not as direct call args).
    """
    if id(arg) in skip:
        return []
    hits: list[str] = []
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and _BARE_SEGMENT.match(arg.value):
        hits.append(f"line {arg.lineno}: bare segment {arg.value!r} in path composition")
    elif isinstance(arg, ast.Name) and arg.id in seg_vars:
        hits.append(
            f"line {arg.lineno}: bare segment {seg_vars[arg.id]!r} "
            f"(via variable {arg.id!r}) in path composition"
        )
    elif isinstance(arg, (ast.List, ast.Tuple)):
        for elt in arg.elts:
            hits.extend(_check_arg_for_bare_segment(elt, seg_vars, skip))
    return hits


def _bare_segment_hits_in_path_context(
    tree: ast.AST,
    seg_vars: dict[str, str],
    skip: set[int],
) -> list[str]:
    """Bare phase-dir segments used to CONSTRUCT a path.

    Covers five composition idioms:
      * ``os.path.join(root, "phase-1", "scripts", ...)``  -> Call args
      * ``os.sep.join(["phase-1", "scripts"])``            -> List elements
      * ``Path(root) / "phase-1" / "scripts"``             -> BinOp(Div)
      * ``PurePath(root, "phase-1", "scripts")``           -> Constructor args
      * ``seg = "phase-1"; os.path.join(root, seg, ...)``  -> Tracked variable

    Excludes bare segments used as labels, which is why the scan is
    context-scoped instead of matching every ``phase-N`` literal.
    """
    hits: list[str] = []

    for node in ast.walk(tree):
        if _is_path_join_call(node) or _is_pathlike_constructor(node):
            for arg in node.args:
                hits.extend(_check_arg_for_bare_segment(arg, seg_vars, skip))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            for side in (node.left, node.right):
                hits.extend(_check_arg_for_bare_segment(side, seg_vars, skip))

    return hits


def _residual_phase_literals(
    abs_path: str,
    forbidden: tuple[str, ...] = _FORBIDDEN_SUBSTRINGS,
) -> list[str]:
    """Executable-code string expressions still naming a phase dir.

    Comments never appear in the AST, which exempts them mechanically.
    Docstrings and the constant definitions themselves are skipped.

    Two complementary checks:

    (1) Forbidden-substring check — any string-producing expression
        whose static value contains a joined forbidden path (e.g.
        ``"phase-1/scripts"``, ``f"{root}/phase-4.5/tokens"``,
        ``"phase-1" + "/scripts"``).  Covers plain literals (B),
        static f-strings (C), split-segment f-strings (D),
        concatenations (E, F), percent-format (G), and .format() (H).

    (2) Bare-segment-in-path-context check — a bare ``"phase-N"``
        literal or a variable holding one, found inside a
        path-construction call or operator.  Covers os.path.join
        args (A), pathlib ``/`` (K), os.sep.join list elements (J),
        PurePath constructor args (L), and tracked variables (I).
    """
    with open(abs_path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=abs_path)

    is_config_module = os.path.basename(abs_path) == "config.py"
    skip = _docstring_nodes(tree) | _constant_definition_nodes(tree, is_config_module)
    seg_vars = _track_bare_segment_vars(tree)

    hits: list[str] = []

    # (1) string expressions whose static value contains a forbidden
    #     joined path.  Extended beyond plain Constants to f-strings
    #     (JoinedStr) and + concatenations (BinOp.Add) so that
    #     split-segment and concat idioms are caught.
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if id(node) in skip or not isinstance(node.value, str):
                continue
            if any(bad in node.value for bad in forbidden):
                hits.append(f"line {node.lineno}: {node.value!r}")
        elif isinstance(node, ast.JoinedStr):
            if id(node) in skip:
                continue
            val = _eval_static_string(node)
            if val is not None and any(bad in val for bad in forbidden):
                hits.append(f"line {node.lineno}: f-string evaluates to {val!r}")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if id(node) in skip:
                continue
            val = _eval_static_string(node)
            if val is not None and any(bad in val for bad in forbidden):
                hits.append(f"line {node.lineno}: concat evaluates to {val!r}")

    # (2) bare segments (or variables holding them) inside
    #     path-construction contexts.
    hits.extend(_bare_segment_hits_in_path_context(tree, seg_vars, skip))

    # (3) bare segments in + concatenation chains.
    #     Catches ``root + "phase-1" + "scripts"`` where check 1 cannot
    #     fold the full value (root is non-constant) and check 2 does
    #     not treat BinOp(Add) as a path-construction call.  The
    #     segment may carry leading/trailing slashes (``"/phase-1"``)
    #     so the match is against the slash-stripped value.
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Add):
            continue
        if id(node) in skip:
            continue
        for side in (node.left, node.right):
            if id(side) in skip:
                continue
            if isinstance(side, ast.Name):
                if side.id in seg_vars:
                    hits.append(
                        f"line {node.lineno}: bare segment "
                        f"{seg_vars[side.id]!r} (via variable "
                        f"{side.id!r}) in concat"
                    )
            else:
                val = _eval_static_string(side)
                if val is not None and _BARE_SEGMENT.match(val.strip("/")):
                    hits.append(
                        f"line {node.lineno}: bare segment {val!r} in concat"
                    )

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
    _skip_if_flipped()
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
    _skip_if_flipped()
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
    _skip_if_flipped()
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
    proc = subprocess.run(
        [sys.executable, lb_rel, "--help"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    stderr = proc.stderr or ""

    # The bootstrap must RESOLVE. This is the assertion that matters: if
    # sys.path handling or the module name were wrong, the failure would
    # name sprint_loop, and it must not.
    assert "sprint_loop" not in stderr or not any(
        exc in stderr for exc in ("ModuleNotFoundError", "ImportError")
    ), f"sprint_loop bootstrap import failed to resolve:\n{stderr}"

    # Exit 0 is asserted only where the interpreter can actually reach
    # argparse. local_backend.py carries a PRE-EXISTING PEP-604
    # annotation (``-> dict | None``) that raises TypeError at def-time
    # under Python < 3.10, so on 3.9 this module cannot exit 0 for
    # reasons unrelated to layout routing. Asserting exit 0
    # unconditionally made this an UNSATISFIABLE assertion; it went
    # unnoticed because the test failed earlier, on the unrouted sites,
    # so this line was never evaluated while the suite was RED. Recorded
    # as a known issue in phase-4.5/LEDGER.md.
    if sys.version_info >= (3, 10):
        assert proc.returncode == 0, (
            f"local_backend.py --help did not exit 0:\n{stderr}"
        )
    else:
        assert "TypeError" in stderr and "|" in stderr, (
            "on Python < 3.10 the only tolerated failure is the pre-existing "
            f"PEP-604 annotation TypeError; got:\n{stderr}"
        )

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
