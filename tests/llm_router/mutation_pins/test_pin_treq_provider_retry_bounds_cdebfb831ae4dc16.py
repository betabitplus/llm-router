# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS cdebfb831ae4dc16
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router._api.errors import ProviderError
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_retrying

pytestmark = pytest.mark.verification_kind("unit")


class RecordingLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def warning(self, event: str, **values: object) -> None:
        self.events.append((event, values))


class TransientCauseError(Exception):
    retryable = True


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==3]")
def test_provider_retrying_reraises_exhausted_provider_error() -> None:
    policy = RetryPolicy(
        min_wait_seconds=0.0,
        max_wait_seconds=0.0,
        max_attempts=2,
    )
    retrying = build_provider_retrying(
        policy=policy,
        logger=RecordingLogger(),
        context_getter=None,
        state_sink=None,
    )

    attempt_count = 0
    cause = TransientCauseError()
    failure = ProviderError(
        cause=cause,
        provider="dummy_provider",
        model="dummy_model",
        message="temporary provider failure",
    )

    def failing_provider_call() -> str:
        nonlocal attempt_count
        attempt_count += 1
        raise failure

    with pytest.raises(
        ProviderError,
        match=r"temporary provider failure",
    ) as exc_info:
        retrying(failing_provider_call)

    assert exc_info.value is failure
    assert attempt_count == 2
