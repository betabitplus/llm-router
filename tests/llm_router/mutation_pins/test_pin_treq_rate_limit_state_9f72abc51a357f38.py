# mutation-pin: TREQ_RATE_LIMIT_STATE 9f72abc51a357f38
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_zero_threshold_never_opens_cooldown_but_counts_failures() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=1.0, rpm=1.0, cooldown_seconds=5.0, cooldown_after_failures=0
    )

    for _ in range(3):
        limiter.record_failure(
            provider=Provider.GOOGLE, key_id=1, limits=limits, now=0.0
        )

    assert limiter.wait_seconds(provider=Provider.GOOGLE, key_id=1, now=0.0) == 0.0
    assert limiter.wait_seconds(provider=Provider.GOOGLE, key_id=1, now=1.0) == 0.0
