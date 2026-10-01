# mutation-pin: TREQ_RATE_LIMIT_STATE 7cfc3f8477b3a2b8
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_zero_threshold_failure_does_not_open_cooldown() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=0,
    )

    for offset in range(3):
        limiter.record_failure(
            provider=Provider.AISTUDIO,
            key_id=0,
            limits=limits,
            now=2.0 + offset,
        )

    assert limiter.wait_seconds(provider=Provider.AISTUDIO, key_id=0, now=5.0) == 0.0
