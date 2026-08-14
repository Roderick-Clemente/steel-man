"""Judge test for chunk-D1-4 (path-existence assertion, §2.2/§4.4).

Authored and locked by the PLANNER before chunk-D1-4 opens; its content hash
is ratified by the REFEREE before it locks. The executor of chunk-D1-4 must
NOT modify this file — framework invariant #3.

**Why this is its own file instead of a fourth test in `test_layout_paths.py`
as CHUNK-4-SPEC.md §2.2 originally asked for.** `test_layout_paths.py` is
content-hash-locked at `tools/phase-1-locks/tests/test_layout_paths.py.lock.json`
(`cb00dfac...`). Editing it in place — even to add a test — invalidates that
lock hash, and the builder seat does not touch a locked judge (invariant #3,
re-affirmed at chunk-D1-1 finding 1 and chunk-D1-3 F8). The builder correctly
refused to author Test 4 anywhere under any filename and filed it as F-A in
`FINDINGS-chunk-D1-4.md`, pointing at the precedent chunks 2, 2a, and 3
already established: each added its own separately-locked
`test_layout_paths_chunkN.py` rather than growing the base file. This file is
that same move for chunk 4. §2.2's *content* (assert the four script paths
resolve to files that exist) is unchanged; only its *location* differs from
the spec's original text, which is corrected in the same pass that ratifies
this file.

By chunk-D1-4, chunk-D1-2's flip has already landed, so the constants already
carry their post-move values — there is no pre/post-flip split to skip across
here the way `test_layout_paths.py` itself has to. Mirrors chunk-2/2a/3's
convention of skipping only if the flip has somehow not happened, as a
defensive floor rather than a live branch.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TOOLS = os.path.join(REPO_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

_TESTS = os.path.dirname(os.path.abspath(__file__))
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

# Reuse the Chunk-1 judge's config accessor, same convention as chunks 2/2a/3.
from test_layout_paths import _cfg, _require  # noqa: E402

# (constant, kind-key, expected relative filename) — §2.2's four rows.
_SUBJECTS = (
    ("SCRIPTS_ROOT", "lock.py"),
    ("SCRIPTS_ROOT", "valid-red.py"),
    ("SCRIPTS_ROOT", "verify-green.py"),
    ("EVIDENCE_CODE_ROOT", "local_backend.py"),
)


def _skip_if_not_flipped():
    config = _cfg()
    if _require(config, "EVIDENCE_ROOT") == "":
        pytest.skip("constants not yet flipped; chunk-D1-2 has not run")


def test_chunk4_script_paths_resolve_to_existing_files():
    """§2.2/§4.4 Test 4 — the constructed script paths exist on disk.

    Belt-and-suspenders: does not depend on running any of the four
    scripts, only on the roots + filename resolving to a real file. This is
    what §3.3's real invocations exercise dynamically; this test is the
    static floor under it, so a future move that breaks a path is caught
    even before anyone runs the scripts.
    """
    _skip_if_not_flipped()
    config = _cfg()

    missing = []
    for root_name, fname in _SUBJECTS:
        root = _require(config, root_name)
        composed = os.path.join(REPO_ROOT, root, fname)
        if not os.path.isfile(composed):
            missing.append(f"{root_name}/{fname} -> {composed}")

    assert not missing, "script path(s) do not resolve to an existing file:\n  " + "\n  ".join(
        missing
    )


def test_chunk4_subjects_cover_all_four_direct_invocations():
    """Guard: the subject list must stay in sync with §3.3's four scripts.

    If this list ever drifted to 3 entries the test above would still pass
    on those 3 — silently narrower than what §2.2 requires. Pinning the
    count and the exact filename set makes a dropped subject a failure
    instead of a quiet gap.
    """
    assert len(_SUBJECTS) == 4
    assert {fname for _, fname in _SUBJECTS} == {
        "lock.py",
        "valid-red.py",
        "verify-green.py",
        "local_backend.py",
    }
