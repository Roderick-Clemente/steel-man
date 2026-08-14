"""Judge tests for chunk-D1-3 (living-doc citations, PATH-REDIRECTS, LEDGER rename).

Authored by the PLANNER before chunk-D1-3 opens; its content hash is ratified
by the REFEREE before it locks, because the planner and the builder now share
a model family. The executor of chunk-D1-3 must NOT modify this file —
framework invariant #3. If an assertion looks wrong, the executor raises
``BLOCKED:`` to the planner rather than editing.

These tests are **side-effect free**: they read files and run read-only git
queries. Nothing here writes, stages, or commits.

Design notes, because this chunk's defect class is different from chunk 2a's:

* chunk-2a judged *path resolution in code*. This chunk judges *citations in
  prose*, so the assertions resolve links and prefixes against the filesystem
  rather than importing anything.
* The central assertion is :func:`test_chunk3_no_dead_relative_links`. It is
  the one that directly encodes the defect — four dead README links that
  404 on GitHub today — and it cannot be satisfied by a cosmetic sweep.
* ``tools/wiki-link-audit.py`` is deliberately NOT relied on. It reports
  ``dead=0`` on the commit where README.md has four dead links, because
  ``:24`` sets ``WIKI = "droid-wiki"`` and ``:88`` walks only that subtree.
  A green check that never looked at the file is the §7 silent-green shape;
  spec §4.6 records this at length.
* Residual ``phase-N/`` tokens are asserted *accounted for*, not *absent*.
  Historical narrative legitimately survives (spec §2.3), so the judge
  requires each residual to be enumerated in ``planning/PATH-REDIRECTS.md``
  and requires the enumeration to have no stale rows. Both directions, or
  the list rots into decoration.
* The 683 tokens under ``planning/layout-refactor/**`` and
  ``planning/phase-N/**`` are out of the citation-edit surface per spec
  §2.1b — those trees are self-describing move specs and time-stamped run
  records. This judge must never assert against them, and
  :func:`test_chunk3_redirect_only_surfaces_untouched` pins that.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── §2.1a — the citation-edit surface ────────────────────────────────────

_SURFACE_FILES = (
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

_SURFACE_GLOBS = (
    "tools/conventions/*.md",
    "tools/sprint_loop/prompts/*.md",
    "droid-wiki/*.md",
    "planning/ROADMAP-REVIEW*.md",
)

_REDIRECTS_REL = os.path.join("planning", "PATH-REDIRECTS.md")
_LEDGER_NEW = os.path.join("evidence", "LEDGER.md")
_LEDGER_OLD = os.path.join("planning", "phase-4.5", "LEDGER.md")

# A path-shaped token beginning with a bare ``phase-N`` segment. The leading
# character class excludes an already-rooted ``evidence/phase-3/``, so a
# correctly-updated citation cannot be counted as residual.
_BARE_PHASE = re.compile(r"(?:^|[^/A-Za-z0-9_.\-])(phase-[0-9]+(?:\.[0-9]+)?/)")

# Markdown inline links: ](target)
_MD_LINK = re.compile(r"\]\(([^)]+)\)")


def _surface() -> list[str]:
    """Repo-relative paths making up the §2.1a citation-edit surface."""
    out = []
    for rel in _SURFACE_FILES:
        if os.path.isfile(os.path.join(REPO_ROOT, rel)):
            out.append(rel)
    for pattern in _SURFACE_GLOBS:
        for abs_path in sorted(glob.glob(os.path.join(REPO_ROOT, pattern))):
            out.append(os.path.relpath(abs_path, REPO_ROOT))
    return sorted(set(out))


def _read(rel: str) -> str:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ("git",) + args, cwd=REPO_ROOT, capture_output=True, text=True
    )


def _residual_tokens() -> list[tuple[str, int, str]]:
    """Every bare ``phase-N/`` token in the surface, as (rel, lineno, token)."""
    found = []
    for rel in _surface():
        for lineno, line in enumerate(_read(rel).splitlines(), start=1):
            for match in _BARE_PHASE.finditer(line):
                found.append((rel, lineno, match.group(1)))
    return found


# ── §3.1 — the central assertion: no dead relative links ─────────────────


def test_chunk3_surface_is_non_empty():
    """Guard: the surface glob must actually resolve to files.

    Every other test in this file iterates the surface. If the globs stop
    matching, those tests pass vacuously — the exact false green spec §4.2
    warns about, where a check reports zero because it ran on nothing.
    """
    surface = _surface()
    assert len(surface) >= 20, f"surface collapsed to {len(surface)} files: {surface}"
    for required in ("README.md", "PRD.md", "tools/OPERATING-RULES.md"):
        assert required in surface, f"{required} missing from resolved surface"


def test_chunk3_no_dead_relative_links():
    """§3.1 — every relative markdown link in the surface resolves.

    The defect this chunk exists to fix. Baseline is 4 dead occurrences over
    3 unique targets, all in README.md, everything else clean — so anything
    other than 0 means the sweep either missed them or regressed a file that
    was already fine.

    A target is accepted if it resolves relative to the citing file's
    directory OR relative to the repo root; some docs legitimately cite from
    the root. External URLs and bare anchors are skipped.
    """
    dead = []
    checked = 0
    for rel in _surface():
        base = os.path.dirname(os.path.join(REPO_ROOT, rel))
        for lineno, line in enumerate(_read(rel).splitlines(), start=1):
            for match in _MD_LINK.finditer(line):
                target = match.group(1).strip()
                if not target or target.startswith("#"):
                    continue
                if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", target):
                    continue  # http:, https:, mailto:, etc.
                target = target.split("#", 1)[0].split("?", 1)[0].strip()
                if not target:
                    continue
                checked += 1
                if os.path.exists(os.path.join(base, target)) or os.path.exists(
                    os.path.join(REPO_ROOT, target)
                ):
                    continue
                dead.append(f"{rel}:{lineno} -> {target}")

    assert checked > 0, "no relative links checked; the link regex found nothing"
    assert not dead, (
        f"{len(dead)} dead relative link(s) of {checked} checked:\n  "
        + "\n  ".join(dead)
    )


def test_chunk3_readme_named_targets_resolve():
    """§2.5 — the three pinned README destinations exist.

    Asserted by resolving the paths, not by string-matching the spec's table,
    so a table edit cannot make this pass.
    """
    for rel in (
        "planning/phase-3.1/RESULTS.md",
        "planning/phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md",
        "planning/phase-1/KNOWN-ISSUES.md",
    ):
        assert os.path.isfile(
            os.path.join(REPO_ROOT, rel)
        ), f"pinned README destination missing: {rel}"

    readme = _read("README.md")
    stale = [
        m.group(0)
        for m in re.finditer(r"\]\(\./phase-[0-9]+(?:\.[0-9]+)?/[^)]*\)", readme)
    ]
    assert not stale, f"README still links bare phase-N paths: {stale}"


def test_chunk3_readme_layout_block_is_current():
    """§2.5 — the Layout block describes the layout that exists.

    It listed ``phase-0 … phase-5/`` as the build record, which is prose
    describing directories that no longer exist, and claimed 194 tests. A
    reader who follows the README's own map into nonexistent directories is
    the failure this chunk exists to prevent.
    """
    readme = _read("README.md")
    assert (
        "phase-0 … phase-5/" not in readme and "phase-0 ... phase-5/" not in readme
    ), "README Layout block still lists phase-0 … phase-5/ as the build record"
    assert "194 tests" not in readme, "README still claims 194 tests"
    assert re.search(
        r"^evidence/\s", readme, re.MULTILINE
    ), "README Layout block does not list evidence/, now a top-level build-record home"


# ── §3.2 / §3.3 — PATH-REDIRECTS is complete and truthful ────────────────


def test_chunk3_path_redirects_exists():
    """§2.2 — the redirects file is the mechanism the hard stop depends on."""
    assert os.path.isfile(
        os.path.join(REPO_ROOT, _REDIRECTS_REL)
    ), f"missing {_REDIRECTS_REL}; §2.1b's 683 redirect-only tokens have nowhere to go"


def test_chunk3_every_residual_token_is_accounted_for():
    """§3.2 — each residual ``phase-N/`` token is enumerated as an exception.

    Not "zero residuals": historical narrative legitimately survives per
    §2.3. What is forbidden is an *unaccounted* residual. The judge requires
    the citing ``file:line`` to appear in PATH-REDIRECTS.
    """
    redirects = _read(_REDIRECTS_REL)
    unaccounted = [
        f"{rel}:{lineno} ({token})"
        for rel, lineno, token in _residual_tokens()
        if f"{rel}:{lineno}" not in redirects
    ]
    assert not unaccounted, (
        f"{len(unaccounted)} residual phase-N citation(s) not enumerated in "
        f"{_REDIRECTS_REL}:\n  " + "\n  ".join(unaccounted)
    )


def test_chunk3_no_stale_exception_rows():
    """§3.2, other direction — a listed exception must still be a residual.

    Without this the exception list rots: rows accumulate for citations that
    were later fixed, and the list stops describing the repo.
    """
    redirects = _read(_REDIRECTS_REL)
    live = {f"{rel}:{lineno}" for rel, lineno, _ in _residual_tokens()}

    surface = set(_surface())
    stale = []
    for match in re.finditer(r"([\w./\-]+\.md):(\d+)", redirects):
        ref = f"{match.group(1)}:{match.group(2)}"
        if match.group(1) in surface and ref not in live:
            stale.append(ref)
    assert not stale, (
        "PATH-REDIRECTS lists surface citations that are no longer residual "
        f"(stale rows): {sorted(set(stale))}"
    )


def test_chunk3_redirect_table_targets_resolve():
    """§3.3 — every new-prefix in the table resolves on disk.

    A redirect table pointing at nothing is the same defect as the dead links
    it replaces. Only rows whose right-hand side is a repo-relative path are
    checked; prose arrows are ignored.
    """
    redirects = _read(_REDIRECTS_REL)
    broken = []
    rows = 0
    for lineno, line in enumerate(redirects.splitlines(), start=1):
        for match in re.finditer(
            r"`([^`]+)`\s*(?:→|->)\s*`([^`]+)`",
            line,
        ):
            new = match.group(2).strip()
            if not re.match(r"^(evidence|planning|tools|tests|telemetry)/", new):
                continue
            rows += 1
            probe = new.rstrip("/")
            if not os.path.exists(os.path.join(REPO_ROOT, probe)):
                broken.append(f"{_REDIRECTS_REL}:{lineno} -> {new}")

    assert rows > 0, (
        f"{_REDIRECTS_REL} declares no old->new prefix rows in backticked form; "
        "the table is the deliverable, not the prose around it"
    )
    assert not broken, "redirect targets that do not resolve:\n  " + "\n  ".join(broken)


# ── §3.4 — the LEDGER rename is a rename ─────────────────────────────────


def test_chunk3_ledger_moved_to_evidence_root():
    """§2.4 — the ledger lands at the evidence root, old path gone."""
    assert os.path.isfile(
        os.path.join(REPO_ROOT, _LEDGER_NEW)
    ), f"missing {_LEDGER_NEW}"
    assert not os.path.exists(
        os.path.join(REPO_ROOT, _LEDGER_OLD)
    ), f"{_LEDGER_OLD} still present; the move left a copy behind"


def test_chunk3_ledger_rename_carried_no_content_edit():
    """§2.4 — zero added and zero deleted lines on the renaming commit.

    The ledger is append-only (§5). A rename that smuggles a content edit
    into it is a failed chunk, not a nit — so this resolves the actual
    rename commit and reads its numstat rather than trusting HEAD.

    The numstat query must NOT use a pathspec: ``git show --numstat --
    <path>`` filters the tree diff before rename detection runs, so git
    reports the destination as an ADD with the full file content as
    additions. The unfiltered diff with ``-M`` detects the rename and
    reports 0/0. Builder finding: BLOCKED on chunk-D1-3, raised correctly.
    """
    found = _git(
        "log", "--follow", "--diff-filter=R", "--format=%H", "--", _LEDGER_NEW
    )
    assert found.returncode == 0, f"git log failed: {found.stderr}"
    shas = [ln.strip() for ln in found.stdout.splitlines() if ln.strip()]
    assert shas, f"no rename commit found for {_LEDGER_NEW}; was it moved with git mv?"

    sha = shas[0]
    # No pathspec: -- <path> breaks rename detection by filtering before
    # the similarity check runs. -M enables rename detection explicitly.
    stat = _git("show", "--numstat", "--format=", "-M", sha)
    assert stat.returncode == 0, f"git show failed: {stat.stderr}"

    # Filter for the LEDGER line (rename format: {old => new}/LEDGER.md)
    ledger_rows = [
        ln for ln in stat.stdout.splitlines()
        if ln.strip() and "LEDGER.md" in ln
    ]
    assert ledger_rows, (
        f"no numstat row for LEDGER.md at {sha}; the rename was not detected. "
        f"Full numstat:\n{stat.stdout}"
    )
    for row in ledger_rows:
        parts = row.split("\t")
        assert len(parts) >= 2, f"unexpected numstat format: {row!r}"
        added, deleted = parts[0], parts[1]
        assert added == "0" and deleted == "0", (
            f"rename commit {sha} changed {_LEDGER_NEW} content: "
            f"+{added}/-{deleted}. Append-only file, rename only."
        )


def test_chunk3_ledger_history_is_preserved():
    """§2.4 — ``git log --follow`` reaches the pre-rename history."""
    log = _git("log", "--follow", "--format=%H", "--", _LEDGER_NEW)
    assert log.returncode == 0, f"git log failed: {log.stderr}"
    shas = [ln.strip() for ln in log.stdout.splitlines() if ln.strip()]
    assert len(shas) > 1, (
        f"--follow on {_LEDGER_NEW} reaches only {len(shas)} commit(s); "
        "history did not survive the move"
    )


# ── §3.6 — the locked judges are untouched ───────────────────────────────


@pytest.mark.parametrize(
    "rel,prefix",
    [
        ("tests/test_layout_paths.py", "cb00dfac"),
        ("tests/test_layout_paths_chunk2.py", "48a579f8"),
    ],
)
def test_chunk3_existing_judges_byte_unchanged(rel, prefix):
    """§3.6 — the executor may not modify the tests that judge it.

    Includes ``test_layout_paths.py:571``, which cites the old LEDGER path in
    a comment. It is lock-frozen, so §2.2 covers it by redirect rather than
    edit — fixing that comment is a lock violation, not a tidy-up.
    """
    import hashlib

    path = os.path.join(REPO_ROOT, rel)
    assert os.path.isfile(path), f"missing judge: {rel}"
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    assert digest.startswith(prefix), f"{rel} sha256 {digest} does not start {prefix}"


def test_chunk3_redirect_only_surfaces_untouched():
    """§2.1b — this chunk does not sweep the 683 redirect-only tokens.

    ``planning/layout-refactor/**`` holds the specs describing this very move
    (their phase-N tokens are the *before* side of move tables) and
    ``planning/phase-N/**`` holds time-stamped run records. Rewriting either
    falsifies a record to fix a link. If these counts collapse, someone
    "finished the job" past the §5 hard stop.
    """
    def count(pattern: str) -> int:
        total = 0
        for abs_path in glob.glob(os.path.join(REPO_ROOT, pattern)):
            if not abs_path.endswith(".md"):
                continue
            rel = os.path.relpath(abs_path, REPO_ROOT)
            for line in _read(rel).splitlines():
                total += len(_BARE_PHASE.findall(line))
        return total

    layout = count("planning/layout-refactor/*.md")
    historical = count("planning/phase-*/*.md")

    assert layout > 200, (
        f"planning/layout-refactor/ bare phase-N tokens dropped to {layout} "
        "(was 265); the move specs' before-side citations were swept"
    )
    assert historical > 350, (
        f"planning/phase-*/ bare phase-N tokens dropped to {historical} "
        "(was 418, minus the 61 that leave with LEDGER); run records were rewritten"
    )
