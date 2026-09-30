# mutation-pin: TREQ_RATE_LIMIT_COOLDOWN_POLICY 9f72abc51a357f38
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_COOLDOWN_POLICY[revision==1]")
def test_zero_threshold_never_opens_cooldown() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=1.0,
        rpm=1.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=0,
    )

    limiter.record_failure(provider=Provider.GOOGLE, key_id=1, limits=limits, now=10.0)

    bucket = limiter._buckets[("google", 1)]
    assert bucket.cooldown_until == 0.0
    assert bucket.failure_count == 1
