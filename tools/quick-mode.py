#!/usr/bin/env python3
"""Quick mode: one cross-family review round, no sprint loop.

For work where the full runner is more ceremony than the change needs
(config swaps, prompt edits, docs), keep the two invariants that catch the
most and drop the rest:

  kept     family separation (MODEL_FAMILY_MAP), fresh blind context (the
           rendered role prompt + artifact + context files, never the
           author's reasoning), read-only seats, envelopes on disk, a
           fail-closed verdict parse against the shared vocab
  dropped  test designer, locked tests, valid-RED, EvidenceBundle, HMAC
           chunk tokens, plan-lint, telemetry rows

Seats fan out in parallel through tools/run-review.sh, one per family.

    python3 tools/quick-mode.py plan <sprint> <artifact> [context ...] \\
        --author claude-opus-5 [--reviewers a,b,c] [--cwd REPO] [--effort high]

Modes: ``plan`` renders prompts/plan-reviewer.md (reviewers attack a plan;
verdicts APPROVE | APPROVE-WITH-NITS | REJECT). ``diff`` renders
prompts/validator.md (validators judge a change; ACCEPT | ACCEPT-WITH-NITS
pass, any other validator verdict blocks).

Exit: 0 gate passed, 1 gate blocked (a blocking verdict, an error envelope,
or no parseable verdict), 2 bad args or family violation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from sprint_loop.config import MODEL_FAMILY_MAP  # noqa: E402
from sprint_loop.prompts.render import render  # noqa: E402
from sprint_loop.vocab import (  # noqa: E402
    PLAN_REVIEW_VERDICTS,
    VALIDATOR_VERDICTS,
    VERDICT_ACCEPT,
    VERDICT_ACCEPT_WITH_NITS,
    VERDICT_APPROVE,
    VERDICT_APPROVE_WITH_NITS,
    tagged_line_pattern,
)

DEFAULT_REVIEWERS = "gpt-6-sol,gemini-3.1-pro-preview,grok-4.7,kimi-k3,deepseek-v4-pro,glm-5.3"
DEFAULT_OUT_ROOT = Path.home() / ".steel-man" / "reviews"

MODES = {
    "plan": {
        "template": TOOLS / "sprint_loop" / "prompts" / "plan-reviewer.md",
        "verdicts": PLAN_REVIEW_VERDICTS,
        "passing": {VERDICT_APPROVE, VERDICT_APPROVE_WITH_NITS},
    },
    "diff": {
        "template": TOOLS / "sprint_loop" / "prompts" / "validator.md",
        "verdicts": VALIDATOR_VERDICTS,
        "passing": {VERDICT_ACCEPT, VERDICT_ACCEPT_WITH_NITS},
    },
}

QUICK_PREAMBLE = """\
> **QUICK MODE.** This is a single cross-family review round, not a full
> sprint. There is no locked test, no EvidenceBundle, no lock manifest, and
> no PRD. Wherever the role text below refers to those, treat it as
> not applicable and judge the ARTIFACT against the CONTEXT files that
> follow it. You are read-only: you may read files and run read-only
> commands in the working directory to check claims; you cannot modify
> anything. Be adversarial: find what will make this fail. Do not invent
> findings to look thorough. Your role text says what to emit on the
> VERDICT line; that line is the only thing the gate reads.

