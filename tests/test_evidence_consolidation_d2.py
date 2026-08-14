"""Filesystem assertions for D2-1 evidence consolidation."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814"
INVENTORY = BUNDLE / "pre-move-sha256.json"
INDEX = ROOT / "planning/evidence-consolidation/D2-DUPLICATE-INDEX.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inventory() -> dict:
    return json.loads(INVENTORY.read_text())


def test_top_level_source_is_absent_and_all_34_destinations_exist():
    inventory = _inventory()
    assert inventory["source_file_count"] == 34
    assert inventory["source_bytes"] == 1_410_544
    assert not (ROOT / "build-evidence").exists()
    assert len(inventory["relocated"]) == 34
    assert all((ROOT / item["destination"]).is_file() for item in inventory["relocated"])
    assert all(not (ROOT / item["source"]).exists() for item in inventory["relocated"])


def test_relocated_bytes_match_pre_move_sha256_inventory():
    for item in _inventory()["relocated"]:
        destination = ROOT / item["destination"]
        assert destination.stat().st_size == item["bytes"], item["destination"]
        assert _sha256(destination) == item["sha256"], item["destination"]


def test_canonical_d1_tree_remains_byte_identical():
    for item in _inventory()["canonical_d1_tree"]:
        path = ROOT / item["path"]
        assert path.is_file(), item["path"]
        assert path.stat().st_size == item["bytes"], item["path"]
        assert _sha256(path) == item["sha256"], item["path"]


def test_duplicate_index_names_existing_canonical_and_retained_paths():
    text = INDEX.read_text()
    assert "evidence/phase-4.5/build-evidence/r-drs-role-split-1/" in text
    assert "evidence/phase-4.5/build-evidence/legacy-duplicates/r-drs-role-split-1/" in text
    for item in _inventory()["relocated"]:
        if "/legacy-duplicates/" in item["destination"]:
            assert (ROOT / item["destination"]).is_file()


def test_d1_tokens_are_unchanged():
    for item in _inventory()["tokens"]:
        path = ROOT / item["path"]
        assert path.is_file(), item["path"]
        assert _sha256(path) == item["sha256"], item["path"]
