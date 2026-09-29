# mutation-pin: TREQ_RATE_LIMIT_COOLDOWN_POLICY 7cfc3f8477b3a2b8
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
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=30.0,
        cooldown_after_failures=0,
    )

    limiter.record_failure(provider=Provider.AISTUDIO, key_id=0, limits=limits, now=2.0)

    wait = limiter.wait_seconds(provider=Provider.AISTUDIO, key_id=0, now=2.0)
    assert wait == 0.0
