"""Provider retry helpers.

Why:
    Keeps same-provider retry classification, backoff, and retry logging
    separate from route fallback.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from llm_router._api.errors import ProviderError
from llm_router._internal.config.models import RetryPolicy
from py_lib_runtime import build_retry_before_sleep_logger


class RetryLogger(Protocol):
    """Minimal logger protocol consumed by retry callbacks."""

    def warning(self, event: str, **values: object) -> None:
        """Emit one warning event."""


class RetryClassification(StrEnum):
    """Provider retry decision for one failure."""

    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """Classified retry decision."""

    classification: RetryClassification
    reason: str
    status_code: int | None = None

    @property
    def retryable(self) -> bool:
        """Return whether the failure should be retried on the same route."""
        return self.classification is RetryClassification.RETRYABLE


_RETRYABLE_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})
_NON_RETRYABLE_STATUS_CODES = frozenset({400, 401, 403, 404, 422})
_SERVER_ERROR_STATUS_MIN = 500


def classify_status_code(status_code: int) -> RetryDecision:
    """Classify an HTTP status code for same-provider retry."""
    if status_code in _RETRYABLE_STATUS_CODES:
        return RetryDecision(
            classification=RetryClassification.RETRYABLE,
            reason="retryable_status",
            status_code=status_code,
        )
    if status_code in _NON_RETRYABLE_STATUS_CODES:
        return RetryDecision(
            classification=RetryClassification.NON_RETRYABLE,
            reason="caller_or_auth_status",
            status_code=status_code,
        )
    if status_code >= _SERVER_ERROR_STATUS_MIN:
        return RetryDecision(
            classification=RetryClassification.RETRYABLE,
            reason="server_status",
            status_code=status_code,
        )
    return RetryDecision(
        classification=RetryClassification.NON_RETRYABLE,
        reason="status_not_retryable",
        status_code=status_code,
    )


def classify_exception(exc: BaseException) -> RetryDecision:
    """Classify transport-style exceptions without importing provider SDKs."""
    tokens = _exception_name_tokens(exc)
    retryable_fragments = (
        "timeout",
        "connect",
        "network",
        "disconnect",
        "remote",
        "protocol",
        "read",
        "write",
    )
    if any(
        token.startswith(fragment)
        for token in tokens
        for fragment in retryable_fragments
    ):
        return RetryDecision(
            classification=RetryClassification.RETRYABLE,
            reason="transport_exception",
        )
    return RetryDecision(
        classification=RetryClassification.NON_RETRYABLE,
        reason="exception_not_retryable",
    )


def _exception_name_tokens(exc: BaseException) -> tuple[str, ...]:
    """Return lower-case CamelCase-aware exception name tokens."""
    name = type(exc).__name__
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    return tuple(token for token in re.split(r"[^a-z0-9]+", spaced.lower()) if token)


def is_retryable_provider_error(exc: BaseException) -> bool:
    """Return whether a public provider error carries a retryable private cause."""
    if not isinstance(exc, ProviderError):
        return False
    return bool(getattr(exc.cause, "retryable", False))


def build_provider_retrying(
    *,
    policy: RetryPolicy,
    logger: RetryLogger,
    context_getter: Callable[[], dict[str, Any]] | None = None,
    state_sink: Callable[[dict[str, Any]], None] | None = None,
) -> Retrying:
    """Build a sync Tenacity policy for same-provider attempts."""
    return Retrying(
        stop=stop_after_attempt(policy.max_attempts),
        wait=wait_random_exponential(
            min=policy.min_wait_seconds,
            max=policy.max_wait_seconds,
        ),
        retry=retry_if_exception(is_retryable_provider_error),
        before_sleep=build_retry_before_sleep_logger(
            logger,
            event_type="llm_router.provider.retry.scheduled",
            context_getter=context_getter,
            state_sink=state_sink,
        ),
        reraise=True,
    )


def build_provider_async_retrying(
    *,
    policy: RetryPolicy,
    logger: RetryLogger,
    context_getter: Callable[[], dict[str, Any]] | None = None,
    state_sink: Callable[[dict[str, Any]], None] | None = None,
) -> AsyncRetrying:
    """Build an async Tenacity policy for same-provider attempts."""
    return AsyncRetrying(
        stop=stop_after_attempt(policy.max_attempts),
        wait=wait_random_exponential(
            min=policy.min_wait_seconds,
            max=policy.max_wait_seconds,
        ),
        retry=retry_if_exception(is_retryable_provider_error),
        before_sleep=build_retry_before_sleep_logger(
            logger,
            event_type="llm_router.provider.retry.scheduled",
            context_getter=context_getter,
            state_sink=state_sink,
        ),
        reraise=True,
    )
