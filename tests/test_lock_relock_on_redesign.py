"""KI-18 pin: a test-designer bounce re-locks the redesigned test.

Arm B of the cheap-vs-expensive executor experiment (see
``tools/EXPERIMENT-cheap-vs-expensive-executor.md``) hit the defect this
suite pins: after a ``REJECT_TEST`` verdict routed the chunk to the
test-designer, the rewritten suite (7 → 20 tests) was not re-locked, so
the lock manifest still held the pre-redesign SHA and the next
validation round fail-closed on a stale lock.

The review-cleanup stack's REJECT_TEST routing (commit ``b4b687a``)
closes this incidentally: the redesign round re-enters
``run_chunk_inner``, whose step 2 runs ``lock_test`` unconditionally, so
the manifest is regenerated from the on-disk redesigned suite before the
next validation round reads ``locked_test_sha``. These tests drive the
REAL ``lock.py`` script (not a stub) through that loop, so a regression
back to a stale manifest fails loudly. The resume-mid-bounce case is
pinned separately: ``rejection_kind="test"`` round-trips through the
checkpoint, and the resumed round re-fires the designer and re-locks.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from conftest import (  # noqa: E402
    _load_runner_module,
    _observed,
    _run_state,
    _stub_loop,
)
from sprint_loop import per_chunk  # noqa: E402
from sprint_loop.backends import BackendResult  # noqa: E402
from sprint_loop.config import Config  # noqa: E402
from sprint_loop.state import ChunkState, GateDecision  # noqa: E402


# The Arm B shape: the first locked suite (7 tests) and the redesigned
# suite (20 tests) are materially different files, so the lock SHA must
# change between them. Content is cosmetic — what matters is that the
# manifest tracks the file that is CURRENTLY locked.
SEVEN_TESTS = "\n".join(
    f"def test_homes_store_{i}():\n    assert True" for i in range(7)
) + "\n"

TWENTY_TESTS = "\n".join(
    f"def test_homes_store_{i}():\n    assert True" for i in range(20)
) + "\n"


def _sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunk() -> ChunkState:
    return ChunkState(
        chunk_id="c-arm-b",
        scope="read devices without naming a home",
        observable_criteria=["devices are readable without an explicit identifier"],
        locked_test_files=["test/test_homes_store.py"],
        commands=["/usr/bin/true -m pytest test/test_homes_store.py -v"],
        accepted_assertion="devices readable without identifier",
    )


_REJECT_FINDING = (
    "Every assertion in the locked test passes an explicit identifier, so the "
    "criterion about reading devices without naming a home is unproven."
)


def _reject_test_result() -> BackendResult:
    return BackendResult(
        gate=GateDecision.REJECT,
        reason="1 validator(s) returned REJECT",
        validators=[
            {
                "label": "grok-4.5",
                "model": "grok-4.5",
                "family": "grok-family",
                "verdict": "REJECT_TEST",
                "finding_text": _REJECT_FINDING,
                "envelope_path": "/tmp/reviews/review-grok-4.5-envelope.json",
            },
            {"label": "gemini-3.1-pro-preview", "verdict": "ACCEPT"},
        ],
    )


def _accept_result() -> BackendResult:
    return BackendResult(
        gate=GateDecision.ACCEPT,
        reason="all 2 validator(s) ACCEPT",
        validators=[{"label": "grok-4.5", "verdict": "ACCEPT"},
                    {"label": "gemini-3.1-pro-preview", "verdict": "ACCEPT"}],
    )


def _standalone_framework(tmp_path) -> str:
    """A minimal framework root with the REAL lock.py script and the
    sprint_loop package it imports, so lock_test exercises the true
    manifest writer without touching the repository's own lock store."""
    fw = tmp_path / "fw"
    shutil.copytree(
        os.path.join(_TOOLS, "sprint_loop"), str(fw / "tools" / "sprint_loop")
    )
    os.makedirs(fw / "tools" / "phase-1-scripts")
    shutil.copyfile(
        os.path.join(_REPO, "tools", "phase-1-scripts", "lock.py"),
        str(fw / "tools" / "phase-1-scripts" / "lock.py"),
    )
    (fw / "telemetry").mkdir()
    return str(fw)


def _manifest_path(fw: str) -> str:
    return os.path.join(
        fw, "tools", "phase-1-locks", "test", "test_homes_store.py.lock.json"
    )


def _stub_seats_with_real_lock(mod, monkeypatch, tmp_path, chunk, observed, fw):
    """The shared stub set from conftest, with the real lock_test put back.

    The 7-test suite is pre-authored on disk (as in Arm B's first round:
    the suite is already locked and the executor ran against it), so the
    test-designer only fires on the REJECT_TEST bounce and rewrites the
    suite to the 20-test redesign, exactly the Arm B sequence.
    """
    pilot = tmp_path / "pilot"
    test_abs = os.path.join(str(pilot), chunk.locked_test_files[0])
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    # Replace the stubbed lock with the REAL script, wrapped only so the
    # test can count how many times the manifest was (re)generated.
    real_lock = per_chunk.lock_test

    def counting_lock(*a, **k):
        observed["lock_test"] += 1
        return real_lock(*a, **k)

    monkeypatch.setattr(mod, "lock_test", counting_lock)

    def designer(*a, **k):
        observed["invoke_test_designer"] += 1
        os.makedirs(os.path.dirname(test_abs), exist_ok=True)
        with open(test_abs, "w") as f:
            f.write(TWENTY_TESTS)
        return {"result_text": "STATUS: TEST_AUTHORED"}

    monkeypatch.setattr(mod, "invoke_test_designer", designer)


