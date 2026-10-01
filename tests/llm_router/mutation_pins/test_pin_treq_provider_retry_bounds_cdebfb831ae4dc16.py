# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS cdebfb831ae4dc16
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router._api.errors import ProviderError
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_retrying

pytestmark = pytest.mark.verification_kind("unit")


class RetryableCauseError(Exception):
    """Private-style provider cause flagged as retryable."""

    retryable: bool = True


class RecordingLogger:
    """Collect retry warning events emitted between attempts."""

    def __init__(self) -> None:
        self.events: list[str] = []

    def warning(self, event: str, **values: object) -> None:
        del values
        self.events.append(event)


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==2]")
def test_sync_exhausted_retry_surfaces_last_provider_error() -> None:
    max_attempts = 3
    policy = RetryPolicy(
        min_wait_seconds=0.0,
        max_wait_seconds=0.0,
        max_attempts=max_attempts,
    )
    retry_logger = RecordingLogger()
    retrying = build_provider_retrying(policy=policy, logger=retry_logger)
    raised: list[ProviderError] = []

    def operation() -> None:
        error = ProviderError(
            RetryableCauseError("upstream overloaded"),
            "openrouter",
            "deepseek-v3",
            message=f"provider outage on attempt {len(raised) + 1}",
        )
        raised.append(error)
        raise error

    with pytest.raises(ProviderError, match=r"provider outage on attempt 3") as info:
        retrying(operation)

    assert len(raised) == max_attempts
    assert info.value is raised[-1]
    assert len(retry_logger.events) == max_attempts - 1
