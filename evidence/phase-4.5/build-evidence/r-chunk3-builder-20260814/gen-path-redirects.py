#!/usr/bin/env python3
"""Generate `planning/PATH-REDIRECTS.md` for chunk-D1-3.

Two of the three blocks in that file are measurements, not prose, so they are
generated rather than typed (§9, §7):

* the **prefix table** is derived from the chunk-D1-2 move commit itself
  (``git show --name-status --find-renames ee90061``), so it cannot disagree with
  what actually moved. 618 renames collapse to a prefix map; every destination is
  probed on disk before it is written.
* the **historical-narrative exception list** is derived by re-running the
  residual matcher over the §2.1a surface, so its ``file:line`` rows are exact
  at generation time rather than hand-counted.

The deliberate non-vacuity guard: this script does NOT enumerate whatever
residuals it happens to find. It enumerates residuals only in the files named in
``NARRATIVE`` — the two documents I argue are records rather than pointers — and
**refuses (rc=1, writes nothing)** if a residual turns up anywhere else. Without
that, a future half-swept sweep would be papered over by re-running the
generator, and `test_chunk3_every_residual_token_is_accounted_for` would pass by
construction instead of by argument. The classification is the human judgment;
only the line numbers are mechanical.

Usage: python3 gen-path-redirects.py [--check]
  --check   compare against the file on disk, write nothing (rc=1 on drift)
"""
from __future__ import annotations

import collections
import glob
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT_REL = os.path.join("planning", "PATH-REDIRECTS.md")
MOVE_COMMIT = "ee90061"

# Mirrors the judge's ``_BARE_PHASE`` (tests/test_layout_paths_chunk3.py). If the
# two ever drift, the judge fails rather than this script lying: an under-broad
# regex here means a residual goes unlisted, which the judge catches.
BARE_PHASE = re.compile(r"(?:^|[^/A-Za-z0-9_.\-])(phase-[0-9]+(?:\.[0-9]+)?/)")

# §2.1a citation-edit surface, same membership as the judge's.
SURFACE_FILES = (
    "PRD.md",
    "AGENTS.md",
    "README.md",
    "tools/OPERATING-RULES.md",
    "tools/README.md",
    "tools/KNOWN-ISSUES.md",
    "tools/PHASE-0.5-CLOSE.md",
    "tools/RUN-LEDGER.md",
    "tools/REPRODUCE.md",
    "skills/adversarial-sprint/SKILL.md",
    "skills/sprint-invocation/SKILL.md",
)
SURFACE_GLOBS = (
    "tools/conventions/*.md",
    "tools/sprint_loop/prompts/*.md",
    "droid-wiki/*.md",
    "planning/ROADMAP-REVIEW*.md",
)

# The classification this chunk stands behind. Anything else with a residual is
# an error, not an exception.
NARRATIVE = {
    "droid-wiki/by-the-numbers.md": (
        "Measurement snapshot. Every row is a count taken against one commit — "
        "files, lines, mean line length per directory. Re-rooting the directory "
        "name falsifies the number beside it: `phase-3.2/` counted 21 files as one "
        "silo, and no directory holds those 21 files today (they are split across "
        "`planning/phase-3.2/`, `evidence/phase-3.2/` and "
        "`tools/phase-3.2-evidence/`). A measurement is only true of the tree it "
        "was taken on."
    ),
    "droid-wiki/lore.md": (
        "Build history. The `Key files created:` lines record what each phase "
        "created **at the path it created it at** — that is the record. Spec §2.3 "
        "names this case exactly (\"Phase 1 built `phase-1/scripts/lock.py`\") and "
        "rules it out of the rewrite."
    ),
}


def surface() -> list[str]:
    out = []
    for rel in SURFACE_FILES:
        if os.path.isfile(os.path.join(REPO_ROOT, rel)):
            out.append(rel)
    for pattern in SURFACE_GLOBS:
        for abs_path in sorted(glob.glob(os.path.join(REPO_ROOT, pattern))):
            out.append(os.path.relpath(abs_path, REPO_ROOT))
    return out


def read(rel: str) -> str:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def residuals() -> list[tuple[str, int, str]]:
    found = []
    for rel in surface():
        for lineno, line in enumerate(read(rel).splitlines(), start=1):
            for match in BARE_PHASE.finditer(line):
                found.append((rel, lineno, match.group(1)))
    return found


