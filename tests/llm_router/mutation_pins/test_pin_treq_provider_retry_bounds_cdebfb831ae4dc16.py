# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS cdebfb831ae4dc16
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

import llm_router._internal.providers.retry as retry_mod
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_retrying

pytestmark = pytest.mark.verification_kind("unit")


class _TestLogger:
    def __call__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def log(self, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, *args: Any, **kwargs: Any) -> None:
        pass

    def info(self, *args: Any, **kwargs: Any) -> None:
        pass

    def debug(self, *args: Any, **kwargs: Any) -> None:
        pass


class DummyProviderError(Exception):
    """Simulates a provider error for testing."""


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==1]")
def test_provider_retrying_reraises_same_exception_when_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _is_retryable(error: BaseException) -> bool:
        return isinstance(error, Exception)

    monkeypatch.setattr(retry_mod, "is_retryable_provider_error", _is_retryable)

    max_attempts = 3
    policy = RetryPolicy(
        min_wait_seconds=0.0,
        max_wait_seconds=0.0,
        max_attempts=max_attempts,
    )
    retrying = build_provider_retrying(
        policy=policy,
        logger=_TestLogger(),
    )

    error = DummyProviderError("simulated provider failure")
    attempts = 0

    def failing_provider_call() -> None:
        nonlocal attempts
        attempts += 1
        raise error

    with pytest.raises(DummyProviderError) as exc_info:
        retrying(failing_provider_call)

    assert exc_info.value is error
    assert attempts == max_attempts
