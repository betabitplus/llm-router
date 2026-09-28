# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS a3f68e4f70d254ab
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router._api.errors import ProviderError
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_async_retrying

pytestmark = pytest.mark.verification_kind("unit")


class _RetryableCauseError(Exception):
    """Private provider failure cause reporting itself as retryable."""

    retryable = True


class _RecordingRetryLogger:
    """Minimal retry logger that records before-sleep warnings."""

    def __init__(self) -> None:
        self.warnings = 0

    def warning(self, event: str, **values: object) -> None:
        del event, values
        self.warnings += 1


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==1]")
@pytest.mark.asyncio
async def test_async_retry_exhaustion_reraises_original_after_max_attempts() -> None:
    max_attempts = 3
    policy = RetryPolicy(
        min_wait_seconds=0.0,
        max_wait_seconds=0.0,
        max_attempts=max_attempts,
    )
    retrying = build_provider_async_retrying(
        policy=policy,
        logger=_RecordingRetryLogger(),
    )
    original = ProviderError(
        _RetryableCauseError("rate limited"),
        provider="openai",
        model="gpt-4o-mini",
    )
    attempts = 0

    async def call_provider() -> None:
        nonlocal attempts
        attempts += 1
        raise original

    with pytest.raises(ProviderError, match=r"Provider 'openai' failed") as info:
        await retrying(call_provider)

    assert info.value is original
    assert attempts == max_attempts
