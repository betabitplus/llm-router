# mutation-pin: TREQ_RATE_LIMIT_COOLDOWN_POLICY 9f107933887a3fa0
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_COOLDOWN_POLICY[revision==1]")
def test_single_failure_threshold_of_one_opens_cooldown() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=1.0,
        rpm=1.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=1,
    )

    limiter.record_failure(provider=Provider.GOOGLE, key_id=1, limits=limits, now=0.0)

    assert limiter.wait_seconds(provider=Provider.GOOGLE, key_id=1, now=0.0) == 5.0
    assert limiter.wait_seconds(provider=Provider.GOOGLE, key_id=1, now=2.0) == 3.0
    assert limiter.wait_seconds(provider=Provider.GOOGLE, key_id=1, now=5.0) == 0.0
