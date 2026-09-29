# mutation-pin: TREQ_RATE_LIMIT_COOLDOWN_POLICY 99d124741e83ae13
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_COOLDOWN_POLICY[revision==1]")
def test_threshold_failure_without_now_blocks_for_cooldown() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=30.0,
        cooldown_after_failures=2,
    )

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits)
    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1) == 0.0

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits)
    wait = limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1)

    assert 25.0 < wait <= 30.0
