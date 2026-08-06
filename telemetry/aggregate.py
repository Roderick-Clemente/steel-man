#!/usr/bin/env python3
"""telemetry/aggregate.py — §13 efficacy metrics aggregator.

Reads JSONL rows from --data-dir (default $TELEMETRY_DATA_DIR or ./telemetry)
and prints three tables that feed the §13 evaluation: per-reviewer yield,
fix-rate by severity, and cost-per-finding-fixed (incl. marginal cost per
extra reviewer).

Invocation:
    python3 telemetry/aggregate.py --data-dir telemetry
    python3 telemetry/aggregate.py --schema-check
    TELEMETRY_DATA_DIR=telemetry python3 telemetry/aggregate.py

Reads paths from --data-dir; never reaches for a hard-coded private path.
The data dir is git-ignored per .gitignore; rows live here during the build
phase and move to a sister private repo or DuckDB later (see
tools/conventions/model-discipline.md "Migrating the data").
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

SCHEMA_VERSION = "v1"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fp:
        for i, line in enumerate(fp, start=1):
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as err:
                print(f"{path}:{i}: skipping malformed row ({err})", file=sys.stderr)
                continue
            rows.append(row)
    return rows


def cohort_total_tokens(run: dict) -> int:
    return int(run.get("input_tokens", 0) or 0) + int(
        run.get("output_tokens", 0) or 0
    ) + int(run.get("cache_read_tokens", 0) or 0) + int(
        run.get("thinking_tokens", 0) or 0
    )


def table_per_reviewer_yield(
    findings: list[dict], runs: list[dict]
) -> list[tuple[int, int, int, int]]:
    """Returns (panel_position, severity, count, tokens_spent)."""
    run_by_id = {r.get("run_id"): r for r in runs}
    cells: list[tuple[int, int, int, int]] = []
    by_pos: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for f in findings:
        pos = int(f.get("first_seen_in_panel_position", 0) or 0)
        sev = str(f.get("severity", "?"))
        by_pos[(pos, sev)].append(f)

    for (pos, sev), group in sorted(by_pos.items()):
        token_sum = 0
        for f in group:
            run = run_by_id.get(f.get("source_run_id"), {})
            token_sum += cohort_total_tokens(run)
        cells.append((pos, sev, len(group), token_sum))
    return cells


def table_fix_rate_by_severity(
    findings: list[dict], dispositions: list[dict]
) -> list[tuple[str, int, int]]:
    """Returns (severity, surfaced, fixed)."""
    dispo_by_id = {d.get("finding_id"): d for d in dispositions}
    cells: list[tuple[str, int, int]] = []
    by_sev: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        by_sev[str(f.get("severity", "?"))].append(f)
    for sev, group in sorted(by_sev.items()):
        fixed = sum(1 for f in group if dispo_by_id.get(f.get("finding_id"), {}).get("disposition") == "fixed")
        cells.append((sev, len(group), fixed))
    return cells


def table_cost_per_finding_fixed(
    findings: list[dict], runs: list[dict], dispositions: list[dict]
) -> tuple[int, int, int]:
    run_by_id = {r.get("run_id"): r for r in runs}
    review_tokens = 0
    fix_tokens = 0
    found_finding_count = 0
    fixed_finding_count = 0
    dispo_by_id = {d.get("finding_id"): d for d in dispositions}

    for f in findings:
        run = run_by_id.get(f.get("source_run_id"), {})
        review_tokens += cohort_total_tokens(run)
        found_finding_count += 1
        dispo = dispo_by_id.get(f.get("finding_id"), {})
        if dispo.get("disposition") == "fixed":
            fix_tokens += int(dispo.get("disposition_tokens_input", 0) or 0) + int(
                dispo.get("disposition_tokens_output", 0) or 0
            )
            fixed_finding_count += 1

    return (
        review_tokens + fix_tokens,
        found_finding_count,
        fixed_finding_count,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate telemetry for §13 efficacy evaluation."
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("TELEMETRY_DATA_DIR", "telemetry"),
        help="Path to telemetry data directory "
             "(default: $TELEMETRY_DATA_DIR or ./telemetry).",
    )
    parser.add_argument(
        "--schema-check",
        action="store_true",
        help="Verify schema_version on every row; do not print tables.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"# data dir not found: {data_dir} — nothing to aggregate yet.", file=sys.stderr)
        return 0

    runs = read_jsonl(data_dir / "runs.jsonl")
    findings = read_jsonl(data_dir / "findings.jsonl")
    dispositions = read_jsonl(data_dir / "dispositions.jsonl")

    if args.schema_check:
        bad = [
            r
            for r in (runs + findings + dispositions)
            if r.get("schema_version") != SCHEMA_VERSION
        ]
        if bad:
            print(
                f"# {len(bad)} rows have schema_version != {SCHEMA_VERSION}; "
                "stopping.",
                file=sys.stderr,
            )
            return 1
        print(f"# schema_version={SCHEMA_VERSION} ok on all rows")
        return 0

    yield_table = table_per_reviewer_yield(findings, runs)
    fix_rate_table = table_fix_rate_by_severity(findings, dispositions)
    cost_total, found_n, fixed_n = table_cost_per_finding_fixed(
        findings, runs, dispositions
    )

    print("# Per-reviewer yield (panel-position, severity, count, total-tokens)")
    if not yield_table:
        print("(no findings yet)")
    else:
        print(
            f"{'pos':>3}  {'severity':<10}  {'count':>6}  {'tokens':>10}"
        )
        for pos, sev, count, tokens in yield_table:
            print(f"{pos:>3}  {sev:<10}  {count:>6}  {tokens:>10}")

    print()
    print("# Fix rate by severity (severity, surfaced, fixed)")
    if not fix_rate_table:
        print("(no findings yet)")
    else:
        print(f"{'severity':<10}  {'surfaced':>8}  {'fixed':>6}  {'fix-rate':>9}")
        for sev, surfaced, fixed in fix_rate_table:
            rate = (fixed / surfaced) if surfaced else 0.0
            print(
                f"{sev:<10}  {surfaced:>8}  {fixed:>6}  {rate:>8.1%}"
            )

    print()
    print("# Cost per finding (review + fix tokens across all findings)")
    print(f"  total tokens : {cost_total}")
    print(f"  found        : {found_n}")
    print(f"  fixed        : {fixed_n}")
    if found_n:
        print(f"  tokens/found : {cost_total / found_n:.1f}")
    if fixed_n:
        print(f"  tokens/fixed : {cost_total / fixed_n:.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
