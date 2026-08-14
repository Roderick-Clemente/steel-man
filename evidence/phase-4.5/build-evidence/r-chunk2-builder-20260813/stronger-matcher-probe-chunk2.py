"""Stronger residual matcher — builder-side verification probe.

NOT a repo file and NOT an edit to the frozen judge. This exists to test one
claim the planner made and my code depends on: "impact on this chunk: none —
routed code uses only flagged idioms." If a stronger matcher flags anything in
d5db8ff/5cd2ac4's routed files, that is MY defect to fix, and I would rather
find it now than when the fixed judge lands and reddens the suite.

Closes the 5 blind spots the planner's probe measured (D f-string split segs,
F concat bare seg, I variable holds segment, J os.sep.join, L PurePath) by
folding static strings instead of pattern-matching one idiom at a time.
"""
from __future__ import annotations

import ast
import os
import re
import sys
import tempfile

FORBIDDEN = (
    "phase-4.5/tokens", "phase-4.5/build-evidence", "phase-4.5/prompts",
    "phase-1/scripts", "phase-1/locks", "phase-3.2/evidence",
)
BARE = re.compile(r"^phase-\d+(?:\.\d+)?$")
JOINERS = {"join"}
PATHCALLS = {"Path", "PurePath", "PurePosixPath", "PureWindowsPath", "PosixPath"}


class Folder:
    """Folds the STATIC part of a string expression. Unknown -> None."""

    def __init__(self, consts: dict[str, str]):
        self.consts = consts

    def fold(self, n):
        if isinstance(n, ast.Constant):
            return n.value if isinstance(n.value, str) else None
        if isinstance(n, ast.Name):
            return self.consts.get(n.id)
        if isinstance(n, ast.JoinedStr):
            # literal parts only; interpolations become a placeholder that
            # cannot mask a forbidden substring spanning them
            out = []
            for v in n.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    out.append(v.value)
                else:
                    inner = self.fold(v.value) if isinstance(v, ast.FormattedValue) else None
                    out.append(inner if inner is not None else "\x00")
            return "".join(out)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            a, b = self.fold(n.left), self.fold(n.right)
            if a is None and b is None:
                return None
            return (a or "\x00") + (b or "\x00")
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod):
            a = self.fold(n.left)
            return a.replace("%s", "\x00") if a else None
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr == "format":
                a = self.fold(f.value)
                return a.replace("{}", "\x00") if a else None
            if isinstance(f, ast.Attribute) and f.attr in JOINERS:
                sep = self.fold(f.value)
                parts = self._elements(n)
                if sep is not None and parts is not None:
                    return sep.join(p if p is not None else "\x00" for p in parts)
            if isinstance(f, ast.Attribute) and f.attr == "join" and isinstance(f.value, ast.Attribute):
                pass
        return None

    def _elements(self, call):
        """Elements of a join(...) call: either a List/Tuple arg or varargs."""
        if len(call.args) == 1 and isinstance(call.args[0], (ast.List, ast.Tuple)):
            return [self.fold(e) for e in call.args[0].elts]
        if call.args:
            return [self.fold(a) for a in call.args]
        return None


def _docstrings(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
               and isinstance(body[0].value.value, str):
                found.add(id(body[0].value))
    return found


def _module_str_consts(tree, is_config):
    """Module-level NAME = "str" bindings, and the config.py constant exemption."""
    consts, exempt = {}, set()
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        f = Folder(consts)
        val = f.fold(node.value)
        for nm in names:
            if val is not None:
                consts[nm] = val
        if is_config and any(n.isupper() and not n.startswith("_") for n in names):
            for sub in ast.walk(node.value):
                exempt.add(id(sub))
    return consts, exempt


def scan(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    is_config = os.path.basename(path) == "config.py"
    skip = _docstrings(tree)
    consts, exempt = _module_str_consts(tree, is_config)
    skip |= exempt
    f = Folder(consts)
    hits = []

    # (1) any expression whose folded static value contains a forbidden path
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if not isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp, ast.Call)):
            continue
        v = f.fold(node)
        if v and any(b in v for b in FORBIDDEN):
            hits.append(f"line {node.lineno}: folded {v!r}")

    # (2) bare segments in ANY path-composition context
    for node in ast.walk(tree):
        elems = []
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr in JOINERS:
                elems = (f._elements(node) or [], node)
            elif isinstance(fn, ast.Name) and fn.id in PATHCALLS:
                elems = ([f.fold(a) for a in node.args], node)
            elif isinstance(fn, ast.Attribute) and fn.attr in PATHCALLS:
                elems = ([f.fold(a) for a in node.args], node)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            elems = ([f.fold(node.left), f.fold(node.right)], node)
        if not elems:
            continue
        vals, anchor = elems
        if id(anchor) in skip:
            continue
        for v in vals:
            if v and BARE.match(v):
                hits.append(f"line {anchor.lineno}: bare segment {v!r} in path composition")

    # (3) concat chains of bare segments: root + "phase-1" + "scripts"
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Add):
            continue
        if id(node) in skip:
            continue
        for side in (node.left, node.right):
            v = f.fold(side)
            if v and BARE.match(v.strip("/")):
                hits.append(f"line {node.lineno}: bare segment {v!r} in concat")

    return sorted(set(hits))


