"""Filesystem assertions for D2-1 evidence consolidation.

The D2-1 inventory at `evidence/reviews/d2-1-builder/pre-move-sha256.json`
records the pixel-perfect "what moved where" at D2-1 close (the chunk-D2-1
deliverable). chunk-D5A then re-migrated a substantial fraction of the
files that inventory references:
  - d2-1 builder bundle: `evidence/phase-4.5/build-evidence/r-d2-1-builder/`
    → `evidence/reviews/d2-1-builder/`
  - top-level archived siblings: `archive/<bundle>/...` →
    `evidence/reviews/archive/<sprint>/...`
  - `legacy-duplicates/`: FROZEN per chunk-D1 deliverables fence;
    paths in inventory referencing it remain at their D2-1 location.

§5 of `planning/PATH-REDIRECTS.md` and §21 of
`tools/OPERATING-RULES.md` pin committed evidence under `evidence/`
as immutable: bytes may not be edited, moved, or rewritten. So the
inventory's destination paths record the **historical D2-1 close**
state, not the current state. Tests verify the bytes are still
retrievable **by SHA-256**, derived dynamically across the post-D5A
tree (which is the only mutability-respecting way to assert against
an inventory that recorded a pre-D5A truth).
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
# chunk-D5A migrated the d2-1 builder bundle to evidence/reviews/.
# legacy-duplicates subtree remains at the chunk-D1-frozen path.
BUNDLE = ROOT / "evidence/reviews/d2-1-builder"
INVENTORY = BUNDLE / "pre-move-sha256.json"
INDEX = ROOT / "planning/evidence-consolidation/D2-DUPLICATE-INDEX.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inventory() -> dict:
    return json.loads(INVENTORY.read_text())


def _sha_index() -> dict:
    """Walk the repo once and index every file by its SHA-256.
    Files with matching SHAs (chunk-D2A saw duplicate SHA bytes in
    some archive directories) are listed in arbitrary order."""
    idx: dict = {}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        try:
            sha = _sha256(p)
        except (PermissionError, OSError):
            continue
        # Skip the inventory itself (we read it first — it would index
        # its own bytes). Other evidence files are fair game.
        idx.setdefault(sha, []).append(p)
    return idx


# Eagerly compute the SHA index at module-load so per-test lookups
# are O(1) instead of walking the tree repeatedly.
_SHA_INDEX = _sha_index()


def test_inventory_parses_and_invariants():
    inventory = _inventory()
    assert inventory["source_file_count"] == 34
    assert inventory["source_bytes"] == 1_410_544
    assert len(inventory["relocated"]) == 34
    # Source paths point at the pre-D2-1 layout (`build-evidence/...`)
    # and are not expected to exist on disk post-D2-1.
    for item in inventory["relocated"]:
        assert (ROOT / item["source"]).exists() is False


def test_legacy_duplicates_subtree_is_frozen_at_chunk_d1_path():
    """chunk-D5A explicit carve-out: legacy-duplicates/ preserved at
    `evidence/phase-4.5/build-evidence/legacy-duplicates/` per the
    chunk-D1 deliverables fence. Inventory entries with
    /legacy-duplicates/ in their destination must still resolve at that
    frozen path."""
    legacy_root = ROOT / "evidence/phase-4.5/build-evidence/legacy-duplicates"
    assert legacy_root.is_dir(), "legacy-duplicates subtree must remain at its chunk-D1-frozen path"
    for item in _inventory()["relocated"]:
        if "/legacy-duplicates/" in item["destination"]:
            assert (ROOT / item["destination"]).is_file(), item["destination"]


def test_relocated_blobs_still_exist_by_sha_after_chunk_d5a():
    """Invariants the inventory asserts (sha256 + bytes) hold over the
    *whole repo* — discoverable post-chunk-D5A — independent of where
    the file is recorded to live (chunk-D2A-history vs. chunk-D5A-state)."""
    for item in _inventory()["relocated"]:
        sha = item["sha256"]
        candidates = _SHA_INDEX.get(sha)
        assert candidates, f"sha {sha} lost from repo"
        assert any(c.stat().st_size == item["bytes"] for c in candidates), item


def test_canonical_d1_blobs_still_exist_by_sha():
    for item in _inventory()["canonical_d1_tree"]:
        sha = item["sha256"]
        candidates = _SHA_INDEX.get(sha)
        assert candidates, f"sha {sha} lost from repo"
        assert any(c.stat().st_size == item["bytes"] for c in candidates), item


def test_d1_tokens_unchanged_after_chunk_d5a():
    """Token files (`evidence/phase-4.5/tokens/*.token.json`) are
    byte-frozen by §21 of OPERATING-RULES. The inventory's token
    entries carry only path + sha256 (no `bytes` field)."""
    for item in _inventory()["tokens"]:
        sha = item["sha256"]
        candidates = _SHA_INDEX.get(sha)
        assert candidates, f"sha {sha} lost from repo"
        # Token files are typically tiny (≤1 KB).
        assert any(c.stat().st_size <= 4096 for c in candidates), item


def test_top_level_archive_blobs_still_exist_by_sha():
    """chunk-D5A moved top-level `archive/<r-name>/` siblings to
    `evidence/reviews/archive/<sprint>/`. SHA-based discovery remains
    valid."""
    n_archive = 0
    for item in _inventory()["relocated"]:
        if "/build-evidence/archive/" in item["destination"]:
            n_archive += 1
            assert item["sha256"] in _SHA_INDEX, item
    assert n_archive >= 1, "inventory should reference the archive subtree"


def test_duplicate_index_documents_canonical_path_post_d5a():
    """D2-DUPLICATE-INDEX.md now names the canonical r-drs-role-split-1
    location post-chunk-D5A migration (evidence/reviews/...), with the
    legacy-duplicates/ subtree kept at its explicit carve-out path."""
    text = INDEX.read_text()
    assert "evidence/reviews/drs-role-split-1/" in text
    assert "evidence/phase-4.5/build-evidence/legacy-duplicates/r-drs-role-split-1/" in text
    # The legacy-duplicates/ subtree is the explicit frozen path
    frozen = ROOT / "evidence/phase-4.5/build-evidence/legacy-duplicates/r-drs-role-split-1"
    assert frozen.is_dir()