def test_redesign_round_relocks_the_redesigned_suite(tmp_path, monkeypatch):
    """The Arm B sequence, end to end: 7-test suite locked → REJECT_TEST
    bounce → designer writes the 20-test suite → the manifest the next
    validation round reads must hash the REDESIGNED suite."""
    mod = _load_runner_module("sprint_loop_runner_lock_relock")
    fw = _standalone_framework(tmp_path)
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    # Round 1 starts where Arm B did: the 7-test suite is already on
    # disk and gets locked before the first validation.
    (pilot / "test" / "test_homes_store.py").write_text(SEVEN_TESTS)
    rs = _run_state(str(pilot), framework_root=fw)
    rs.pilot_python = "/usr/bin/python3"  # the REAL lock.py must run
    chunk = _chunk()
    observed = _observed()
    _stub_seats_with_real_lock(mod, monkeypatch, tmp_path, chunk, observed, fw)
    results = [_reject_test_result(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    final = mod.run_chunk_with_retries(rs, chunk, str(tmp_path / "ev"), False, Config())

    # The lock step ran twice: once for the 7-test suite, once after the
    # redesign — and the manifest now records the REDESIGNED SHA, which
    # is what the next validation round's SHA cross-check reads.
    assert observed["lock_test"] == 2
    assert observed["invoke_test_designer"] == 1  # the bounce only
    manifest = json.load(open(_manifest_path(fw)))
    assert manifest["sha256"] == _sha256_of(TWENTY_TESTS)
    assert manifest["sha256"] != _sha256_of(SEVEN_TESTS)
    # This is the field the validation round cross-checks the bundle's
    # locked_test_sha_observed against; it must equal the redesigned
    # suite's SHA, which is exactly what Arm B observed as stale.
    assert chunk.locked_test_sha == _sha256_of(TWENTY_TESTS)
    assert final.status.value == "ACCEPTED"


def test_resume_mid_bounce_relocks_after_the_designer_reruns(tmp_path, monkeypatch):
    """A checkpoint written mid-bounce restores rejection_kind="test";
    the resumed round re-fires the designer and the real lock step
    regenerates the manifest from the redesigned suite."""
    mod = _load_runner_module("sprint_loop_runner_lock_relock_resume")
    fw = _standalone_framework(tmp_path)
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    # The pre-checkpoint state: round 1 authored + locked a 7-test
    # suite, validation bounced it. The superseded test was archived out
    # of the pilot tree by archive_superseded_test before the pause.
    (pilot / "test" / "test_homes_store.py").write_text(SEVEN_TESTS)

    rs = _run_state(str(pilot), framework_root=fw)
    rs.pilot_python = "/usr/bin/python3"  # the REAL lock.py must run
    rs.retry_threshold = 1
    chunk = _chunk()
    chunk.rejection_kind = "test"
    chunk.test_design_feedback = [_REJECT_FINDING]
    chunk.test_design_retry_count = 0  # the bounce itself is unspent
    rs.chunks = [chunk]

    mod.write_checkpoint(rs, str(tmp_path / "checkpoint.json"))
    restored = mod.load_checkpoint(str(tmp_path / "checkpoint.json"))
    assert restored.chunks[0].rejection_kind == "test"

    observed = _observed()
    observed["invoke_test_designer"] = 1  # the pre-checkpoint design round
    _stub_loop(
        mod, monkeypatch, restored.chunks[0], tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    monkeypatch.setattr(mod, "lock_test", per_chunk.lock_test)
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: _accept_result())

    def designer(*a, **k):
        observed["invoke_test_designer"] += 1
        test_abs = os.path.join(str(pilot), chunk.locked_test_files[0])
        os.makedirs(os.path.dirname(test_abs), exist_ok=True)
        with open(test_abs, "w") as f:
            f.write(TWENTY_TESTS)
        return {"result_text": "STATUS: TEST_AUTHORED"}

    monkeypatch.setattr(mod, "invoke_test_designer", designer)

    final = mod.run_chunk_with_retries(
        restored, restored.chunks[0], str(tmp_path / "ev"), False, Config()
    )

    manifest = json.load(open(_manifest_path(fw)))
    assert manifest["sha256"] == _sha256_of(TWENTY_TESTS)
    assert restored.chunks[0].locked_test_sha == _sha256_of(TWENTY_TESTS)
    assert final.status.value == "ACCEPTED"
