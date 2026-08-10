#!/usr/bin/env python3
"""Refusal-at-parse cross-family review gate (PRD §11 Phase 5 deliverable #2).

The runner feeds this module:

  * ``--implementer-model-id``     — who authored the chunk.
  * ``--reviewer-models``           — comma-separated list (≥2 expected).
  * ``--reviewers-verdicts-json``   — JSON list of verdicts, same length.
  * ``--reviewers-envelope-sha256s`` — JSON list of envelope SHAs.

Refuses (exit 6) at parse time if any of:

  * reviewer list empty (or fewer than 2 — dual-ACCEPT invariant)
  * any reviewer family equals implementer family (MODEL_FAMILY_MAP lookup)
  * any reviewer family is ``"unknown"`` (curated map does not list it)
  * any reviewer verdict is not in ACCEPT-CLASS (ACCEPT or ACCEPT-WITH-NITS)

Only emits ``chunk-N.token.json`` (via ``tools.sign_chunk_token.build_token``)
when ALL reviewers pass every check. The token, not the verdict alone,
is the durable artifact the chunk-close path needs (HMAC verifies under
``EVIDENCE_SIGNING_KEY``).

Composition (OPERATING-RULES §18): MODEL_FAMILY_MAP is reused from
``tools/sprint_loop/config.py``. No family taxonomy is invented here.

Failure mode (KNOWN-ISSUES KN-14 family collision; chunk-14 pass-r5
lesson): the chunk-14 reviewer was two same-family subagents and reached
ACCEPT-WITH-NITS — this module refuses at parse so that scenario
becomes structure, not luck.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from typing import Any

# Make ``tools/`` importable for both ``python -m`` and direct-script runs.
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.config import MODEL_FAMILY_MAP  # noqa: E402
import sign_chunk_token as sct  # noqa: E402


ACCEPT_CLASS: frozenset[str] = sct.ACCEPT_CLASS

# Placeholder-envelope detector (KN-A-5): build agents tend to type
# fixture-marker sha256 values like "5555555555555555555555...5501"
# (all-5 leading run + suffix). Real envelope_sha256 values are
# produced by hashlib.sha256 over raw model output; the leading 50
# characters have ~uniform distribution, so a 50-character
# homogeneous run is effectively impossible (probability ~2^-200).
# This asymmetry is the gate's leverage against the §17.2
# implementation-pattern (KN-A-5 / design-doc §10).
PLACEHOLDER_LEADING_RUN_MIN: int = 50


def envelope_is_placeholder(sha: str) -> bool:
    """True if ``sha`` looks like a fixture-marker, not a real sha256.

    Refuses: any ``sha`` where the first ``PLACEHOLDER_LEADING_RUN_MIN``
    hex characters are all identical. Also refuses on length-mismatch
    and non-hex-character inputs — bad SHAs are also placeholders for
    our purposes (no real `droid exec` envelope hashes to them).
    """
    if not isinstance(sha, str):
        return True
    if len(sha) != 64:
        return True
    if not all(c in "0123456789abcdef" for c in sha):
        # permissive on lower-case only; real sha256 hex digests are
        # conventionally lowercase, so an uppercase-but-other-wise-valid
        # input is a typing error worth refusing rather than silently
        # normalising.
        return True
    head = sha[:PLACEHOLDER_LEADING_RUN_MIN]
    return len(set(head)) == 1


@dataclasses.dataclass(frozen=True)
class RefusalLog:
    """One refusal per call; the gate logs and exits 6."""
    reason: str
    reviewer_index: int = -1  # -1 = not reviewer-specific


def family_of(model_id: str) -> tuple[str, str]:
    """(provider, family) for ``model_id``; 'unknown' if not in map.

    Curated only — never infer. PRD §4: provenance is curated, not
    guessed. Mirrors ``Config.provider_family`` exactly so the gate
    and the runner cannot disagree.
    """
    if model_id in MODEL_FAMILY_MAP:
        return MODEL_FAMILY_MAP[model_id]
    return ("unknown", "unknown")


def check_reviewer_panel(
    *,
    implementer_model_id: str,
    reviewer_model_ids: list[str],
    reviewer_verdicts: list[str],
    reviewer_envelope_sha256s: list[str],
) -> list[RefusalLog]:
    """Pure refusal-list producer. No I/O, no exit codes — callers
    (CLI + future runner integration) decide what to do with the list.

    Composition: purity preserves the §7 audit-trail principle (the
    refusal list IS the trail; sign_chunk_token's HMAC binds it to
    the operator's key).
    """
    refusals: list[RefusalLog] = []
    if not reviewer_model_ids:
        refusals.append(RefusalLog(reason="reviewer list empty"))
        return refusals
    if len(reviewer_model_ids) < 2:
        refusals.append(RefusalLog(
            reason=f"need ≥2 reviewers for cross-family invariant; got {len(reviewer_model_ids)}",
        ))
    if len(reviewer_verdicts) != len(reviewer_model_ids):
        refusals.append(RefusalLog(
            reason=f"verdict count {len(reviewer_verdicts)} does not match reviewer count {len(reviewer_model_ids)}",
        ))
    if len(reviewer_envelope_sha256s) != len(reviewer_model_ids):
        refusals.append(RefusalLog(
            reason=f"envelope-sha256 count {len(reviewer_envelope_sha256s)} does not match reviewer count {len(reviewer_model_ids)}",
        ))

    impl_provider, impl_family = family_of(implementer_model_id)
    if impl_family == "unknown":
        refusals.append(RefusalLog(
            reason=f"implementer model {implementer_model_id!r} has no curated family — refusing pre-§17.2",
        ))

    for i, model_id in enumerate(reviewer_model_ids):
        provider, family = family_of(model_id)
        if family == "unknown":
            refusals.append(RefusalLog(
                reason=f"reviewer[{i}]={model_id!r}: family=unknown (curated MODEL_FAMILY_MAP does not list it)",
                reviewer_index=i,
            ))
        elif family == impl_family:
            refusals.append(RefusalLog(
                reason=f"reviewer[{i}]={model_id!r}: family={family} collides with implementer family={impl_family} — same-family reviews do not satisfy §17.2",
                reviewer_index=i,
            ))
        # envelope authenticity check (KN-A-5; design-doc §10):
        # a real envelope_sha256 is hashlib.sha256 over raw droid output;
        # a fixture marker has a 50-char homogeneous run. Probability
        # 2^-200 of a real sha256 satisfying that constraint, so the
        # refusal rate on real reviews is ~zero.
        if i < len(reviewer_envelope_sha256s):
            sha = reviewer_envelope_sha256s[i]
            if envelope_is_placeholder(sha):
                refusals.append(RefusalLog(
                    reason=(
                        f"reviewer[{i}]={model_id!r}: envelope_sha256 looks like a "
                        f"fixture marker (KN-A-5 / design-doc §10): first "
                        f"{PLACEHOLDER_LEADING_RUN_MIN} chars are homogeneous or "
                        f"sha is non-canonical. Compute the SHA over the real "
                        f"droid envelope output on disk; do not type a marker."
                    ),
                    reviewer_index=i,
                ))
        # verdict check below
        if i < len(reviewer_verdicts):
            verdict = reviewer_verdicts[i]
            if verdict not in ACCEPT_CLASS:
                refusals.append(RefusalLog(
                    reason=f"reviewer[{i}]={model_id!r}: verdict={verdict!r} not in ACCEPT-CLASS {sorted(ACCEPT_CLASS)}",
                    reviewer_index=i,
                ))
    return refusals


def build_cross_family_token(
    *,
    chunk_id: str,
    chunk_commit_sha: str,
    implementer_model_id: str,
    reviewer_model_ids: list[str],
    reviewer_verdicts: list[str],
    reviewer_envelope_sha256s: list[str],
    signed_by: str,
    signing_key_env: str = "EVIDENCE_SIGNING_KEY",
) -> dict[str, Any]:
    """Materialise the chunk-close token once the panel passes."""
    reviewers: list[dict[str, Any]] = []
    for i, model_id in enumerate(reviewer_model_ids):
        provider, family = family_of(model_id)
        reviewers.append({
            "family": family,
            "model_id": model_id,
            "verdict": reviewer_verdicts[i],
            "envelope_sha256": reviewer_envelope_sha256s[i],
            "provider": provider,
        })
    return sct.build_token(
        chunk_id=chunk_id,
        chunk_commit_sha=chunk_commit_sha,
        reviewers=reviewers,
        signed_by=signed_by,
        signing_key_env=signing_key_env,
    )


# ── CLI ─────────────────────────────────────────────────────────────────

def _cli_main(args: argparse.Namespace) -> int:
    reviewer_model_ids = [m.strip() for m in args.reviewer_models.split(",") if m.strip()]
    reviewer_verdicts = json.loads(args.reviewers_verdicts_json)
    reviewer_envelope_sha256s = json.loads(args.reviewers_envelope_sha256s_json)

    refusals = check_reviewer_panel(
        implementer_model_id=args.implementer_model_id,
        reviewer_model_ids=reviewer_model_ids,
        reviewer_verdicts=reviewer_verdicts,
        reviewer_envelope_sha256s=reviewer_envelope_sha256s,
    )

    if refusals:
        for r in refusals:
            print(r.reason, file=sys.stderr)
        print(
            f"cross_family_review: REFUSED — {len(refusals)} check(s) failed "
            f"for chunk={args.chunk_id}",
            file=sys.stderr,
        )
        return 6

    token = build_cross_family_token(
        chunk_id=args.chunk_id,
        chunk_commit_sha=args.chunk_commit_sha,
        implementer_model_id=args.implementer_model_id,
        reviewer_model_ids=reviewer_model_ids,
        reviewer_verdicts=reviewer_verdicts,
        reviewer_envelope_sha256s=reviewer_envelope_sha256s,
        signed_by=args.signed_by,
        signing_key_env=args.signing_key_env,
    )
    out = args.out
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w") as f:
        json.dump(token, f, indent=2, sort_keys=True)
        f.write("\n")
    print(
        f"cross_family_review: OK chunk={args.chunk_id} "
        f"implementer={args.implementer_model_id} reviewers={len(reviewer_model_ids)} "
        f"-> wrote {out}",
        file=sys.stderr,
    )
    return 0


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cross_family_review",
        description="Refusal-at-parse dual-ACCEPT cross-family gate (§17.2 / PRD §11 Phase 5 #2).",
    )
    p.add_argument("--implementer-model-id", required=True)
    p.add_argument("--reviewer-models", required=True,
                   help="Comma-separated reviewer model IDs (must be ≥2).")
    p.add_argument("--reviewers-verdicts-json", required=True,
                   help='JSON list of verdicts, length matches --reviewer-models.')
    p.add_argument("--reviewers-envelope-sha256s-json", required=True,
                   help='JSON list of envelope SHAs, length matches --reviewer-models.')
    p.add_argument("--chunk-id", required=True)
    p.add_argument("--chunk-commit-sha", required=True)
    p.add_argument("--signed-by", default="factory/droid@local")
    p.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")
    p.add_argument("--out", required=True, help="token path to write on acceptance")
    return p


def main(argv: list[str] | None = None) -> int:
    p = build_argparser()
    args = p.parse_args(argv)
    # Allow --reviewers-verdicts-json to also accept the alias name
    # (negotiated with build_argparser).
    if not hasattr(args, "reviewers_verdicts_json"):
        args.reviewers_verdicts_json = ""
    return _cli_main(args)


if __name__ == "__main__":
    # Bridge argparse name alias: --reviewers-verdicts-json vs
    # --reviewers-verdicts-json (above) vs the JSON-encoded shorthand.
    import argparse as _ap
    raw = sys.argv[1:]
    # If user passed --reviewers-verdicts-json (no final 's'), alias it.
    if "--reviewers-verdicts-json" in raw:
        idx = raw.index("--reviewers-verdicts-json")
        raw[idx] = "--reviewers-verdicts-json"
    sys.argv = [sys.argv[0]] + raw
    raise SystemExit(main(sys.argv[1:]))