"""


def die(msg: str) -> None:
    print(f"quick-mode: {msg}", file=sys.stderr)
    sys.exit(2)


def family(model_id: str) -> str:
    return MODEL_FAMILY_MAP.get(model_id, ("unknown", "unknown"))[1]


def check_panel(author: str, seats: list[str]) -> None:
    author_family = family(author)
    if author_family == "unknown":
        die(f"author {author!r} not in MODEL_FAMILY_MAP (tools/sprint_loop/config.py)")
    seen: dict[str, str] = {}
    for seat in seats:
        fam = family(seat)
        if fam == "unknown":
            die(f"reviewer {seat!r} not in MODEL_FAMILY_MAP; add it rather than guess")
        if fam == author_family:
            die(f"reviewer {seat!r} shares the author's family ({fam})")
        if fam in seen:
            die(f"{seen[fam]!r} and {seat!r} are both {fam}; one family is one opinion")
        seen[fam] = seat


def next_round(sprint_dir: Path) -> str:
    n = 1
    while (sprint_dir / f"round{n}").exists():
        n += 1
    return f"round{n}"


def render_prompt(mode: str, seat_index: int, artifact: Path, contexts: list[Path], cwd: Path) -> str:
    first_context = str(contexts[0]) if contexts else "n/a"
    na = "n/a (quick mode)"
    body = render(
        str(MODES[mode]["template"]),
        {
            # plan-reviewer.md
            "plan_doc_path": str(artifact),
            "pilot_spec_path": first_context,
            "panel_position": str(seat_index),
            # validator.md
            "chunk_spec": f"see ARTIFACT and CONTEXT below ({first_context})",
            "branch": na,
            "commit": na,
            "pilot_root": str(cwd),
            "test_file_path": na,
            "evidence_bundle_path": na,
        },
    )
    parts = [QUICK_PREAMBLE, body]
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    parts.append(f"\n\n{'=' * 60}\nARTIFACT UNDER REVIEW: {artifact}\nsha256: {digest}\n{'=' * 60}\n\n")
    parts.append(artifact.read_text())
    for ctx in contexts:
        parts.append(f"\n\n{'=' * 60}\nCONTEXT: {ctx}\n{'=' * 60}\n\n")
        parts.append(ctx.read_text())
    return "".join(parts)


def parse_seat(envelope_path: Path, verdicts: tuple[str, ...]) -> tuple[str, str, int | None]:
    """Return (verdict, result_text, seconds). Fail closed on anything odd."""
    try:
        env = json.loads(envelope_path.read_text())
    except (OSError, ValueError):
        return "NO_ENVELOPE", "", None
    seconds = int(env["duration_ms"] / 1000) if isinstance(env.get("duration_ms"), (int, float)) else None
    # Only an explicit False is a clean run; a missing is_error is not success
    # (the fake-pass finding in tools/KNOWN-ISSUES.md).
    if env.get("is_error") is not False:
        return "ERROR", str(env.get("result") or ""), seconds
    text = str(env.get("result") or "")
    pattern = re.compile(tagged_line_pattern("VERDICT", verdicts))
    found = None
    for line in text.splitlines():
        m = pattern.match(line.strip().strip("`*").strip())
        if m:
            found = m.group(1)
    return (found or "NO_VERDICT"), text, seconds


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=sorted(MODES))
    ap.add_argument("sprint", help="review topic; rounds accumulate under <out-root>/<sprint>/")
    ap.add_argument("artifact", type=Path)
    ap.add_argument("context", nargs="*", type=Path)
    ap.add_argument("--author", required=True, help="model id that wrote the artifact")
    ap.add_argument("--reviewers", default=DEFAULT_REVIEWERS)
    ap.add_argument("--cwd", type=Path, default=Path.cwd(), help="repo the seats may read")
    ap.add_argument("--effort", default="", help="reasoning effort for every seat")
    ap.add_argument(
        "--out-root",
        type=Path,
        default=Path(os.environ.get("STEEL_MAN_REVIEWS", DEFAULT_OUT_ROOT)),
        help="outside this repo by default, so private work never lands in evidence/",
    )
    ap.add_argument("--timeout", type=int, default=1200, help="seconds per seat")
    args = ap.parse_args()

    for p in [args.artifact, *args.context]:
        if not p.is_file() or p.stat().st_size == 0:
            die(f"missing or empty: {p}")
    seats = [s.strip() for s in args.reviewers.split(",") if s.strip()]
    if not seats:
        die("no reviewers")
    check_panel(args.author, seats)

    artifact = args.artifact.resolve()
    contexts = [c.resolve() for c in args.context]
    cwd = args.cwd.resolve()
    sprint_dir = args.out_root.resolve() / args.sprint
    round_name = next_round(sprint_dir)
    round_dir = sprint_dir / round_name
    round_dir.mkdir(parents=True)

    print(f"{args.sprint} {round_name}: {args.mode} review of {artifact}")
    print(f"author {args.author} [{family(args.author)}]; seats read {cwd} read-only")
    env_base = {
        **os.environ,
        "REVIEW_OUT_ROOT": str(args.out_root.resolve()),
        "REVIEW_ROUND": round_name,
        "REVIEW_AUTO": "none",
        "REVIEW_EFFORT": args.effort,
    }
    procs = {}
    start = time.time()
    for i, seat in enumerate(seats, 1):
        prompt = round_dir / f"prompt-{seat}.md"
        prompt.write_text(render_prompt(args.mode, i, artifact, contexts, cwd))
        procs[seat] = subprocess.Popen(
            ["timeout", str(args.timeout), "bash", str(TOOLS / "run-review.sh"), seat, str(prompt), args.sprint],
            cwd=cwd,
            env=env_base,
        )
        print(f"  seat {i}: {seat} [{family(seat)}]")

    passing = MODES[args.mode]["passing"]
    rows, sections, blocked = [], [], False
    for seat, proc in procs.items():
        rc = proc.wait()
        verdict, text, secs = parse_seat(round_dir / f"review-{seat}-envelope.json", MODES[args.mode]["verdicts"])
        if rc != 0 and verdict not in passing:
            verdict = f"{verdict} (rc={rc})"
        ok = verdict in passing
        blocked |= not ok
        print(f"  {seat:26} {verdict}")
        rows.append(f"| `{seat}` | {family(seat)} | {verdict} | {secs if secs is not None else '?'} |")
        sections.append(f"\n---\n\n## {seat}\n\n{text or f'_no output; see review-{seat}-stderr.log_'}\n")

    gate = "BLOCKED" if blocked else "PASS"
    summary = round_dir / "SUMMARY.md"
    summary.write_text(
        f"# {args.sprint} {round_name} ({args.mode} review)\n\n"
        f"Author `{args.author}`. Artifact `{artifact}`.\n\n"
        "| Seat | Family | Verdict | Seconds |\n|---|---|---|---|\n"
        + "\n".join(rows)
        + f"\n\n**Gate: {gate}**\n"
        + "".join(sections)
    )
    print(f"wall clock {int(time.time() - start)}s; GATE: {gate}")
    print(f"findings: {summary}")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
