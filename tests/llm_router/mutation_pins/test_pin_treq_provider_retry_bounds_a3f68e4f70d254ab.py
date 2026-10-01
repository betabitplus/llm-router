# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS a3f68e4f70d254ab
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
"""Unit test for async provider retry bounds and reraise contract."""

from __future__ import annotations

import pytest

from llm_router._api.errors import ProviderError
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_async_retrying

pytestmark = pytest.mark.verification_kind("unit")


class RetryableCauseError(Exception):
    """Private error cause flagged as retryable."""

    retryable: bool = True


class QuietLogger:
    """Logger that drops warnings."""

    def warning(self, event: str, **values: object) -> None:
        del event, values


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==3]")
async def test_async_retry_reraises_provider_error_on_exhaustion() -> None:
    policy = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=3)
    retrying = build_provider_async_retrying(policy=policy, logger=QuietLogger())
    attempts = 0

    async def failing_operation() -> None:
        nonlocal attempts
        attempts += 1
        raise ProviderError(
            RetryableCauseError("temporary cause"),
            "test_provider",
            "test_model",
            message="temporary provider error",
        )

    with pytest.raises(ProviderError, match=r"temporary provider error"):
        await retrying(failing_operation)

    assert attempts == 3
