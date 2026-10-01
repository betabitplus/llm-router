# mutation-pin: TREQ_PROVIDER_RETRY_BOUNDS 621cfe26a9c437b8
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
from __future__ import annotations

import pytest

from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.retry import build_provider_async_retrying

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_BOUNDS[revision==3]")
def test_async_retrying_applies_maximum_wait_bound() -> None:
    policy = RetryPolicy(
        min_wait_seconds=1.0,
        max_wait_seconds=10.0,
        max_attempts=3,
    )
    retrying = build_provider_async_retrying(
        policy=policy,
        logger=None,
    )
    assert retrying.wait.max == 10.0
    assert retrying.wait.min == 1.0
