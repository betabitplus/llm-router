# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS 909ea17c8e00b989
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router._api.errors import ProviderError
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_retrying

pytestmark = pytest.mark.verification_kind("unit")


class RecordingLogger:
    """Capture retry logger calls for assertion without external logging."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.events.append((args, kwargs))

    def log(self, level: Any, *args: Any, **kwargs: Any) -> None:
        self.events.append((level, args, kwargs))

    def warning(self, *args: Any, **kwargs: Any) -> None:
        self.events.append((args, kwargs))

    def info(self, *args: Any, **kwargs: Any) -> None:
        self.events.append((args, kwargs))

    def error(self, *args: Any, **kwargs: Any) -> None:
        self.events.append((args, kwargs))


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==3]")
def test_build_provider_retrying_does_not_retry_permanent_error() -> None:
    policy = RetryPolicy(
        min_wait_seconds=0.001,
        max_wait_seconds=0.002,
        max_attempts=3,
    )
    logger = RecordingLogger()
    state_events: list[dict[str, Any]] = []
    retrying = build_provider_retrying(
        policy=policy,
        logger=logger,
        state_sink=state_events.append,
    )

    call_count = 0
    cause = RuntimeError("internal failure")

    def fail_permanently() -> None:
        nonlocal call_count
        call_count += 1
        raise ProviderError(
            cause,
            "test_provider",
            "test_model",
            message="permanent provider error",
        )

    with pytest.raises(ProviderError, match=r"permanent provider error"):
        retrying(fail_permanently)

    assert call_count == 1
    assert len(logger.events) == 0
    assert len(state_events) == 0
