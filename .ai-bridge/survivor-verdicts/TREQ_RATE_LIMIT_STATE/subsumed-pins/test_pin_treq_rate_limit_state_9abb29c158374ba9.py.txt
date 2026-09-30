# mutation-pin: TREQ_RATE_LIMIT_STATE 9abb29c158374ba9
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


def _limits(
    *,
    cooldown_seconds: float = 0.0,
    cooldown_after_failures: int = 0,
) -> ProviderLimits:
    return ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=cooldown_seconds,
        cooldown_after_failures=cooldown_after_failures,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_enum_and_string_provider_share_one_isolated_bucket() -> None:
    limiter = LimiterState()
    limits = _limits(cooldown_seconds=5.0, cooldown_after_failures=2)

    limiter.record_failure(provider="gemini_webapi", key_id=3, limits=limits, now=10.0)
    limiter.record_failure(
        provider=Provider.GEMINI_WEBAPI, key_id=3, limits=limits, now=10.0
    )

    assert limiter.wait_seconds(provider="gemini_webapi", key_id=3, now=10.0) == 5.0
    assert (
        limiter.wait_seconds(provider=Provider.GEMINI_WEBAPI, key_id=3, now=10.0) == 5.0
    )
    assert (
        limiter.wait_seconds(provider=Provider.GEMINI_WEBAPI, key_id=4, now=10.0) == 0.0
    )
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=3, now=10.0) == 0.0