CASES = {
 "A os.path.join bare segs":   'import os\np = os.path.join(root, "phase-1", "scripts", "x.py")\n',
 "B joined literal":           'p = "phase-1/scripts/x.py"\n',
 "C static f-string":          'p = f"{root}/phase-1/scripts/x.py"\n',
 "D f-string split segs":      'p = f"{root}/phase-1" + "/scripts"\n',
 "E str concat (ast.Add)":     'p = root + "/phase-1/scripts"\n',
 "F concat bare seg":          'p = root + "phase-1" + "scripts"\n',
 "G percent format":           'p = "%s/phase-1/scripts" % root\n',
 "H .format()":                'p = "{}/phase-1/scripts".format(root)\n',
 "I variable holds segment":   'import os\nseg = "phase-1"\np = os.path.join(root, seg, "scripts")\n',
 "J os.sep.join":              'import os\np = os.sep.join(["phase-1","scripts"])\n',
 "K pathlib /":                'from pathlib import Path\np = Path(root) / "phase-1" / "scripts"\n',
 "L PurePath":                 'from pathlib import PurePath\np = PurePath(root, "phase-1", "scripts")\n',
}
MUST_FLAG = set("ABCDEFGHIJKL")

ROUTED = (
 "tools/sprint_loop/per_chunk.py", "tools/sprint_loop/config.py",
 "tools/sprint_loop/backends.py", "tools/orchestrate-review.py",
 "tools/phase-3.2-evidence/local_backend.py", "tools/sprint_loop/chunk_close_banner.py",
 "tools/sprint-loop.py", "tools/chunk_sequence_gate.py", "tools/sign_chunk_token.py",
)
# §2.2 excludes these by design — telemetry/HMAC labels. Must NOT regress.
LABELS = {
 "tools/sprint_loop/per_chunk.py": [287], "tools/sprint_loop/backends.py": [197, 198],
 "tools/sprint-loop.py": [268, 422, 483], "tools/orchestrate-review.py": [459],
}

print("=" * 66)
print("PART 1 — 12 synthetic idioms through the STRONGER matcher")
print("=" * 66)
bad = []
for name, src in CASES.items():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(src); p = fh.name
    hits = scan(p); os.unlink(p)
    ok = bool(hits)
    if name[0] in MUST_FLAG and not ok:
        bad.append(name)
    print(f"  {name:28} {'YES' if ok else '*** NO ***'}")
print(f"\n  all 12 flagged: {'YES' if not bad else 'NO -> ' + str(bad)}")

print("=" * 66)
print("PART 2 — STRONGER matcher over the routed files at HEAD")
print("=" * 66)
total = 0
for rel in ROUTED:
    hits = scan(rel)
    total += len(hits)
    print(f"  {rel:46} {len(hits)} hit(s)")
    for h in hits:
        print(f"      {h}")
print(f"\n  TOTAL residual hits in routed code: {total}")

print("=" * 66)
print("PART 3 — legitimate label sites must stay UNFLAGGED")
print("=" * 66)
regress = []
for rel, lines in LABELS.items():
    hits = scan(rel)
    for ln in lines:
        if any(f"line {ln}:" in h for h in hits):
            regress.append(f"{rel}:{ln}")
    print(f"  {rel:46} labels {lines} -> {'FLAGGED (regression)' if any(f'line {l}:' in h for h in hits for l in lines) else 'clean'}")
print(f"\n  false-positive regressions: {regress or 'none'}")
print()
print("VERDICT:", "routed code is CLEAN under the stronger matcher"
      if total == 0 and not bad and not regress else "ATTENTION NEEDED")
