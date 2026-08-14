"""Judge tests for chunk-D1-2a (repair the four evidence-relative scripts).

Authored by the PLANNER before chunk-D1-2a opens; its content hash is
ratified by the REFEREE before it locks, because the planner and the builder
now share a model family. The executor of chunk-D1-2a must NOT modify this
file — framework invariant #3. If an assertion looks wrong, the executor
raises ``BLOCKED:`` to the planner rather than editing.

These tests are deliberately **side-effect free**. The scripts under test
write to ``telemetry/runs.jsonl``, which is the system of record; a judge
that executes them to observe rc=0 would mutate the artifact it is judging.
Per §7, rc=0 is an exit code, not evidence. So the assertions target the
thing that actually broke — *path resolution* — by resolving each script's
roots and checking they land on real directories, plus one genuine
subprocess run of the only script with a ``--dry-run`` mode.

This design is what closes builder finding 6.5: a partial fix of
``reconstruct-telemetry.py`` that repairs ``:31-32`` but leaves ``:29``
still exits 0 and emits no stale ``envelope_path``, while silently writing a
truncated fork of the SoR to ``tools/telemetry/runs.jsonl``. An rc-based
judge cannot see that. ``test_chunk2a_runs_path_is_the_real_sor`` can.

Two distinct defect classes are covered, and they need different probes:

* **Wrong depth** (``gen-telemetry.py`` x2, ``reconstruct-telemetry.py``):
  roots are built from ``__file__``, so they are already CWD-independent —
  they are simply wrong, resolving one level short of the framework root now
  that the scripts live under ``tools/``. Probed by resolving them.
* **CWD-relative** (``gen-findings.py``): literal paths passed to ``open()``
  resolve against the invoking directory. Probed statically via AST, because
  the module has no ``if __name__ == "__main__"`` guard and importing it
  would execute it.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TOOLS = os.path.join(REPO_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

_TESTS = os.path.dirname(os.path.abspath(__file__))
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from test_layout_paths import _cfg, _require  # noqa: E402

# ── Subjects ─────────────────────────────────────────────────────────────

# Scripts whose path roots are top-level constants derived from __file__.
# All three have a __main__ guard, so importing them is side-effect free.
_ROOT_CONSTANT_SCRIPTS = {
    "tools/phase-3-gen/gen-telemetry.py": ("EVID",),
    "tools/phase-3.1-gen/gen-telemetry.py": ("EVID",),
    "tools/phase-4-gen/reconstruct-telemetry.py": ("PHASE2_EVID", "PHASE3_EVID"),
}

# Scripts that write the telemetry system of record, and the constant naming
# the destination. A wrong root here forks the SoR instead of failing.
_SOR_WRITERS = {
    "tools/phase-3-gen/gen-telemetry.py": "OUT",
    "tools/phase-3.1-gen/gen-telemetry.py": "RUNS",
    "tools/phase-4-gen/reconstruct-telemetry.py": "RUNS_PATH",
}

# No __main__ guard — never import. AST only.
_UNGUARDED = "tools/phase-4-gen/gen-findings.py"

_ALL_SUBJECTS = tuple(_ROOT_CONSTANT_SCRIPTS) + (_UNGUARDED,)

# The one true telemetry system of record.
_SOR_REL = os.path.join("telemetry", "runs.jsonl")


def _load(rel: str):
    """Import a guarded script by path and return its module object."""
    abs_path = os.path.join(REPO_ROOT, rel)
    assert os.path.isfile(abs_path), f"missing subject: {abs_path}"
    name = "judge2a_" + rel.replace("/", "_").replace(".", "_").replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, abs_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree(rel: str) -> ast.Module:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=rel)


def _string_constants(rel: str) -> list[str]:
    return [
        node.value
        for node in ast.walk(_tree(rel))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


# ── §2.1 — read roots resolve to real directories ────────────────────────


@pytest.mark.parametrize("rel", sorted(_ROOT_CONSTANT_SCRIPTS))
def test_chunk2a_evidence_roots_resolve_to_existing_dirs(rel):
    """§2.1 — each script's evidence root points at a directory that exists.

    This is the regression itself. Pre-fix, ``gen-telemetry.py``'s ``EVID``
    is ``tools/phase-3-gen/build-evidence`` (the sibling it used to have)
    and ``reconstruct-telemetry.py``'s roots hang off ``tools/`` because
    ``:29`` walks up one level too few. Asserting existence rather than a
    literal string keeps this from re-breaking on the next move.
    """
    module = _load(rel)
    for const in _ROOT_CONSTANT_SCRIPTS[rel]:
        assert hasattr(module, const), f"{rel}: {const} no longer defined"
        resolved = os.path.realpath(getattr(module, const))
        assert os.path.isdir(resolved), f"{rel}: {const} -> {resolved} (not a dir)"
        # Must land inside evidence/, not under tools/.
        assert not resolved.startswith(
            os.path.realpath(_TOOLS) + os.sep
        ), f"{rel}: {const} resolves under tools/ -> {resolved}"


def test_chunk2a_runs_path_is_the_real_sor():
    """§4.7 — the SoR destination is the real file, not a fork.

    Closes builder finding 6.5. A partial fix that repairs the read roots
    but leaves the framework root wrong sends writes to
    ``tools/telemetry/runs.jsonl``: the merge guard then reads zero existing
    rows and the truncating write produces a plausible-looking file with the
    history silently dropped. rc stays 0 throughout.
    """
    want = os.path.realpath(os.path.join(REPO_ROOT, _SOR_REL))
    assert os.path.isfile(want), f"SoR missing: {want}"

    for rel, const in sorted(_SOR_WRITERS.items()):
        module = _load(rel)
        assert hasattr(module, const), f"{rel}: {const} no longer defined"
        got = os.path.realpath(getattr(module, const))
        assert got == want, f"{rel}: {const} -> {got}, expected the SoR at {want}"


def test_chunk2a_no_forked_telemetry_dir_on_disk():
    """§4.7 — ``tools/telemetry/`` must not come into existence."""
    forked = os.path.join(_TOOLS, "telemetry")
    assert not os.path.exists(forked), (
        f"forked telemetry tree present: {forked} — a partial path fix wrote "
        "the system of record to the wrong root"
    )


def test_chunk2a_sor_is_not_empty():
    """§4.7 — the SoR has rows, so a truncating write is detectable.

    If this file is ever empty, the non-shrinking check in §4.7 becomes
    vacuous and a dropped-history bug passes unnoticed.
    """
    with open(os.path.join(REPO_ROOT, _SOR_REL), encoding="utf-8") as fh:
        rows = [ln for ln in fh if ln.strip()]
    assert len(rows) > 0, "telemetry SoR is empty; §4.7 row-count check is vacuous"


# ── §2.1 — envelope_path write strings ───────────────────────────────────


@pytest.mark.parametrize("rel", sorted(_ALL_SUBJECTS))
def test_chunk2a_no_stale_phase_prefix_literals(rel):
    """§2.1 — no ``phase-N/...`` path literal survives in these scripts.

    The read-path fix and the ``envelope_path`` write-string fix must land
    together: repairing reads alone turns a loud FileNotFoundError into
    telemetry rows carrying pointers to files that no longer exist there.
    Docstrings are excluded — prose may narrate history (§ Chunk 3 rules
    living-doc citations, not code).
    """
    doc_strings = set()
    for node in ast.walk(_tree(rel)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                doc_strings.add(doc)

    hits = [
        s
        for s in _string_constants(rel)
        if s not in doc_strings and _looks_like_stale_phase_path(s)
    ]
    assert not hits, f"{rel}: stale phase-prefixed path literals: {hits}"


def _looks_like_stale_phase_path(value: str) -> bool:
    """True for a path-shaped literal beginning with a bare ``phase-N`` segment.

    ``phase-3/build-evidence/`` matches. ``evidence/phase-3/build-evidence``
    does not — that one is correctly rooted. A bare ``phase-3`` with no
    separator is not path-shaped and does not match, so ``os.path.join``
    segment arguments stay legal.
    """
    if "/" not in value:
        return False
    head = value.split("/", 1)[0]
    if not head.startswith("phase-"):
        return False
    tail = head[len("phase-") :]
    return bool(tail) and all(ch.isdigit() or ch == "." for ch in tail)


# ── §2.1 — gen-findings.py CWD independence ──────────────────────────────


def test_chunk2a_gen_findings_has_no_cwd_relative_opens():
    """§2.1 — every literal path handed to ``open()`` is anchored.

    ``gen-findings.py`` has no ``__main__`` guard, so it is never imported
    here. Its defect class is different from the other three: the paths are
    literals inside functions, resolved against the invoking directory. A
    relative literal is the defect regardless of what the string says.
    """
    offenders = []
    for node in ast.walk(_tree(_UNGUARDED)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_open = (isinstance(func, ast.Name) and func.id == "open") or (
            isinstance(func, ast.Attribute) and func.attr == "open"
        )
        if not is_open or not node.args:
            continue
        first = node.args[0]
        # A bare literal, or an f-string whose leading piece is a literal,
        # both resolve against the CWD.
        literal = None
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            literal = first.value
        elif isinstance(first, ast.JoinedStr) and first.values:
            lead = first.values[0]
            if isinstance(lead, ast.Constant) and isinstance(lead.value, str):
                literal = lead.value
        if literal is not None and not os.path.isabs(literal):
            offenders.append((getattr(node, "lineno", "?"), literal))

    assert not offenders, (
        f"{_UNGUARDED}: CWD-relative open() paths at {offenders} — anchor them to "
        "the framework root via the sprint_loop.config roots"
    )


# ── §2.1 — real execution, the one script that can do it safely ──────────


def test_chunk2a_reconstruct_telemetry_dry_run_from_foreign_cwd():
    """§4.2 — ``reconstruct-telemetry.py --dry-run`` succeeds off-root.

    The only subject with a no-write mode, so the only one a judge can
    honestly execute. Run from a temp directory: a script that resolves its
    own roots correctly does not care where it was invoked from.
    """
    script = os.path.join(REPO_ROOT, "tools/phase-4-gen/reconstruct-telemetry.py")
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, script, "--dry-run"],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
    assert proc.returncode == 0, (
        f"rc={proc.returncode} from a foreign CWD\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    # A dry run that reports zero existing rows means the merge guard read
    # the wrong file — the silent half of finding 6.5.
    assert "0 existing rows" not in proc.stdout, (
        "dry run read zero existing rows; the merge guard is pointed at the "
        f"wrong path\nstdout:\n{proc.stdout}"
    )


# ── §2.2 — stale test fixture ────────────────────────────────────────────


def test_chunk2a_sprint_loop_fixture_uses_taxonomy_roots():
    """§2.2 — the ``test_sprint_loop.py`` fixture builds real root shapes.

    The fixture created ``fw/phase-1/scripts`` and ``fw/phase-3.2/evidence``,
    which nothing reads — ``_validate_config`` only requires
    ``tools/sprint_loop``, so the test passed while asserting nothing. Point
    the mkdirs at the taxonomy homes so the fixture matches the layout the
    rest of the suite enforces.
    """
    config = _cfg()
    scripts_root = _require(config, "SCRIPTS_ROOT")
    evidence_code_root = _require(config, "EVIDENCE_CODE_ROOT")

    path = os.path.join(REPO_ROOT, "tests", "test_sprint_loop.py")
    with open(path, encoding="utf-8") as fh:
        source = fh.read()

    for stale in ("phase-1", "scripts"), ("phase-3.2", "evidence"):
        assert (
            os.path.join(*stale) not in source
        ), f"stale fixture path {os.path.join(*stale)!r} still in test_sprint_loop.py"

    for root in (scripts_root, evidence_code_root):
        assert root in source, f"fixture does not build {root!r}"
