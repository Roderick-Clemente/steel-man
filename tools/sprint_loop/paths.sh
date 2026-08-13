# tools/sprint_loop/paths.sh — sourced by fire-design-review.sh
#
# Shell mirror of the layout roots (CHUNK-1-SPEC §2.1/§2.4). Sourced, never
# executed, so it sets variables and does nothing else.
#
# Deliberately NOT a 1:1 mirror of the seven Python constants: only
# EVIDENCE_ROOT is one of them. BUILD_EVIDENCE_REL mirrors the derived Python
# constant of the same name, and PHASE5_SCRIPTS_ROOT has no Python consumer.
# This file carries exactly what fire-design-review.sh composes with, no more.
#
# Today's layout (Chunk 1 defaults). Chunk 2 flips these.

EVIDENCE_ROOT=""                                # → "evidence" in Chunk 2
BUILD_EVIDENCE_REL="phase-4.5/build-evidence"   # segment; unchanged by Chunk 2
PHASE5_SCRIPTS_ROOT="phase-5/scripts"           # → "tools/phase-5-scripts" in Chunk 2

export EVIDENCE_ROOT BUILD_EVIDENCE_REL PHASE5_SCRIPTS_ROOT
