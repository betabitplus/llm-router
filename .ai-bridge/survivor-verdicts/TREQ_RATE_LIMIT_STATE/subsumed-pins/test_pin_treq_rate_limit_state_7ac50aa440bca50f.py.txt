# mutation-pin: TREQ_RATE_LIMIT_STATE 7ac50aa440bca50f
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_plain_string_provider_bucket_is_isolated_per_provider() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=1,
    )

    limiter.record_failure(
        provider="custom-provider", key_id=3, limits=limits, now=10.0
    )

    assert limiter.wait_seconds(provider="custom-provider", key_id=3, now=10.0) == 5.0
    assert limiter.wait_seconds(provider="other-provider", key_id=3, now=10.0) == 0.0
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=3, now=10.0) == 0.0
    assert limiter.wait_seconds(provider="custom-provider", key_id=4, now=10.0) == 0.0
