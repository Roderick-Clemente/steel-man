#!/usr/bin/env python3
"""Generate telemetry/findings.jsonl from accumulated review rounds.

This is the auditable recipe that produces findings.jsonl from:
- Phase 1 review findings (encoded from meta-narrative + RUN-LEDGER)
- Phase 2 review findings (from phase-2/findings.md)
- Phase 3.1 degraded spike findings (from phase-3.1/RESULTS.md)
- Roadmap review v1 findings (from roadmap-review-cross-family-findings.json)
- Roadmap review v2 findings (from roadmap-review-v2-cross-family-findings.json)
- Post-v3 review findings (from post-v3-review-{grok,gemini}-envelope.json)
- Track execution review findings (from track-execution-review-{grok,gemini}-envelope.json)

Each finding gets a first_seen_in_panel_position:
  1 = first reviewer to surface this finding
  0 = shared (both reviewers found it)

With 2 reviewers, position is 1 (unique) or 0 (shared).
"""

import json
import os
import re
import sys

# chunk-D1-2a: the reads below were CWD-relative, so this script only worked
# when invoked from the repo root — and after the chunk-2 move the paths were
# wrong from every directory. Anchor them to the framework root derived from
# __file__ and compose through sprint_loop.config's roots.
_TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRAMEWORK_ROOT = os.path.dirname(_TOOLS_DIR)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.config import phase_path  # noqa: E402

# chunk-D1-2a: the historical `surface` labels below were also bare `phase-N/...`
# strings. They are DATA, not paths — nothing opens them — but they named
# locations that no longer exist, which makes them unresolvable to any future
# analyst reading findings.jsonl. Re-rooted onto the chunk-2 taxonomy by
# swapping the leading segment only, leaving each tail byte-identical: a
# reviewer's recorded surface is their finding, so re-rooting it is a migration
# while "correcting" the tail would be a rewrite. `phase-1/hooks/lock.py` is
# preserved as `tools/phase-1-hooks/lock.py` for exactly that reason, even
# though lock.py in fact lives in tools/phase-1-scripts/ — the imprecision is
# the reviewer's and stays theirs.

_P32_REVIEWS = phase_path(_FRAMEWORK_ROOT, "evidence", "phase-3.2", "reviews")
_P4_EVID = phase_path(_FRAMEWORK_ROOT, "evidence", "phase-4")


def ts(date_str):
    return date_str


def row(
    finding_id,
    phase,
    date,
    surface,
    category,
    severity,
    source_role,
    source_run_id,
    source_model,
    source_family,
    panel_size,
    first_seen,
    raw_text,
):
    return {
        "schema_version": "v2",
        "ts": date,
        "finding_id": finding_id,
        "phase": phase,
        "surface": surface,
        "category": category,
        "severity": severity,
        "source_role": source_role,
        "source_run_id": source_run_id,
        "source_model_id": source_model,
        "source_family": source_family,
        "panel_size_at_surfacing": panel_size,
        "first_seen_in_panel_position": first_seen,
        "raw_text_first_240": raw_text[:240],
        "verdict_blocking_total": 0,
    }


findings = []

# ============================================================
# Phase 1 — 3 rounds of 2 reviewers (grok + gemini)
# Encoded from meta-narrative.md cross-family divergence table
# ============================================================
D = "2026-07-15"  # approximate date for Phase 1 reviews

# Round 1 — Grok: 7 findings (all minor/nit), Gemini: 1 (blocking tooling)
# Grok findings (all 7 from R1)
p1_grok_r1 = [
    ("F-P1R1-G01", "correctness", "minor", "unused accepted_assertion load"),
    ("F-P1R1-G02", "correctness", "minor", "missing-invalid-signature gap"),
    ("F-P1R1-G03", "security", "minor", "fail-open-on-malformed-manifest"),
    ("F-P1R1-G04", "security", "minor", "dead SHELL_WRITE_OPERATORS surface"),
    ("F-P1R1-G05", "readability", "nit", "brittle conftest.py regex"),
    ("F-P1R1-G06", "spec-deviation", "nit", "Phase 0.5 hand-off cleanliness"),
    ("F-P1R1-G07", "spec-deviation", "nit", "test-quality: real Werkzeug behavior"),
]
for fid, cat, sev, desc in p1_grok_r1:
    findings.append(
        row(
            fid,
            "phase-1",
            D,
            "tools/phase-1-hooks/",
            cat,
            sev,
            "reviewer",
            "r-phase1-r1-grok",
            "grok-4.5",
            "grok-family",
            2,
            1,
            desc,
        )
    )

