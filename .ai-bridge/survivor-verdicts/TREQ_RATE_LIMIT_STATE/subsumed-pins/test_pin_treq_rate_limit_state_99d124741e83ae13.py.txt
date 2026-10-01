# mutation-pin: TREQ_RATE_LIMIT_STATE 99d124741e83ae13
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_failures_without_now_open_cooldown_for_own_bucket_only() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=1000.0,
        cooldown_after_failures=2,
    )

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits)
    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1) == 0.0

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits)

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1) > 0.0
    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=2) == 0.0
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=1) == 0.0
