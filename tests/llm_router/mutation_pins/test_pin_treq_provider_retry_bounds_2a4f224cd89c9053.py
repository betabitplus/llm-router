# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS 2a4f224cd89c9053
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
from __future__ import annotations

import typing

import pytest

from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_retrying

pytestmark = pytest.mark.verification_kind("unit")


class DummyLogger:
    """Minimal logger stub for provider retry policy construction."""

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        del args, kwargs

    def info(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        del args, kwargs

    def warning(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        del args, kwargs

    def debug(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        del args, kwargs

    def error(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        del args, kwargs

    def log(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        del args, kwargs


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==3]")
def test_provider_retrying_wait_bounds() -> None:
    policy = RetryPolicy(
        min_wait_seconds=1.0,
        max_wait_seconds=5.0,
        max_attempts=3,
    )
    logger = DummyLogger()
    retrying = build_provider_retrying(
        policy=policy,
        logger=logger,
    )
    assert retrying.wait.min == policy.min_wait_seconds
    assert retrying.wait.max == policy.max_wait_seconds