# Gemini R1: 1 blocking (tooling refusal)
findings.append(
    row(
        "F-P1R1-M01",
        "phase-1",
        D,
        "planning/phase-1/review-prompt",
        "spec-deviation",
        "blocking",
        "reviewer",
        "r-phase1-r1-gemini",
        "gemini-3.1-pro-preview",
        "gemini-family",
        2,
        1,
        "Execute tool not in --enabled-tools; refused to render judgment",
    )
)

# Round 2 — Grok: 1 blocking (python3 bypass), Gemini: 3 (hook bypasses)
# Grok R2: python3 inline-eval bypass (also found by Gemini)
findings.append(
    row(
        "F-P1R2-G01",
        "phase-1",
        D,
        "tools/phase-1-hooks/lock.py",
        "security",
        "blocking",
        "reviewer",
        "r-phase1-r2-grok",
        "grok-4.5",
        "grok-family",
        2,
        0,  # shared — Gemini also found python3
        "python3 inline-eval bypass in READ_ONLY_HEADS",
    )
)

# Gemini R2: 3 findings (glob short-circuit, python3, MultiEdit missing)
findings.append(
    row(
        "F-P1R2-M01",
        "phase-1",
        D,
        "tools/phase-1-hooks/glob-match",
        "security",
        "blocking",
        "reviewer",
        "r-phase1-r2-gemini",
        "gemini-3.1-pro-preview",
        "gemini-family",
        2,
        1,
        "glob short-circuit on basename prefilter",
    )
)
findings.append(
    row(
        "F-P1R2-M02",
        "phase-1",
        D,
        "tools/phase-1-hooks/lock.py",
        "security",
        "blocking",
        "reviewer",
        "r-phase1-r2-gemini",
        "gemini-3.1-pro-preview",
        "gemini-family",
        2,
        0,  # shared with Grok
        "python3 inline-eval bypass in READ_ONLY_HEADS",
    )
)
findings.append(
    row(
        "F-P1R2-M03",
        "phase-1",
        D,
        "tools/phase-1-hooks/multiedit",
        "security",
        "blocking",
        "reviewer",
        "r-phase1-r2-gemini",
        "gemini-3.1-pro-preview",
        "gemini-family",
        2,
        1,
        "MultiEdit missing from hook matcher",
    )
)

# Round 3 — Grok: 4 (2 major, 2 minor, 2 nit), Gemini: 1 nit
p1_grok_r3 = [
    ("F-P1R3-G01", "spec-deviation", "major", "ledger-completeness: recorded RED not re-run"),
    ("F-P1R3-G02", "spec-deviation", "major", "ledger-completeness: missing evidence row"),
    ("F-P1R3-G03", "correctness", "minor", "case-sensitivity disagreement red/green"),
    ("F-P1R3-G04", "correctness", "minor", "regex tightening needed"),
]
for fid, cat, sev, desc in p1_grok_r3:
    findings.append(
        row(
            fid,
            "phase-1",
            D,
            "planning/phase-1/",
            cat,
            sev,
            "reviewer",
            "r-phase1-r3-grok",
            "grok-4.5",
            "grok-family",
            2,
            1,
            desc,
        )
    )

findings.append(
    row(
        "F-P1R3-M01",
        "phase-1",
        D,
        "tools/phase-1-hooks/",
        "readability",
        "nit",
        "reviewer",
        "r-phase1-r3-gemini",
        "gemini-3.1-pro-preview",
        "gemini-family",
        2,
        1,
        "structurally sound, only nit on hook",
    )
)

# ============================================================
# Phase 2 — 2 stages (brief + plan), grok was finder, gemini confirmer
# Encoded from phase-2/findings.md
# ============================================================
D2 = "2026-07-20"

# Grok unique findings on plan review
findings.append(
    row(
        "F-P2-G01",
        "phase-2",
        D2,
        "planning/phase-2/plan-v1.md",
        "spec-deviation",
        "minor",
        "reviewer",
        "r-phase2-plan-grok",
        "grok-4.5",
        "grok-family",
        2,
        1,
        "Plan self-corrected 3 wrong file anchors in its own prompt",
    )
)

findings.append(
    row(
        "F-P2-G02",
        "phase-2",
        D2,
        "planning/phase-2/plan-v1.md",
        "correctness",
        "minor",
        "reviewer",
        "r-phase2-plan-grok",
        "grok-4.5",
        "grok-family",
        2,
        1,
        "Hidden scope trap: ALTER TABLE + migration runner needed for address column",
    )
)

# Gemini: 0 unique (confirmer only)

# ============================================================
# Phase 3.1 — Degraded spike: panel split
# Grok caught the same-family bias, Gemini dismissed it
# ============================================================
D3 = "2026-07-28"

findings.append(
    row(
        "F-P31-G01",
        "phase-3.1",
        D3,
        "evidence/phase-3.1/chunk-1",
        "correctness",
        "major",
        "reviewer",
        "r-phase31-c1-validator-grok-r1",
        "grok-4.5",
        "grok-family",
        2,
        1,
        "Same-family test-author encoded test-independence bias in chunk 1",
    )
)

