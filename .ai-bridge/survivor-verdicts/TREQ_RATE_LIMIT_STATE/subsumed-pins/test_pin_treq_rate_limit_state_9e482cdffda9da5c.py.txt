# mutation-pin: TREQ_RATE_LIMIT_STATE 9e482cdffda9da5c
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_wait_seconds_without_now_uses_real_clock() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=1000000.0,
        cooldown_after_failures=1,
    )

    fresh = limiter.wait_seconds(provider=Provider.GROQ, key_id=3)
    assert fresh == 0.0

    limiter.record_failure(provider=Provider.GROQ, key_id=3, limits=limits)

    blocked = limiter.wait_seconds(provider=Provider.GROQ, key_id=3)
    assert 0.0 < blocked <= 1000000.0
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=4) == 0.0
