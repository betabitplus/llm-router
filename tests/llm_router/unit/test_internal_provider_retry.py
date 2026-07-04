from __future__ import annotations

import pytest

from llm_router import Model, Provider, ProviderError
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.base import ProviderFailure
from llm_router._internal.providers.retry import (
    build_provider_retrying,
    classify_exception,
    classify_status_code,
    is_retryable_provider_error,
)


class FakeLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def warning(self, _message: str, **event: object) -> None:
        self.events.append(event)


def _provider_error(
    *,
    retryable: bool,
    status_code: int | None = None,
) -> ProviderError:
    failure = ProviderFailure(
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        message="provider unavailable",
        retryable=retryable,
        status_code=status_code,
        retry_reason="retryable_status" if retryable else "caller_or_auth_status",
    )
    return ProviderError(failure, Provider.OPENROUTER, Model.DEEPSEEK_V3)


def test_retry_classification_marks_retryable_and_permanent_statuses() -> None:
    retryable = classify_status_code(503)
    permanent = classify_status_code(400)

    assert retryable.retryable is True
    assert retryable.reason == "retryable_status"
    assert permanent.retryable is False
    assert permanent.reason == "caller_or_auth_status"


def test_transport_exception_classification_uses_safe_type_names() -> None:
    class RemoteDisconnectedError(RuntimeError):
        pass

    decision = classify_exception(RemoteDisconnectedError("gone"))

    assert decision.retryable is True
    assert decision.reason == "transport_exception"


def test_non_transport_exception_words_are_not_substring_matched() -> None:
    class CannotOverwriteExistingCassetteError(RuntimeError):
        pass

    decision = classify_exception(CannotOverwriteExistingCassetteError("nope"))

    assert decision.retryable is False
    assert decision.reason == "exception_not_retryable"


def test_provider_retrying_retries_only_retryable_provider_errors() -> None:
    logger = FakeLogger()
    snapshots: list[dict[str, object]] = []
    retrying = build_provider_retrying(
        policy=RetryPolicy(
            min_wait_seconds=0.001,
            max_wait_seconds=0.001,
            max_attempts=2,
        ),
        logger=logger,
        context_getter=lambda: {"request_id": "req-1"},
        state_sink=snapshots.append,
    )
    calls = 0

    for attempt in retrying:
        with attempt:
            calls += 1
            if calls == 1:
                raise _provider_error(retryable=True, status_code=503)
            result = "ok"

    assert result == "ok"
    assert calls == 2
    assert snapshots[0]["attempt_number"] == 1
    assert logger.events[0]["event_type"] == "llm_router.provider.retry.scheduled"
    assert logger.events[0]["request_id"] == "req-1"


def test_provider_retrying_does_not_retry_non_retryable_provider_errors() -> None:
    logger = FakeLogger()
    retrying = build_provider_retrying(
        policy=RetryPolicy(
            min_wait_seconds=0.001,
            max_wait_seconds=0.001,
            max_attempts=3,
        ),
        logger=logger,
    )
    calls = 0

    with pytest.raises(ProviderError):
        for attempt in retrying:
            with attempt:
                calls += 1
                raise _provider_error(retryable=False, status_code=400)

    assert calls == 1
    assert logger.events == []


def test_retryable_provider_error_detection_reads_private_cause() -> None:
    assert is_retryable_provider_error(_provider_error(retryable=True)) is True
    assert is_retryable_provider_error(_provider_error(retryable=False)) is False
    assert is_retryable_provider_error(RuntimeError("plain")) is False