# Gemini: dismissed the identical failure (0 findings)

# ============================================================
# Roadmap review v1 — REJECT by both
# From roadmap-review-cross-family-findings.json (Grok) + Gemini envelope
# ============================================================
D4 = "2026-08-08"

# Load Grok's structured findings
with open(os.path.join(_P32_REVIEWS, "roadmap-review-cross-family-findings.json")) as f:
    v1_data = json.load(f)

for finding in v1_data.get("findings", []):
    fid = finding.get("id", "F-RR-???")
    sev_map = {"blocker": "blocking", "high": "major", "medium": "minor", "low": "nit"}
    sev = sev_map.get(finding.get("severity", "low"), "nit")
    findings.append(
        row(
            fid,
            "phase-4",
            D4,
            finding.get("section", "ROADMAP-REVIEW.md"),
            finding.get("category", "other"),
            sev,
            "reviewer",
            "r-roadmap-v1-grok",
            "grok-4.5",
            "grok-family",
            2,
            1,
            finding.get("claim", finding.get("description", ""))[:240],
        )
    )

# Gemini v1 findings (5 findings, known from envelope parsing)
# Key save: F-RR-001 blocker caught that orchestration actually ran
gem_v1_findings = [
    (
        "F-RR-GV1-01",
        "ROADMAP-REVIEW.md §3.1",
        "other",
        "blocking",
        "orchestrate-review.py was never successfully run — telemetry has 10 rows with real decisions",
    ),
    (
        "F-RR-GV1-02",
        "ROADMAP-REVIEW.md §4",
        "other",
        "major",
        "H-CI should be Priority 1, not Priority 2 — economic fork must precede infrastructure",
    ),
    (
        "F-RR-GV1-03",
        "ROADMAP-REVIEW.md §4",
        "other",
        "minor",
        "Demo requires cost evidence to be real, not placeholder",
    ),
    (
        "F-RR-GV1-04",
        "ROADMAP-REVIEW.md §1",
        "other",
        "minor",
        "Phase 0.5 exists and is closed — not unbuilt",
    ),
    ("F-RR-GV1-05", "ROADMAP-REVIEW.md §3", "other", "minor", "Telemetry row count is 10 not 6"),
]
for fid, surface, cat, sev, desc in gem_v1_findings:
    findings.append(
        row(
            fid,
            "phase-4",
            D4,
            surface,
            cat,
            sev,
            "reviewer",
            "r-roadmap-v1-gemini",
            "gemini-3.1-pro-preview",
            "gemini-family",
            2,
            1,
            desc,
        )
    )

# ============================================================
# Roadmap review v2 — APPROVE-WITH-NITS by both
# From roadmap-review-v2-cross-family-findings.json (Grok) + Gemini envelope
# ============================================================

# Load Grok's structured findings
with open(os.path.join(_P32_REVIEWS, "roadmap-review-v2-cross-family-findings.json")) as f:
    v2_data = json.load(f)

for finding in v2_data.get("findings", []):
    fid = finding.get("id", "F-RR-v2-???")
    sev_map = {"blocker": "blocking", "high": "major", "medium": "minor", "low": "nit"}
    sev = sev_map.get(finding.get("severity", "low"), "nit")
    findings.append(
        row(
            fid,
            "phase-4",
            D4,
            finding.get("section", "ROADMAP-REVIEW.md"),
            finding.get("category", "other"),
            sev,
            "reviewer",
            "r-roadmap-v2-grok",
            "grok-4.5",
            "grok-family",
            2,
            1,
            finding.get("claim", finding.get("description", ""))[:240],
        )
    )

# Gemini v2 findings (5 findings, known from envelope parsing)
gem_v2_findings = [
    (
        "F-RR-GV2-01",
        "ROADMAP-REVIEW.md §3.13",
        "other",
        "major",
        "KI-2 validator Execute write vector needs preventive fix, not detective-only",
    ),
    (
        "F-RR-GV2-02",
        "ROADMAP-REVIEW.md §3.1",
        "other",
        "minor",
        "Orchestration needs empty envelope fail-closed handling",
    ),
    (
        "F-RR-GV2-03",
        "ROADMAP-REVIEW.md §4",
        "other",
        "major",
        "H3 not scheduled — execution-side cost thesis untested",
    ),
    (
        "F-RR-GV2-04",
        "ROADMAP-REVIEW.md §3.13",
        "other",
        "minor",
        "Evidence Provider IS the KI-2 fix — parameterize so H-CI control arm works",
    ),
    (
        "F-RR-GV2-05",
        "ROADMAP-REVIEW.md §3.2",
        "other",
        "minor",
        "Empty envelope handling already exists via JSONDecodeError — need retry logic instead",
    ),
]
for fid, surface, cat, sev, desc in gem_v2_findings:
    findings.append(
        row(
            fid,
            "phase-4",
            D4,
            surface,
            cat,
            sev,
            "reviewer",
            "r-roadmap-v2-gemini",
            "gemini-3.1-pro-preview",
            "gemini-family",
            2,
            1,
            desc,
        )
    )

