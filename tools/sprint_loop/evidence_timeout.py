"""Shared timeout budget for the local evidence producer."""

VERIFY_GREEN_TIMEOUT_SECONDS = 120
PYTEST_TIMEOUT_SECONDS = 300
COVERAGE_TIMEOUT_SECONDS = 120
BANDIT_TIMEOUT_SECONDS = 120
TOOL_VERSION_TIMEOUT_SECONDS = 10
GIT_METADATA_TIMEOUT_SECONDS = 10
EVIDENCE_TIMEOUT_GRACE_SECONDS = 60


def local_backend_timeout_seconds(*, full_suite: bool, security_scan: bool) -> int:
    """Return an outer budget that exceeds every enabled producer step."""
    inner_timeout = (
        VERIFY_GREEN_TIMEOUT_SECONDS
        + PYTEST_TIMEOUT_SECONDS
        + COVERAGE_TIMEOUT_SECONDS
        + (PYTEST_TIMEOUT_SECONDS if full_suite else 0)
        + (BANDIT_TIMEOUT_SECONDS if security_scan else 0)
        + TOOL_VERSION_TIMEOUT_SECONDS * (4 if security_scan else 3)
    )
    return inner_timeout + EVIDENCE_TIMEOUT_GRACE_SECONDS
