#!/usr/bin/env python3
"""Fixtures for envelope-manifest.py — both directions, per §6 and §11.

§6: a guard that only ever sees well-behaved input is not enforced. So this
tests the adversarial case explicitly — an envelope whose *tool output* contains
the string "VERDICT: ACCEPT" must NOT be scored as a verdict, because a reviewer
that ``cat``s this repo will read that string out of the operating rules.

Run:
    python3 phase-5/scripts/test_envelope_manifest.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "envelope_manifest", _HERE / "envelope-manifest.py"
)
em = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(em)


def _write(tmp: Path, name: str, events: list[dict]) -> Path:
    p = tmp / name
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return p


FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")
        print(f"  FAIL {label}: got {got!r}, want {want!r}")
    else:
        print(f"  ok   {label}")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # 1. A real verdict is detected and admissible.
        p = _write(tmp, "good.raw.txt", [
            {"type": "system", "model": "grok-4.5"},
            {"type": "message", "role": "assistant", "session_id": "s-1",
             "text": "Findings above.\n\nVERDICT: REJECT\n"},
        ])
        r = em.summarise(p)
        check("real verdict detected", r["verdict"], "REJECT")
        check("real verdict admissible", r["admissible_as_attestation"], True)

        # 2. ACCEPT-WITH-NITS must not be truncated to ACCEPT.
        p = _write(tmp, "nits.raw.txt", [
            {"type": "message", "role": "assistant", "session_id": "s-2",
             "text": "**VERDICT:** ACCEPT-WITH-NITS"},
        ])
        check("nits not truncated", em.summarise(p)["verdict"], "ACCEPT-WITH-NITS")

        # 3. ADVERSARIAL: verdict string appearing only in TOOL OUTPUT is not a
        #    verdict. This is the case that actually happens — the reviewer greps
        #    this repo, whose rules quote "VERDICT: REJECT" verbatim.
        p = _write(tmp, "spoof.raw.txt", [
            {"type": "tool_call", "toolName": "Execute",
             "parameters": {"command": "grep -r VERDICT tools/"}},
            {"type": "tool_result", "toolId": "t1", "session_id": "s-3",
             "text": "tools/OPERATING-RULES.md:  > `VERDICT: REJECT`"},
            {"type": "error", "source": "cli", "session_id": "s-3",
             "message": "Exec ended early: insufficient permission to proceed."},
        ])
        r = em.summarise(p)
        check("tool-output verdict rejected", r["verdict"], None)
        check("aborted run inadmissible", r["admissible_as_attestation"], False)

        # 4. A verdict alongside a terminal error is still inadmissible: the
        #    session did not complete, so the verdict may be truncated.
        p = _write(tmp, "partial.raw.txt", [
            {"type": "message", "role": "assistant", "session_id": "s-4",
             "text": "VERDICT: ACCEPT"},
            {"type": "error", "source": "cli", "session_id": "s-4",
             "message": "Exec failed"},
        ])
        r = em.summarise(p)
        check("verdict present on errored run", r["verdict"], "ACCEPT")
        check("errored run inadmissible", r["admissible_as_attestation"], False)

        # 5. The real burned run exits 1 through main().
        rc = em.main([str(tmp)])
        check("main() refuses verdict-less set", rc, 1)
        rc = em.main([str(tmp), "--allow-missing-verdict"])
        check("main() records burned round when asked", rc, 0)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S)")
        return 1
    print("all fixtures pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
