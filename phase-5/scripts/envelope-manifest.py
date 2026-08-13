#!/usr/bin/env python3
"""Summarise reviewer envelopes and REFUSE to call a verdict-less run a review.

Why this exists (OPERATING-RULES §7): during run ``r-drs-role-split-1`` the
orchestrator reported ``154293 total`` bytes and two ``sha256`` digests as if
they were reviewer attestations. Both sessions had in fact aborted without
rendering judgment. Byte counts and digests are properties of *files*; a verdict
is a property of *content*. Nothing in the repo asserted the difference, so the
mistake was invisible until a human read the error events.

This tool makes the distinction mechanical:

* it parses ``droid exec --output-format stream-json`` envelopes (JSONL),
* records the facts a §21 audit needs (sha256, bytes, session_id, model),
* extracts the ``VERDICT:`` line if one exists,
* and **exits non-zero when any envelope carries no verdict**, so a burned
  round cannot be laundered into evidence by a caller that only checks
  ``$?`` of the fire step.

It deliberately does NOT sign anything and does NOT compute token fields. It is
an evidence *reader*. Signing authority lives outside any agent process (§21/§22).

Usage:
    python3 phase-5/scripts/envelope-manifest.py <run-dir-or-envelope-dir> \\
        [--json out.json] [--markdown out.md] [--allow-missing-verdict]

Exit codes:
    0  every envelope carried a parseable verdict
    1  at least one envelope carried no verdict (or was unparseable)
    2  usage / no envelopes found
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

VERDICTS = ("ACCEPT-WITH-NITS", "ACCEPT", "REJECT")
# ACCEPT-WITH-NITS must be tested before ACCEPT: it contains it as a substring.
VERDICT_RE = re.compile(
    r"^\s*(?:\*\*)?VERDICT(?:\*\*)?\s*[::]\s*(?:\*\*)?\s*"
    r"(ACCEPT-WITH-NITS|ACCEPT|REJECT)",
    re.IGNORECASE | re.MULTILINE,
)


def _iter_events(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Return (events, unparseable_line_count) for a JSONL envelope."""
    events: list[dict[str, Any]] = []
    bad = 0
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            bad += 1
    return events, bad


def _assistant_text(events: list[dict[str, Any]]) -> str:
    """Concatenate assistant-authored natural language, excluding tool noise.

    Only ``message`` events with a non-user role carry reviewer prose. Tool
    results are excluded on purpose: a reviewer that ``cat``s a file containing
    the string "VERDICT: ACCEPT" must not thereby appear to have rendered one.
    """
    out: list[str] = []
    for e in events:
        if e.get("type") != "message":
            continue
        if str(e.get("role", "")).lower() == "user":
            continue
        text = e.get("text")
        if isinstance(text, str) and text.strip():
            out.append(text)
    return "\n".join(out)


def summarise(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    events, bad = _iter_events(path)
    census = Counter(str(e.get("type")) for e in events)

    session_ids = sorted({
        str(e["session_id"]) for e in events if e.get("session_id")
    })
    models = sorted({str(e["model"]) for e in events if e.get("model")})
    errors = [
        {
            "source": e.get("source"),
            "message": e.get("message"),
            "session_id": e.get("session_id"),
        }
        for e in events if e.get("type") == "error"
    ]

    text = _assistant_text(events)
    m = VERDICT_RE.search(text)
    verdict = m.group(1).upper() if m else None

    return {
        "envelope": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "events": sum(census.values()),
        "unparseable_lines": bad,
        "event_census": dict(sorted(census.items())),
        "session_ids": session_ids,
        "models": models,
        "assistant_text_chars": len(text),
        "verdict": verdict,
        "errors": errors,
        # §21 language: a digest over a verdict-less file is NOT an attestation.
        "admissible_as_attestation": bool(verdict) and not errors,
    }


def _find_envelopes(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    pats = ("*.raw.txt", "envelope*.json", "*.envelope.json")
    found: list[Path] = []
    for pat in pats:
        found.extend(sorted(root.rglob(pat)))
    # stderr sidecars are not envelopes
    return [p for p in found if ".stderr." not in p.name]


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| envelope | model | bytes | events | session_id | verdict | admissible |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            "| `{}` | {} | {} | {} | `{}` | {} | {} |".format(
                Path(r["envelope"]).name,
                ", ".join(r["models"]) or "-",
                r["bytes"],
                r["events"],
                ", ".join(r["session_ids"]) or "-",
                r["verdict"] or "**NONE**",
                "yes" if r["admissible_as_attestation"] else "**no**",
            )
        )
    lines.append("")
    lines.append("sha256:")
    lines.append("")
    for r in rows:
        lines.append(f"- `{Path(r['envelope']).name}` — `{r['sha256']}`")
    err_rows = [r for r in rows if r["errors"]]
    if err_rows:
        lines.append("")
        lines.append("Terminal errors (verbatim):")
        lines.append("")
        for r in err_rows:
            for e in r["errors"]:
                lines.append(
                    f"- `{Path(r['envelope']).name}` [{e['source']}] "
                    f"`{e['message']}`"
                )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="run dir, envelope dir, or single envelope file")
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--markdown", dest="md_out", default=None)
    ap.add_argument("--allow-missing-verdict", action="store_true",
                    help="report but do not fail on verdict-less envelopes "
                         "(for recording a burned round as burned)")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"envelope-manifest: no such path: {root}", file=sys.stderr)
        return 2

    envelopes = _find_envelopes(root)
    if not envelopes:
        print(f"envelope-manifest: no envelopes under {root}", file=sys.stderr)
        return 2

    rows = [summarise(p) for p in envelopes]
    md = render_markdown(rows)
    print(md)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(rows, indent=2) + "\n")
    if args.md_out:
        Path(args.md_out).write_text(md)

    missing = [r for r in rows if not r["verdict"]]
    if missing:
        names = ", ".join(Path(r["envelope"]).name for r in missing)
        print(
            f"envelope-manifest: NO VERDICT in {len(missing)}/{len(rows)} "
            f"envelope(s): {names}",
            file=sys.stderr,
        )
        print(
            "  These are NOT reviewer attestations. Do not SHA them into a "
            "chunk token (§21).",
            file=sys.stderr,
        )
        if not args.allow_missing_verdict:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