# ============================================================
# Post-v3 review — APPROVE-WITH-NITS by both
# From post-v3-review-{grok,gemini}-envelope.json
# ============================================================
D5 = "2026-08-08"

# Parse Grok findings from the envelope result text
# The result text contains JSON blocks with findings

for name, model, family, run_id in [
    ("grok", "grok-4.5", "grok-family", "r-post-v3-grok"),
    ("gemini", "gemini-3.1-pro-preview", "gemini-family", "r-post-v3-gemini"),
]:
    try:
        with open(os.path.join(_P4_EVID, f"post-v3-review-{name}-envelope.json")) as f:
            env = json.load(f)
        result = env.get("result", "")
        # Extract JSON finding blocks
        json_blocks = re.findall(r'\{[^{}]*"finding_id"[^{}]*\}', result, re.DOTALL)
        for block in json_blocks:
            try:
                finding = json.loads(block)
                sev_map = {"blocker": "blocking", "high": "major", "medium": "minor", "low": "nit"}
                sev = sev_map.get(finding.get("severity", "low"), "nit")
                findings.append(
                    row(
                        finding.get("finding_id", f"F-PV3-{name}-?"),
                        "phase-4",
                        D5,
                        finding.get("location", "unknown"),
                        finding.get("category", "other"),
                        sev,
                        "reviewer",
                        run_id,
                        model,
                        family,
                        2,
                        1,
                        finding.get("description", "")[:240],
                    )
                )
            except json.JSONDecodeError:
                pass
    except FileNotFoundError:
        pass

# ============================================================
# Track execution review — Grok REJECT, Gemini APPROVE
# From track-execution-review-{grok,gemini}-envelope.json
# ============================================================
D6 = "2026-08-08"

for name, model, family, run_id in [
    ("grok", "grok-4.5", "grok-family", "r-tex-grok"),
    ("gemini", "gemini-3.1-pro-preview", "gemini-family", "r-tex-gemini"),
]:
    try:
        with open(os.path.join(_P4_EVID, f"track-execution-review-{name}-envelope.json")) as f:
            env = json.load(f)
        result = env.get("result", "")
        json_blocks = re.findall(r'\{[^{}]*"finding_id"[^{}]*\}', result, re.DOTALL)
        for block in json_blocks:
            try:
                finding = json.loads(block)
                sev_map = {"blocker": "blocking", "high": "major", "medium": "minor", "low": "nit"}
                sev = sev_map.get(finding.get("severity", "low"), "nit")
                findings.append(
                    row(
                        finding.get("finding_id", f"F-TEX-{name}-?"),
                        "phase-4",
                        D6,
                        finding.get("location", "unknown"),
                        finding.get("category", "other"),
                        sev,
                        "reviewer",
                        run_id,
                        model,
                        family,
                        2,
                        1,
                        finding.get("description", "")[:240],
                    )
                )
            except json.JSONDecodeError:
                pass
    except FileNotFoundError:
        pass

# ============================================================
# Write findings.jsonl
# ============================================================
out_path = os.path.join(_FRAMEWORK_ROOT, "telemetry", "findings.jsonl")
with open(out_path, "w") as f:
    for r in findings:
        f.write(json.dumps(r) + "\n")

print(f"Wrote {len(findings)} findings to {out_path}")

# Summary stats
from collections import Counter  # noqa: E402

by_model = Counter(r["source_model_id"] for r in findings)
by_family = Counter(r["source_family"] for r in findings)
by_unique = Counter((r["source_model_id"], r["first_seen_in_panel_position"]) for r in findings)
by_severity = Counter(r["severity"] for r in findings)

print(f"\nBy model: {dict(by_model)}")
print(f"By family: {dict(by_family)}")
print(f"By severity: {dict(by_severity)}")

grok_unique = sum(
    1
    for r in findings
    if r["source_model_id"] == "grok-4.5" and r["first_seen_in_panel_position"] == 1
)
gemini_unique = sum(
    1
    for r in findings
    if r["source_model_id"] == "gemini-3.1-pro-preview" and r["first_seen_in_panel_position"] == 1
)
shared = sum(1 for r in findings if r["first_seen_in_panel_position"] == 0)

print(f"\nGrok unique: {grok_unique}")
print(f"Gemini unique: {gemini_unique}")
print(f"Shared: {shared}")
print(f"Total: {len(findings)}")
