# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS af31395bc89f6b7e
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import typing

import pytest

from llm_router._api.errors import ProviderError
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_async_retrying

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==3]")
async def test_async_retrying_does_not_retry_permanent_provider_error() -> None:
    policy = RetryPolicy(
        min_wait_seconds=1.0,
        max_wait_seconds=2.0,
        max_attempts=3,
    )
    events: list[dict[str, typing.Any]] = []
    retryer = build_provider_async_retrying(
        policy=policy,
        logger=None,
        context_getter=None,
        state_sink=events.append,
    )
    error = ProviderError(
        cause=ValueError("bad request"),
        provider="test_provider",
        model="test_model",
        message="permanent provider error",
    )
    attempts = 0

    async def call_provider() -> None:
        nonlocal attempts
        attempts += 1
        raise error

    with pytest.raises(ProviderError, match=r"permanent provider error") as info:
        await retryer(call_provider)

    assert info.value is error
    assert attempts == 1
    assert not events
