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
* **CWD-relative** (``gen-findings.py``): paths passed to ``open()``
  resolve against the invoking directory. Probed both statically (every
  ``open()`` argument must derive from an anchored root) and behaviourally
  (the script runs from a foreign CWD under the write-intercepting probe).

**Amendment, ratified after the chunk-D1-2a code gate.** kimi-k3 constructed
three partial fixes that the first-ratified judge certified green, each
against an assertion that tested a *proxy* for the property instead of the
property: an AST scan for ``phase-N/`` literals (defeated by dropping the
prefix entirely and emitting ``build-evidence/<file>``, well-formed and
resolving to nothing), an AST scan for literal ``open()`` arguments (defeated
by ``os.path.join("evidence", "phase-3.2", ...)``, a Call node rather than a
literal, still CWD-relative), and ``"LOCKS_ROOT" in ast.unparse(default)``
(defeated by ``os.path.join(_FRAMEWORK_ROOT, "LOCKS_ROOT")``, the quoted
constant name). All three are now asserted behaviourally. The planner had
recorded an erratum in spec §3 claiming a side-effect-free judge could not
observe emitted ``envelope_path`` values at all; that erratum is wrong and is
superseded here. It is the *write* that must not happen, not the run — see
:data:`_PROBE_SRC`.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
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
    assert spec is not None, f"could not build an import spec for {rel}"
    assert spec.loader is not None, f"import spec for {rel} has no loader"
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


# ── Write-intercepting probe ─────────────────────────────────────────────

# Executes a subject for real, from a foreign CWD, with ``builtins.open``
# replaced so that write modes return an in-memory sink: every byte the script
# would have written is captured instead of reaching disk. This is what makes
# behavioural assertions about *emitted values* legal in a judge that must not
# mutate the artifact under review.
#
# Verified against all four subjects before this harness was written: each
# performs every read before its first write, and none calls ``os.makedirs``,
# ``os.replace``, or anything from ``shutil``, so no write escapes the
# intercept. If a subject ever gains one, this probe stops being sufficient and
# the planner must be told — do not weaken the assertions to compensate.
_PROBE_SRC = r'''
import builtins, io, json, os, runpy, sys

script, outpath = sys.argv[1], sys.argv[2]
# The subjects that inspect argv must see their own, not the harness's.
sys.argv = [script]

_real_open = builtins.open
reads, writes = [], {}


class _Sink(io.StringIO):
    """Collects what would have been written, keyed by path."""

    def __init__(self, path):
        io.StringIO.__init__(self)
        self._path = path

    def close(self):
        writes[self._path] = self.getvalue()
        io.StringIO.close(self)

    def __exit__(self, *exc):
        self.close()
        return False


def _probe_open(file, mode="r", *args, **kwargs):
    path = os.fspath(file)
    if any(ch in mode for ch in "wax+"):
        return _Sink(path)
    reads.append(path)
    return _real_open(file, mode, *args, **kwargs)


builtins.open = _probe_open
error = None
try:
    runpy.run_path(script, run_name="__main__")
except BaseException as exc:  # noqa: BLE001 — reported to the judge, not raised
    error = "%s: %s" % (type(exc).__name__, exc)
finally:
    builtins.open = _real_open

with _real_open(outpath, "w") as fh:
    json.dump({"error": error, "reads": reads, "writes": writes}, fh)
'''