def prefix_map() -> list[tuple[str, str, int]]:
    """(old prefix, new prefix, files moved) from the move commit's renames."""
    proc = subprocess.run(
        ["git", "show", "--name-status", "--find-renames", "--format=", MOVE_COMMIT],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    counts: dict[tuple[str, str], int] = collections.Counter()
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if not parts[0].startswith("R") or len(parts) != 3:
            continue
        old, new = parts[1], parts[2]
        segs = old.split("/")
        if not segs[0].startswith("phase-"):
            continue  # the plan-lint fixture repo; covered in prose, not the table
        key = segs[0] + "/" + (segs[1] + "/" if len(segs) > 2 else "")
        tail = old[len(key):]
        if not new.endswith(tail):
            raise SystemExit(f"non-segment-preserving rename, table would lie: {old} -> {new}")
        counts[(key, new[:len(new) - len(tail)])] += 1
    rows = []
    for (old, new), n in sorted(counts.items()):
        if not os.path.exists(os.path.join(REPO_ROOT, new.rstrip("/"))):
            raise SystemExit(f"redirect target does not resolve, refusing to write: {new}")
        rows.append((old, new, n))
    return rows


def ambiguous_files(rows: list[tuple[str, str, int]]) -> dict[str, list[tuple[str, str]]]:
    """File-level rows for old prefixes that fan out to more than one root."""
    fan = collections.Counter(old for old, _, _ in rows)
    multi = {old for old, n in fan.items() if n > 1}
    if not multi:
        return {}
    proc = subprocess.run(
        ["git", "show", "--name-status", "--find-renames", "--format=", MOVE_COMMIT],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    out: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if not parts[0].startswith("R") or len(parts) != 3:
            continue
        old, new = parts[1], parts[2]
        for key in multi:
            rest = old[len(key):]
            if old.startswith(key) and rest and "/" not in rest:
                out[key].append((old, new))
    return {k: sorted(v) for k, v in out.items()}


def build() -> str:
    rows = prefix_map()
    amb = ambiguous_files(rows)
    res = residuals()

    unexpected = sorted({rel for rel, _, _ in res} - set(NARRATIVE))
    if unexpected:
        print("REFUSING to write: residual phase-N citations in files that are not "
              "declared historical narrative. Fix the citation or argue the "
              "exception explicitly — do not let the generator absorb it.",
              file=sys.stderr)
        for rel in unexpected:
            for r, ln, tok in res:
                if r == rel:
                    print(f"  {r}:{ln}  {tok}", file=sys.stderr)
        raise SystemExit(1)

    per_file: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    for rel, ln, tok in res:
        per_file[rel].append((ln, tok))

    L: list[str] = []
    A = L.append
    A("# `PATH-REDIRECTS.md` — old path → new home")
    A("")
    A("Deliverable D1 (chunk-D1-2, commit `ee90061`) moved **618 tracked files** out of")
    A("the `phase-N/` silos and into homes organized by kind. This file is how a citation")
    A("written before that move is still followable afterwards.")
    A("")
    A("It exists because the alternative does not scale and would not be honest.")
    A("**788** bare `phase-N/` tokens survive the move across markdown; **105** of them")
    A("sit in living documents that a reader follows today, and those were rewritten in")
    A("chunk-D1-3. The other **683** must not be edited at all:")
    A("")
    A("* **`planning/layout-refactor/**` (265 tokens at measurement time)** — the move")
    A("  specs. Their `phase-N/` tokens are the *before* side of move tables. \"Updating\"")
    A("  `` `phase-0/evidence/` → `evidence/phase-0/` `` yields")
    A("  `` `evidence/phase-0/` → `evidence/phase-0/` `` and destroys the document.")
    A("* **`planning/phase-N/**` (418 tokens, 357 after the LEDGER moved out)** —")
    A("  time-stamped run records. `planning/phase-3/RUN-COMMANDS.md` records the literal")
    A("  command that was executed at the time. Rewriting it produces a command that was")
    A("  never run: a falsified record in exchange for a working link.")
    A("* **Committed evidence under `evidence/`** — immutable by §5/§21. 144 lines across")
    A("  76 envelope/capture files carry old prefixes and stay exactly as the reviewer")
    A("  wrote them.")
    A("")
    A("For all of those, this file carries the delta instead. That is the §5 hard stop")
    A("working as designed rather than a scope cut.")
    A("")
    A("## Matching algorithm")
    A("")
    A("Carried from `planning/layout-refactor/PLAN.md`:")
    A("")
    A("1. Strip an optional absolute repo-root prefix")
    A("   (`/Users/factory/work/adversarial-sprint-dev/`) from the cited path.")
    A("2. Match the **longest** old prefix in the table below against the resulting")
    A("   relative path.")
    A("3. Apply only to path-shaped tokens:")
    A("   `(?:tools|phase-\\d+(?:\\.\\d+)?|tests|telemetry|evidence|planning)/[\\w/.-]+`")
    A("4. Leave prose mentions (\"Phase 1 built…\") untouched.")
    A("")
    A("The mapping is **segment-preserving**: everything after the matched prefix is")
    A("copied through unchanged, so")
    A("`phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt` →")
    A("`evidence/phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`.")
    A("")
    A(f"## Prefix table — {len(rows)} rows, derived from `{MOVE_COMMIT}`")
    A("")
    A("Generated from the move commit's own rename records")
    A("(`git show --name-status --find-renames`), not hand-transcribed, and every")
    A("destination is probed on disk before this file is written. The count is how many")
    A("files moved under that prefix.")
    A("")
    A("| redirect | files |")
    A("|---|---|")
    for old, new, n in rows:
        A(f"| `{old}` → `{new}` | {n} |")
    A("")
    A("### Prefixes that fan out to more than one root")
    A("")
    A("The move split silos by **kind**, so a few old prefixes have no single answer:")
    A("code went to `tools/`, committed evidence to `evidence/`, plans and prompts to")
    A("`planning/`. Longest-prefix matching is not enough for these; resolve them")
    A("file by file.")
    A("")
    for key in sorted(amb):
        A(f"**`{key}`**")
        A("")
        A("| old | new |")
        A("|---|---|")
        for old, new in amb[key]:
            A(f"| `{old}` | `{new}` |")
        A("")
    A("## Historical-narrative exceptions")
    A("")
    A("Spec §2.3 keeps historical narrative out of the rewrite: a sentence about what")
    A("was built, or a measurement of a past tree, is a record rather than a pointer.")
    A(f"Every surviving residual on the §2.1a surface is listed here — **{len(res)}**")
    A("tokens in 2 files — so that a residual is an accounted-for decision and never a")
    A("missed sweep. `tests/test_layout_paths_chunk3.py` asserts this list in both")
    A("directions: no unlisted residual, and no listed row that is no longer residual.")
    A("")
    A("Line numbers are exact as of the commit that lands this file. They are")
    A("regenerable — see `evidence/phase-4.5/build-evidence/r-chunk3-builder-20260814/`")
    A("— and the judge fails loudly rather than quietly if they rot.")
    A("")
    for rel in sorted(per_file):
        entries = per_file[rel]
        A(f"### `{rel}` — {len(entries)} residual tokens")
        A("")
        A(NARRATIVE[rel])
        A("")
        A("| citation | token | line |")
        A("|---|---|---|")
        lines = read(rel).splitlines()
        for ln, tok in entries:
            text = lines[ln - 1].strip().replace("|", "\\|")
            if len(text) > 88:
                text = text[:85] + "…"
            A(f"| `{rel}:{ln}` | `{tok}` | {text} |")
        A("")
    A("## Stale citations inside lock-frozen live code")
    A("")
    A("One residual is not in a document at all. `tests/test_layout_paths.py` line 571")
    A("carries a comment citing the ledger at its pre-chunk-3 path,")
    A("`planning/phase-4.5/LEDGER.md`. That file is a judge, content-locked at")
    A("`cb00dfac…` against `tools/phase-1-locks/tests/test_layout_paths.py.lock.json`,")
    A("and the executor of this chunk may not touch it — not even to fix a comment")
    A("(spec §6, framework invariant #3).")
    A("")
    A("It is called out separately because it is the first case where this file covers a")
    A("stale citation inside **live code** rather than inside a document or an evidence")
    A("byte. A future reader who greps the tests, finds the old path, and cannot find")
    A("the file needs to know that the staleness is intentional and where the ledger")
    A("went: `planning/phase-4.5/LEDGER.md` → `evidence/LEDGER.md`, moved by `git mv` in")
    A("chunk-D1-3 with zero content edits, because the ledger is append-only (§5, §21)")
    A("and a sprint-wide record does not belong inside one phase's planning directory.")
    A("")
    A("## Scope")
    A("")
    A("This file is a redirect map, not a to-do list. The 683 tokens it covers are")
    A("**deliberately** unedited, for the reasons at the top. Anyone tempted to \"finish")
    A("the job\" by sweeping them should read spec §5 first — and")
    A("`test_chunk3_redirect_only_surfaces_untouched` fails if those trees are swept,")
    A("which is the same hard stop expressed as a test.")
    A("")
    return "\n".join(L)


def main() -> int:
    text = build()
    out_abs = os.path.join(REPO_ROOT, OUT_REL)
    if "--check" in sys.argv[1:]:
        current = open(out_abs, encoding="utf-8").read() if os.path.isfile(out_abs) else None
        if current == text:
            print(f"{OUT_REL}: up to date ({len(text.splitlines())} lines)")
            return 0
        print(f"{OUT_REL}: DRIFT — regenerate", file=sys.stderr)
        return 1
    with open(out_abs, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT_REL}: {len(text.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
