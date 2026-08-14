import importlib.util, os, tempfile
spec=importlib.util.spec_from_file_location('t','tests/test_layout_paths.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

cases = {
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
print(f"{'case':28} {'flagged?':10} detail")
for name, src in cases.items():
    with tempfile.NamedTemporaryFile('w',suffix='.py',delete=False) as fh:
        fh.write(src); path=fh.name
    hits = m._residual_phase_literals(path)
    os.unlink(path)
    print(f"{name:28} {'YES' if hits else '*** NO ***':10} {hits}")
