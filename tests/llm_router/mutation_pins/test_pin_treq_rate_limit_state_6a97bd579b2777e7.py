# mutation-pin: TREQ_RATE_LIMIT_STATE 6a97bd579b2777e7
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_enum_provider_is_normalised_to_plain_string_bucket_key() -> None:
    limits = ProviderLimits(
        rps=0.0, rpm=0.0, cooldown_seconds=5.0, cooldown_after_failures=2
    )
    limiter = LimiterState()

    limiter.record_failure(
        provider=Provider.GEMINI_WEBAPI, key_id=3, limits=limits, now=10.0
    )
    limiter.record_failure(provider="gemini_webapi", key_id=3, limits=limits, now=10.0)

    assert limiter.wait_seconds(provider="gemini_webapi", key_id=3, now=10.0) == 5.0
    assert (
        limiter.wait_seconds(provider=Provider.GEMINI_WEBAPI, key_id=3, now=10.0) == 5.0
    )

    keys = list(limiter._buckets)
    assert len(keys) == 1
    stored_provider, stored_id = next(iter(keys))
    assert type(stored_provider) is str
    assert stored_provider == "gemini_webapi"
    assert stored_id == 3
