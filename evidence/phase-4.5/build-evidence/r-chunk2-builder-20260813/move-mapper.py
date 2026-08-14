#!/usr/bin/env python3
"""chunk-D1-2 move mapper. Computes destination for every tracked phase-*/ file
per CHUNK-2-SPEC §2.1 + PLAN §4, asserts total coverage and zero collisions,
then emits (or executes) git mv operations.

Leaf rule (PLAN §4:133-136): leaf subdir names are preserved under the new
root, EXCEPT a leaf literally named `evidence`, which is absorbed by the
`evidence/` root (PLAN §4:171 "schema JSONs stay in evidence/phase-3.2/").
"""
import os
import subprocess
import sys

DRY = "--apply" not in sys.argv

# --- whole-directory moves: src prefix -> dst prefix ------------------------
DIR_MOVES = [
    ("phase-0/evidence/", "evidence/phase-0/"),                       # leaf absorbed
    ("phase-1/build-evidence/", "evidence/phase-1/build-evidence/"),
    ("phase-1/prompts/", "planning/phase-1/prompts/"),
    ("phase-1/hooks/", "tools/phase-1-hooks/"),
    ("phase-1/scripts/", "tools/phase-1-scripts/"),
    ("phase-1/probes/", "tools/phase-1-probes/"),
    ("phase-1/locks/", "tools/phase-1-locks/"),
    ("phase-1/fixtures/", "tests/fixtures/phase-1/"),
    ("phase-2/build-evidence/", "evidence/phase-2/build-evidence/"),
    ("phase-2/reviews/", "planning/phase-2/reviews/"),                # GAP: all 3 are .md prompts
    ("phase-3/build-evidence/", "evidence/phase-3/build-evidence/"),
    ("phase-3/reviews/", "evidence/phase-3/reviews/"),                # GAP: only .gitkeep
    ("phase-3/prompts/", "planning/phase-3/prompts/"),
    ("phase-3.1/build-evidence/", "evidence/phase-3.1/build-evidence/"),
    ("phase-3.1/prompts/", "planning/phase-3.1/prompts/"),
    ("phase-3.1/locks/", "tools/phase-3.1-locks/"),
    ("phase-3.2/build-evidence/", "evidence/phase-3.2/build-evidence/"),
    ("phase-4/h-ci/", "evidence/phase-4/h-ci/"),
    ("phase-4/h3/", "evidence/phase-4/h3/"),
    ("phase-4/demo/", "planning/phase-4/demo/"),
    ("phase-4.5/build-evidence/", "evidence/phase-4.5/build-evidence/"),
    ("phase-4.5/tokens/", "evidence/phase-4.5/tokens/"),
    ("phase-4.5/prompts/", "planning/phase-4.5/prompts/"),
    ("phase-4.5/adversarial_review/", "planning/phase-4.5/adversarial_review/"),
    ("phase-5/prompts/", "planning/phase-5/prompts/"),
    ("phase-5/scripts/", "tools/phase-5-scripts/"),
]

# --- explicit per-file moves (split subtrees + loose code files) ------------
FILE_MOVES = {
    # phase-3.2/evidence splits: schema JSONs -> evidence, .py -> tools
    "phase-3.2/evidence/bundle_schema_v1.json": "evidence/phase-3.2/bundle_schema_v1.json",
    "phase-3.2/evidence/security_allowlist.json": "evidence/phase-3.2/security_allowlist.json",
    "phase-3.2/evidence/consumer.py": "tools/phase-3.2-evidence/consumer.py",
    "phase-3.2/evidence/local_backend.py": "tools/phase-3.2-evidence/local_backend.py",
    "phase-3.2/evidence/token_accounting.py": "tools/phase-3.2-evidence/token_accounting.py",
    # phase-3.2/reviews splits: docs -> planning, envelopes/logs/json -> evidence
    "phase-3.2/reviews/RUN-COMMANDS.md": "planning/phase-3.2/reviews/RUN-COMMANDS.md",
    "phase-3.2/reviews/review-prompt.md": "planning/phase-3.2/reviews/review-prompt.md",
    # loose code files -> tools/phase-N-gen/
    "phase-3/gen-telemetry.py": "tools/phase-3-gen/gen-telemetry.py",
    "phase-3.1/gen-telemetry.py": "tools/phase-3.1-gen/gen-telemetry.py",
    "phase-4/gen-findings.py": "tools/phase-4-gen/gen-findings.py",
    "phase-4/reconstruct-telemetry.py": "tools/phase-4-gen/reconstruct-telemetry.py",
}


def destination(rel):
    if rel in FILE_MOVES:
        return FILE_MOVES[rel]
    for src, dst in DIR_MOVES:
        if rel.startswith(src):
            return dst + rel[len(src):]
    parts = rel.split("/")
    phase, name = parts[0], parts[-1]
    # remaining phase-3.2/reviews/** (orchestrated/ subdir, envelopes, logs)
    if rel.startswith("phase-3.2/reviews/"):
        return "evidence/phase-3.2/reviews/" + rel[len("phase-3.2/reviews/"):]
    # loose top-of-phase files
    if len(parts) == 2:
        if name.endswith("envelope.json"):
            return "evidence/%s/%s" % (phase, name)
        if name.endswith(".md"):
            return "planning/%s/%s" % (phase, name)
    return None


def main():
    out = subprocess.run(
        ["git", "ls-files", "phase-0", "phase-1", "phase-2", "phase-3",
         "phase-3.1", "phase-3.2", "phase-3.3", "phase-4", "phase-4.5", "phase-5"],
        capture_output=True, text=True, check=True,
    )
    files = [l for l in out.stdout.splitlines() if l]
    mapping, unmapped = {}, []
    for rel in files:
        dst = destination(rel)
        if dst is None:
            unmapped.append(rel)
        else:
            mapping[rel] = dst

    if unmapped:
        print("UNMAPPED (%d):" % len(unmapped))
        for u in unmapped:
            print("  " + u)
        sys.exit(1)

    seen = {}
    collisions = []
    for src, dst in mapping.items():
        if dst in seen:
            collisions.append((dst, seen[dst], src))
        seen[dst] = src
    if collisions:
        print("COLLISIONS (%d):" % len(collisions))
        for c in collisions:
            print("  %s  <-  %s  AND  %s" % c)
        sys.exit(1)

    existing = [d for d in seen if os.path.exists(d)]
    if existing:
        print("DESTINATION ALREADY EXISTS (%d):" % len(existing))
        for e in existing:
            print("  " + e)
        sys.exit(1)

    print("mapped=%d  unmapped=0  collisions=0" % len(mapping))
    if DRY:
        by_root = {}
        for dst in seen:
            by_root.setdefault("/".join(dst.split("/")[:2]), 0)
            by_root["/".join(dst.split("/")[:2])] += 1
        for k in sorted(by_root):
            print("  %5d  %s" % (by_root[k], k))
        print("\n(dry run — pass --apply to execute)")
        return

    for src in sorted(mapping):
        dst = mapping[src]
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        subprocess.run(["git", "mv", src, dst], check=True)
    print("moved %d files" % len(mapping))


main()
