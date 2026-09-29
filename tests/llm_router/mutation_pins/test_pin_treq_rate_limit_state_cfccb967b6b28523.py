# mutation-pin: TREQ_RATE_LIMIT_STATE cfccb967b6b28523
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_record_success_without_now_uses_monotonic_clock() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=2.0,
        rpm=0.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=2,
    )

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits, now=1.0)
    limiter.record_success(provider=Provider.NVIDIA, key_id=1, limits=limits)

    wait = limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1)
    assert 0.0 < wait <= 0.5

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits)
    wait_after = limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1)
    assert wait_after <= 0.5
