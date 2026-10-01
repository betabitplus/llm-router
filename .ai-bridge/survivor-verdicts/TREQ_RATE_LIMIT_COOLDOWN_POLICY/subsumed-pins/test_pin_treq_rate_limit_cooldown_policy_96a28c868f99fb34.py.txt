# mutation-pin: TREQ_RATE_LIMIT_COOLDOWN_POLICY 96a28c868f99fb34
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_COOLDOWN_POLICY[revision==1]")
def test_failure_count_resets_after_cooldown_opens() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0, rpm=0.0, cooldown_seconds=5.0, cooldown_after_failures=2
    )

    limiter.record_failure(provider=Provider.GROQ, key_id=3, limits=limits, now=10.0)
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=3, now=10.0) == 0.0
    limiter.record_failure(provider=Provider.GROQ, key_id=3, limits=limits, now=11.0)
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=3, now=11.0) == 5.0

    limiter.record_failure(provider=Provider.GROQ, key_id=3, limits=limits, now=20.0)

    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=3, now=20.0) == 0.0
