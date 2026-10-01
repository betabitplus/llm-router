# mutation-pin: TREQ_RATE_LIMIT_STATE FN-7F8E200A
# pinned-by: delegate, one pin for 2 pins of LimiterState._bucket
# kills: 6a97bd579b2777e7 7ac50aa440bca50f
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


class CaseInsensitiveName(str):
    """Provider name compared without regard to case."""

    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, str) and self.casefold() == other.casefold()

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.casefold())


def _limits(failures: int) -> ProviderLimits:
    return ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=failures,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_enum_provider_bucket_is_shared_with_its_string_name() -> None:
    limits = _limits(3)
    member = Provider.GEMINI_WEBAPI
    name = CaseInsensitiveName("Gemini_WebAPI")
    limiter = LimiterState()

    limiter.record_failure(provider=member, key_id=2, limits=limits, now=10.0)
    limiter.record_failure(provider=member, key_id=2, limits=limits, now=10.0)
    limiter.record_success(provider=name, key_id=2, limits=limits, now=11.0)
    limiter.record_failure(provider=member, key_id=2, limits=limits, now=12.0)

    assert limiter.wait_seconds(provider=member, key_id=2, now=12.0) == 0.0
    assert limiter.wait_seconds(provider=name, key_id=2, now=12.0) == 0.0

    limiter.record_failure(provider=member, key_id=2, limits=limits, now=13.0)
    limiter.record_failure(provider=member, key_id=2, limits=limits, now=14.0)

    assert limiter.wait_seconds(provider=name, key_id=2, now=14.0) == 5.0
    assert limiter.wait_seconds(provider=member, key_id=2, now=14.0) == 5.0
    assert limiter.wait_seconds(provider=name, key_id=3, now=14.0) == 0.0
    assert limiter.wait_seconds(provider=Provider.QWENCHAT, key_id=2, now=14.0) == 0.0


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_plain_string_provider_bucket_is_isolated_per_provider() -> None:
    limiter = LimiterState()
    limits = _limits(1)

    limiter.record_failure(
        provider="custom-provider", key_id=3, limits=limits, now=10.0
    )

    assert limiter.wait_seconds(provider="custom-provider", key_id=3, now=10.0) == 5.0
    assert limiter.wait_seconds(provider="other-provider", key_id=3, now=10.0) == 0.0
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=3, now=10.0) == 0.0
    assert limiter.wait_seconds(provider="custom-provider", key_id=4, now=10.0) == 0.0
