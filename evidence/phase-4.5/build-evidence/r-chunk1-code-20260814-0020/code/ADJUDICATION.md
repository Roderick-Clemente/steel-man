# Adjudication: grok vs gemini on the residual scan's blind spots

The two seats **contradicted each other**, so the claim was settled by
measurement rather than by preferring a reviewer. Probe:
`residual-scan-probe.py`, output `residual-scan-probe.out`. It feeds twelve
synthetic unrouted sites through the locked judge's own
`_residual_phase_literals` and reports which are flagged.

| case | idiom | flagged? |
|------|-------|----------|
| A | `os.path.join(root, "phase-1", "scripts")` | YES |
| B | `"phase-1/scripts/x.py"` | YES |
| C | `f"{root}/phase-1/scripts/x.py"` | YES |
| D | `f"{root}/phase-1" + "/scripts"` | **NO** |
| E | `root + "/phase-1/scripts"` | YES |
| F | `root + "phase-1" + "scripts"` | **NO** |
| G | `"%s/phase-1/scripts" % root` | YES |
| H | `"{}/phase-1/scripts".format(root)` | YES |
| I | `seg = "phase-1"; os.path.join(root, seg, ...)` | **NO** |
| J | `os.sep.join(["phase-1","scripts"])` | **NO** |
| K | `Path(root) / "phase-1" / "scripts"` | YES |
| L | `PurePath(root, "phase-1", "scripts")` | **NO** |

## Who was right

**Neither, fully.**

- **gemini's `high` is directionally CORRECT — blind spots are real** — but
  its specific list is wrong on four of six items. It claimed the scan is
  blind to f-strings (`ast.JoinedStr`), `%`, `.format()`, and string
  concatenation (`ast.Add`). Cases C, G, H, E show all four ARE flagged.
  The reason is that in each, the phase prefix survives as a *single* string
  constant containing `phase-1/scripts`, which matcher 1 catches regardless
  of the surrounding expression node. gemini reasoned about the AST node
  types rather than about where the literal ends up.

- **grok's probe was accurate on what it tested** (it reported f-strings and
  joined literals flagged, which matches C and B) but it did not enumerate
  the negative cases, so it understated the gap.

- **The real blind spots are five, and only one seat gestured at any of
  them:** D, F, I, J, L. The common property is that no single constant ever
  contains a forbidden joined form AND no bare segment appears syntactically
  inside a `.join()` call or a pathlib `/` operand. `os.sep.join` (J) is the
  sharpest of these, because it is idiomatic path construction that the
  matcher's `.attr == "join"` test *does* reach — but the segments sit in a
  `List` argument rather than in `node.args`, so they are never inspected.

## Disposition

These are gaps in the **judge**, not in the build. No blind spot corresponds
to an actual site in chunk-D1-1: the routed code uses only idioms A, B, C, K,
all of which are flagged, and the suite is green at 197 with the routing in
place. So the gate did not let a real defect through; it is weaker than
advertised against a *hypothetical* future executor.

Recorded for the operator's freeze decision. Fixing this means widening the
matcher and re-locking, which is another judge edit under freeze.
