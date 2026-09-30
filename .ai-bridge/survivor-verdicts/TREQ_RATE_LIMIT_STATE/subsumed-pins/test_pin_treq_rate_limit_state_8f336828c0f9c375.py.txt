# mutation-pin: TREQ_RATE_LIMIT_STATE 8f336828c0f9c375
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_failures_do_not_open_cooldown_when_threshold_is_zero() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=0,
    )

    for _ in range(3):
        limiter.record_failure(
            provider=Provider.AISTUDIO, key_id=1, limits=limits, now=10.0
        )

    wait = limiter.wait_seconds(provider=Provider.AISTUDIO, key_id=1, now=10.0)
    assert wait == 0.0
