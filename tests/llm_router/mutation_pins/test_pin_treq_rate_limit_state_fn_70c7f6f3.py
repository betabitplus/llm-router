# mutation-pin: TREQ_RATE_LIMIT_STATE FN-70C7F6F3
# pinned-by: delegate, one pin for 3 pins of LimiterState.record_failure
# kills: 7cfc3f8477b3a2b8 96a28c868f99fb34 99d124741e83ae13
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


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_failure_count_resets_after_cooldown_opens() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=10.0,
        cooldown_after_failures=3,
    )
    for _ in range(3):
        limiter.record_failure(
            provider=Provider.GOOGLE, key_id=1, limits=limits, now=0.0
        )
    assert limiter.wait_seconds(provider=Provider.GOOGLE, key_id=1, now=0.0) == 10.0

    for _ in range(2):
        limiter.record_failure(
            provider=Provider.GOOGLE, key_id=1, limits=limits, now=20.0
        )
        assert limiter.wait_seconds(provider=Provider.GOOGLE, key_id=1, now=20.0) == 0.0
    limiter.record_failure(provider=Provider.GOOGLE, key_id=1, limits=limits, now=20.0)
    assert limiter.wait_seconds(provider=Provider.GOOGLE, key_id=1, now=20.0) == 10.0


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
