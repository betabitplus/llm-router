# mutation-pin: TREQ_RATE_LIMIT_STATE 6a97bd579b2777e7
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


class CaseInsensitiveName(str):
    """Provider name as a caller may carry it: compared without regard to case."""

    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, str) and self.casefold() == other.casefold()

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.casefold())


def _limits() -> ProviderLimits:
    return ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=3,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==2]")
def test_enum_provider_bucket_is_shared_with_its_string_name() -> None:
    limits = _limits()
    member = Provider.GEMINI_WEBAPI
    name = CaseInsensitiveName("Gemini_WebAPI")
    limiter = LimiterState()

    limiter.record_failure(provider=member, key_id=2, limits=limits, now=10.0)
    limiter.record_failure(provider=member, key_id=2, limits=limits, now=10.0)
    limiter.record_success(provider=name, key_id=2, limits=limits, now=11.0)
    limiter.record_failure(provider=member, key_id=2, limits=limits, now=12.0)

    # The success recorded under the string name cleared the enum's count.
    assert limiter.wait_seconds(provider=member, key_id=2, now=12.0) == 0.0
    assert limiter.wait_seconds(provider=name, key_id=2, now=12.0) == 0.0

    limiter.record_failure(provider=member, key_id=2, limits=limits, now=13.0)
    limiter.record_failure(provider=member, key_id=2, limits=limits, now=14.0)

    # Threshold reached via the enum: the same key is blocked under its name.
    assert limiter.wait_seconds(provider=name, key_id=2, now=14.0) == 5.0
    assert limiter.wait_seconds(provider=member, key_id=2, now=14.0) == 5.0
    assert limiter.wait_seconds(provider=name, key_id=3, now=14.0) == 0.0
    assert limiter.wait_seconds(provider=Provider.QWENCHAT, key_id=2, now=14.0) == 0.0
