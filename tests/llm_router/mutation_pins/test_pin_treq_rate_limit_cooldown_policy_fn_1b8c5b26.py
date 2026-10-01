# mutation-pin: TREQ_RATE_LIMIT_COOLDOWN_POLICY FN-1B8C5B26
# pinned-by: delegate, one pin for 4 pins of LimiterState.record_failure
# kills: 7cfc3f8477b3a2b8 96a28c868f99fb34 99d124741e83ae13 9f107933887a3fa0
from __future__ import annotations

import pytest

from llm_router._api.types import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")

REQ = "TREQ_RATE_LIMIT_COOLDOWN_POLICY[revision==1]"


def make_limits(after: int) -> ProviderLimits:
    return ProviderLimits(
        rps=0.0, rpm=0.0, cooldown_seconds=5.0, cooldown_after_failures=after
    )


@pytest.mark.verifies(REQ)
def test_threshold_blocks_then_counter_resets() -> None:
    limiter = LimiterState()
    limits = make_limits(2)
    prov = Provider.GROQ

    limiter.record_failure(provider=prov, key_id=3, limits=limits, now=10.0)
    assert limiter.wait_seconds(provider=prov, key_id=3, now=10.0) == 0.0
    limiter.record_failure(provider=prov, key_id=3, limits=limits, now=11.0)
    assert limiter.wait_seconds(provider=prov, key_id=3, now=11.0) == 5.0
    assert limiter.wait_seconds(provider=prov, key_id=3, now=14.0) == 2.0

    limiter.record_failure(provider=prov, key_id=3, limits=limits, now=20.0)
    assert limiter.wait_seconds(provider=prov, key_id=3, now=20.0) == 0.0


@pytest.mark.verifies(REQ)
def test_threshold_one_blocks_immediately() -> None:
    limiter = LimiterState()
    limits = make_limits(1)
    prov = Provider.GOOGLE

    limiter.record_failure(provider=prov, key_id=1, limits=limits, now=0.0)

    assert limiter.wait_seconds(provider=prov, key_id=1, now=0.0) == 5.0
    assert limiter.wait_seconds(provider=prov, key_id=1, now=5.0) == 0.0


@pytest.mark.verifies(REQ)
def test_zero_threshold_never_blocks() -> None:
    limiter = LimiterState()
    limits = make_limits(0)

    limiter.record_failure(provider=Provider.AISTUDIO, key_id=0, limits=limits, now=2.0)

    wait = limiter.wait_seconds(provider=Provider.AISTUDIO, key_id=0, now=2.0)
    assert wait == 0.0


@pytest.mark.verifies(REQ)
def test_threshold_without_now_uses_clock() -> None:
    limiter = LimiterState()
    limits = make_limits(2)
    prov = Provider.NVIDIA

    limiter.record_failure(provider=prov, key_id=1, limits=limits)
    assert limiter.wait_seconds(provider=prov, key_id=1) == 0.0
    limiter.record_failure(provider=prov, key_id=1, limits=limits)

    wait = limiter.wait_seconds(provider=prov, key_id=1)
    assert 3.0 < wait <= 5.0