def _probe(rel: str) -> dict:
    """Run a subject with writes captured. Returns error/reads/writes."""
    script = os.path.join(REPO_ROOT, rel)
    assert os.path.isfile(script), f"missing subject: {script}"
    with tempfile.TemporaryDirectory() as tmp:
        harness = os.path.join(tmp, "_probe.py")
        out = os.path.join(tmp, "_probe.json")
        with open(harness, "w", encoding="utf-8") as fh:
            fh.write(_PROBE_SRC)
        proc = subprocess.run(
            [sys.executable, harness, script, out],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0 and os.path.isfile(out), (
            f"probe harness failed for {rel} (rc={proc.returncode})\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)


def _emitted_rows(result: dict) -> list[dict]:
    """Every JSONL row the subject would have written."""
    rows = []
    for _, content in sorted(result["writes"].items()):
        for line in content.splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _sor_envelope_paths() -> set[str]:
    """``envelope_path`` values already recorded in the SoR.

    Used to separate rows a subject *generated* from rows it *carried through*
    from the existing file. Absent SoR (fresh clone, gitignored per
    ``.gitignore:44``) yields an empty set, which is correct: with nothing to
    read, every emitted row is generated.
    """
    path = os.path.join(REPO_ROOT, _SOR_REL)
    if not os.path.isfile(path):
        return set()
    values = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "envelope_path" in row:
                values.add(row["envelope_path"])
    return values


def _anchored_names(rel: str) -> set[str]:
    """Module-level names whose value derives from the framework root.

    Computed rather than hardcoded, so renaming a root constant does not
    silently widen what counts as anchored. A small fixpoint covers the
    ``_FRAMEWORK_ROOT`` -> ``_P32_REVIEWS`` -> derived chains in these scripts.
    """
    anchored = {"_FRAMEWORK_ROOT", "REPO_ROOT"}
    body = _tree(rel).body
    for _ in range(4):
        for node in body:
            if not isinstance(node, ast.Assign):
                continue
            src = ast.unparse(node.value)
            if "phase_path" in src or any(name in src for name in anchored):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        anchored.add(target.id)
    return anchored


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
        assert not resolved.startswith(os.path.realpath(_TOOLS) + os.sep), (
            f"{rel}: {const} resolves under tools/ -> {resolved}"
        )


def test_chunk2a_runs_path_is_the_real_sor():
    """§4.7 — the SoR destination is the real file, not a fork.

    Closes builder finding 6.5. A partial fix that repairs the read roots
    but leaves the framework root wrong sends writes to
    ``tools/telemetry/runs.jsonl``: the merge guard then reads zero existing
    rows and the truncating write produces a plausible-looking file with the
    history silently dropped. rc stays 0 throughout.
    """
    want = os.path.realpath(os.path.join(REPO_ROOT, _SOR_REL))
    if not os.path.isfile(want):
        pytest.skip(
            f"no {_SOR_REL} in this tree, so there is no SoR to check the "
            "writer constants against; the SoR is gitignored and absent on "
            "a fresh clone (spec §4.7)"
        )

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
    path = os.path.join(REPO_ROOT, _SOR_REL)
    if not os.path.isfile(path):
        pytest.skip(
            f"no {_SOR_REL} in this tree, so there is no SoR to check for "
            "rows; the SoR is gitignored and absent on a fresh clone (spec §4.7)"
        )
    with open(path, encoding="utf-8") as fh:
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


@pytest.mark.parametrize("rel", sorted(_SOR_WRITERS))
def test_chunk2a_emitted_envelope_paths_resolve(rel):
    """§3 assertion 2 — every emitted ``envelope_path`` resolves on disk.

    Closes kimi-k3 blocker 1. Shape is not the property. A fix that removes
    the dead ``phase-N/`` prefix without adding the real root emits
    ``build-evidence/<file>``: it matches no stale-prefix pattern, satisfies
    :func:`test_chunk2a_no_stale_phase_prefix_literals`, and points at
    nothing. That mutation was demonstrated 16/16 green against the
    first-ratified judge, which is why this assertion exists.

    A well-formed pointer to a file that is not there is worse than the
    ``FileNotFoundError`` this chunk repaired: the row lands in the telemetry
    record and reads as evidence.
    """
    result = _probe(rel)
    assert result["error"] is None, f"{rel} raised under the probe: {result['error']}"

    emitted = [row["envelope_path"] for row in _emitted_rows(result) if "envelope_path" in row]
    assert emitted, (
        f"{rel} emitted no envelope_path values under the probe (writes seen: "
        f"{sorted(result['writes'])}). Either the probe missed the write or "
        "this script no longer emits telemetry rows; both make this assertion "
        "vacuous, so raise BLOCKED: to the planner rather than editing it."
    )

    # Two of these scripts merge rather than truncate: they read the existing
    # SoR and re-emit its rows alongside their own. Carried rows are OUT OF
    # SCOPE and must stay that way — per spec §2.1 their old-prefix values are
    # accurate records of where those bytes lived at the time, protected by
    # §5/§21, and the dead-pointer delta is carried by PATH-REDIRECTS. One of
    # them legitimately points into a different pilot repo entirely. Only
    # newly-generated values are this chunk's responsibility.
    generated = [v for v in emitted if v not in _sor_envelope_paths()]
    assert generated, (
        f"{rel} generated no new envelope_path values (all {len(emitted)} "
        "emitted values already exist in the SoR), so this assertion would "
        "pass vacuously"
    )

    dead = sorted({v for v in generated if not os.path.isfile(os.path.join(REPO_ROOT, v))})
    assert not dead, (
        f"{rel}: {len(dead)} distinct newly-generated envelope_path value(s) "
        f"of {len(generated)} do not resolve under {REPO_ROOT}: {dead[:5]}"
    )


@pytest.mark.parametrize("rel", sorted(_SOR_WRITERS))
def test_chunk2a_probe_writes_land_only_on_the_sor(rel):
    """§4.7 — behavioural confirmation that no forked telemetry file is written.

    :func:`test_chunk2a_runs_path_is_the_real_sor` checks the destination
    constant; this checks where the write actually goes, which is the claim
    that matters. A subject that resolved its constant correctly and then
    wrote somewhere else would pass the former and fail this.
    """
    want = os.path.realpath(os.path.join(REPO_ROOT, _SOR_REL))
    result = _probe(rel)
    stray = sorted(p for p in result["writes"] if os.path.realpath(p) != want)
    assert not stray, f"{rel} wrote outside the SoR: {stray} (expected only {want})"


# ── §2.1 — gen-findings.py CWD independence ──────────────────────────────


def test_chunk2a_gen_findings_has_no_cwd_relative_opens():
    """§2.1 — every literal path handed to ``open()`` is anchored.

    ``gen-findings.py`` has no ``__main__`` guard, so it is never imported
    here. Its defect class is different from the other three: the paths are
    literals inside functions, resolved against the invoking directory. A
    relative literal is the defect regardless of what the string says.
    """
    anchored = _anchored_names(_UNGUARDED)
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
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            if os.path.isabs(first.value):
                continue
        elif {n.id for n in ast.walk(first) if isinstance(n, ast.Name)} & anchored:
            continue
        offenders.append((getattr(node, "lineno", "?"), ast.unparse(first)))

    assert not offenders, (
        f"{_UNGUARDED}: unanchored open() paths at {offenders} — every argument "
        f"must derive from one of {sorted(anchored)} or be absolute"
    )


def test_chunk2a_gen_findings_runs_from_a_foreign_cwd():
    """§2.1 / §4.2 — the behavioural half of CWD independence.

    Closes kimi-k3 blocker 2. The static check above is a syntactic proxy, and
    the mutation that defeated its predecessor —
    ``open(os.path.join("evidence", "phase-3.2", ...))`` — was chosen because
    it is the *most natural* shape a well-meaning fix takes. This runs the
    script for real from a temp directory under the write-intercepting probe,
    so the property is measured rather than inferred.
    """
    result = _probe(_UNGUARDED)
    assert result["error"] is None, f"{_UNGUARDED} failed from a foreign CWD: {result['error']}"
    assert result["reads"], f"{_UNGUARDED} opened nothing; the probe saw no reads"
    relative = sorted({p for p in result["reads"] if not os.path.isabs(p)})
    assert not relative, (
        f"{_UNGUARDED} read CWD-relative path(s) {relative}; they resolved only "
        "because the probe's temp directory happened to contain them"
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
        f"rc={proc.returncode} from a foreign CWD\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    # A dry run that reports zero existing rows means the merge guard read the
    # wrong file — the silent half of finding 6.5. The assertion this replaces
    # tested ``"0 existing rows" not in stdout`` against a script that prints
    # "Existing rows: N (run_ids: [...])": the words never appear in that
    # order, so it could not fail. Parse the integer instead.
    if not os.path.isfile(os.path.join(REPO_ROOT, _SOR_REL)):
        pytest.skip(
            f"no {_SOR_REL} in this tree, so a zero row count is legitimate; "
            "the SoR is gitignored and absent on a fresh clone (spec §4.7)"
        )
    match = re.search(r"Existing rows:\s*(\d+)", proc.stdout)
    assert match is not None, (
        "dry run printed no 'Existing rows:' line; this assertion can no "
        f"longer see the merge guard\nstdout:\n{proc.stdout}"
    )
    assert int(match.group(1)) > 0, (
        "dry run read zero existing rows; the merge guard is pointed at the "
        f"wrong path\nstdout:\n{proc.stdout}"
    )


# ── §2.5 — lock.py's default locks dir ───────────────────────────────────


def test_chunk2a_lock_py_default_locks_dir_is_locks_root():
    """§2.5 — the lock writer defaults to where locks actually live.

    Unlike the other four subjects this one does not fail closed. Pre-fix the
    default resolves to ``tools/locks``, a directory that does not exist;
    ``lock.py`` would create it, write a manifest there, and report success
    while the guard that reads locks from ``LOCKS_ROOT`` sees nothing. Judge
    immutability — invariant 3 — would be silently off with every log line
    claiming otherwise.

    Parsed rather than executed: running ``lock.py`` writes a manifest, and a
    judge must not.
    """
    config = _cfg()
    locks_root = _require(config, "LOCKS_ROOT")
    expected = os.path.realpath(os.path.join(REPO_ROOT, locks_root))
    assert os.path.isdir(expected), f"LOCKS_ROOT is not a directory: {expected}"

    rel = "tools/phase-1-scripts/lock.py"
    default = None
    for node in ast.walk(_tree(rel)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_argument"):
            continue
        names = [
            a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)
        ]
        if "--locks-dir" not in names:
            continue
        for kw in node.keywords:
            if kw.arg == "default":
                default = kw.value
    assert default is not None, f"{rel}: no default found for --locks-dir"

    # Evaluate the default rather than grepping its source. Closes kimi-k3
    # blocker 3: the assertion this replaces was
    # ``"LOCKS_ROOT" in ast.unparse(default)``, which a one-keystroke typo
    # shape — ``os.path.join(_FRAMEWORK_ROOT, "LOCKS_ROOT")``, the quoted
    # constant name — satisfies while resolving to a directory that does not
    # exist. That is the fail-open wrong-directory write §2.5 exists to kill,
    # certified green.
    #
    # ``eval`` is bounded, not arbitrary: the expression is the ``default=``
    # keyword of the ``--locks-dir`` ``add_argument`` call, evaluated in the
    # module's own namespace after a side-effect-free import (``lock.py`` has a
    # ``__main__`` guard, so importing it writes nothing).
    src = ast.unparse(default)
    module = _load(rel)
    try:
        value = eval(src, dict(vars(module)))  # noqa: S307 — see above  # nosec B307 — controlled test eval of argparse default
    except Exception as exc:  # pragma: no cover - a default that cannot be built
        pytest.fail(f"{rel}: --locks-dir default {src!r} did not evaluate: {exc}")
    assert isinstance(value, str) and value, (
        f"{rel}: --locks-dir default {src!r} evaluated to {value!r}"
    )
    assert os.path.realpath(value) == expected, (
        f"{rel}: --locks-dir default {src!r} resolves to "
        f"{os.path.realpath(value)}, but locks live at {expected}. A lock "
        "writer and the guard that reads locks must not disagree."
    )
    assert os.path.isdir(os.path.realpath(value)), (
        f"{rel}: --locks-dir default resolves to {os.path.realpath(value)}, "
        "which is not a directory — lock.py would create it and report success"
    )


@pytest.mark.parametrize(
    "rel",
    [
        "tools/phase-1-scripts/lock.py",
        "tools/phase-1-hooks/locked-test-guard.py",
    ],
)
def test_chunk2a_lock_tooling_has_no_stale_phase_literals(rel):
    """§2.5 — route the lock writer and the lock reader.

    Neither is in the chunk-2 judge's ``ROUTED_PY_FILES``, which is how the
    ``lock.py`` default survived the chunk-2 residual scan. A lock writer and
    a lock reader that disagree about the lock location is the worst
    unrouted pair in the repo.
    """
    assert os.path.isfile(os.path.join(REPO_ROOT, rel)), f"missing: {rel}"
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
        assert os.path.join(*stale) not in source, (
            f"stale fixture path {os.path.join(*stale)!r} still in test_sprint_loop.py"
        )

    for root in (scripts_root, evidence_code_root):
        assert root in source, f"fixture does not build {root!r}"
