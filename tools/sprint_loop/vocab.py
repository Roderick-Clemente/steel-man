"""Protocol vocabulary shared by prompts, parsers, and telemetry emitters.

These strings cross process boundaries. Keeping them here prevents one seat
from advertising a value that the receiving parser or schema does not know.
Static markdown prompts cannot import Python, so contract tests compare their
literal blocks against these tuples.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Plan-reviewer verdicts.
VERDICT_APPROVE = "APPROVE"
VERDICT_APPROVE_WITH_NITS = "APPROVE-WITH-NITS"
VERDICT_REJECT = "REJECT"
PLAN_REVIEW_VERDICTS = (
    VERDICT_APPROVE,
    VERDICT_REJECT,
    VERDICT_APPROVE_WITH_NITS,
)

# Per-chunk validator verdicts. REPLAN directs the rejection at the
# PLANNED WORK rather than the code or the locked test: the chunk stops
# fail-closed and the runner re-enters plan -> plan-review -> reconcile
# with the validator's finding rendered into the planner prompt. It was
# removed while unsupported (KI-19) and returns here with the routing,
# bounded budget, and exit code it requires.
VERDICT_ACCEPT = "ACCEPT"
VERDICT_ACCEPT_WITH_NITS = "ACCEPT-WITH-NITS"
VERDICT_REJECT_IMPLEMENTATION = "REJECT_IMPLEMENTATION"
VERDICT_REJECT_TEST = "REJECT_TEST"
VERDICT_HUMAN_DECISION = "HUMAN_DECISION"
VERDICT_REPLAN = "REPLAN"
VALIDATOR_VERDICTS = (
    VERDICT_ACCEPT,
    VERDICT_ACCEPT_WITH_NITS,
    VERDICT_REJECT_IMPLEMENTATION,
    VERDICT_REJECT_TEST,
    VERDICT_REPLAN,
    VERDICT_HUMAN_DECISION,
)
TEST_DIRECTED_VERDICTS = frozenset({VERDICT_REJECT_TEST})

# Executor result signals.
RESULT_GREEN = "GREEN"
RESULT_RED = "RED"
RESULT_SPEC_OR_TEST_BLOCKED = "SPEC_OR_TEST_BLOCKED"
EXECUTOR_RESULT_SIGNALS = (
    RESULT_GREEN,
    RESULT_RED,
    RESULT_SPEC_OR_TEST_BLOCKED,
)

# Per-seat telemetry phase_step values.
PHASE_PLAN = "plan"
PHASE_PLAN_REPLAN = "plan-replan"
PHASE_PLAN_REVIEW = "plan-review"
PHASE_TEST_DESIGN = "test-design"
PHASE_TEST_DESIGN_RERUN = "test-design-rerun"
PHASE_EXECUTE = "execute"
PHASE_STEPS = (
    PHASE_PLAN,
    PHASE_PLAN_REPLAN,
    PHASE_PLAN_REVIEW,
    PHASE_TEST_DESIGN,
    PHASE_TEST_DESIGN_RERUN,
    PHASE_EXECUTE,
)


def tagged_line_pattern(tag: str, values: Iterable[str]) -> str:
    """Return an anchored regex for one tagged protocol line.

    Values are longest-first so a prefix such as ``ACCEPT`` cannot consume
    ``ACCEPT-WITH-NITS``. Callers choose flags and extract capture group 1.
    """
    alternatives = "|".join(
        re.escape(value) for value in sorted(values, key=len, reverse=True)
    )
    return rf"^{re.escape(tag)}:\s*({alternatives})\s*$"
