# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS a3f68e4f70d254ab
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from typing import Any

import pytest

from llm_router._api.errors import ProviderError
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_async_retrying

pytestmark = pytest.mark.verification_kind("unit")


class RetryableCauseError(Exception):
    """Error cause indicating a retryable provider failure."""

    retryable = True


class DummyRetryLogger:
    """Minimal logger implementation for retrying tests."""

    def warning(self, event: str, **values: Any) -> None:
        del event, values


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==2]")
async def test_provider_async_retrying_reraises_original_error() -> None:
    call_count = 0
    policy = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=3)
    error = ProviderError(
        RetryableCauseError(),
        "dummy_provider",
        "dummy_model",
        message="rate limit exceeded",
    )
    retrying = build_provider_async_retrying(policy=policy, logger=DummyRetryLogger())

    async def failing_provider_call() -> None:
        nonlocal call_count
        call_count += 1
        raise error

    with pytest.raises(ProviderError, match=r"rate limit exceeded"):
        await retrying(failing_provider_call)

    assert call_count == policy.max_attempts
