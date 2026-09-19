from __future__ import annotations

from math import isclose

import pytest

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState

pytestmark = pytest.mark.verification_kind("unit")


def _limits(
    *,
    rps: float = 0.0,
    rpm: float = 0.0,
    cooldown_seconds: float = 0.0,
    cooldown_after_failures: int = 0,
) -> ProviderLimits:
    return ProviderLimits(
        rps=rps,
        rpm=rpm,
        cooldown_seconds=cooldown_seconds,
        cooldown_after_failures=cooldown_after_failures,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==1]")
@pytest.mark.coverage_item("VC_RATE_LIMIT_CONSERVATIVE_INTERVAL")
@pytest.mark.coverage_path("rpm-dominant")
def test_success_uses_rpm_interval_when_it_is_more_conservative() -> None:
    limiter = LimiterState()

    limiter.record_success(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=_limits(rps=2.0, rpm=60.0),
        now=10.0,
    )

    assert isclose(
        limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=10.25),
        0.75,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==1]")
@pytest.mark.coverage_item("VC_RATE_LIMIT_CONSERVATIVE_INTERVAL")
@pytest.mark.coverage_path("rps-dominant")
def test_success_uses_rps_interval_when_it_is_more_conservative() -> None:
    limiter = LimiterState()

    limiter.record_success(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=_limits(rps=1.0, rpm=120.0),
        now=10.0,
    )

    assert isclose(
        limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=10.25),
        0.75,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==1]")
@pytest.mark.coverage_item("VC_RATE_LIMIT_PROVIDER_KEY_ISOLATION")
@pytest.mark.coverage_path("same-provider-other-key")
def test_limiter_state_is_isolated_between_keys_of_one_provider() -> None:
    limiter = LimiterState()
    limits = _limits(rps=1.0, rpm=1_000.0)

    limiter.record_success(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=20.0,
    )

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=20.1) > 0.0
    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=2, now=20.1) == 0.0


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==1]")
@pytest.mark.coverage_item("VC_RATE_LIMIT_PROVIDER_KEY_ISOLATION")
@pytest.mark.coverage_path("same-key-other-provider")
def test_limiter_state_is_isolated_between_providers_for_same_key_id() -> None:
    limiter = LimiterState()
    limits = _limits(rps=1.0, rpm=1_000.0)

    limiter.record_success(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=20.0,
    )

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=20.1) > 0.0
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=1, now=20.1) == 0.0


@pytest.mark.verifies("TREQ_RATE_LIMIT_STATE[revision==1]")
@pytest.mark.coverage_item("VC_RATE_LIMIT_SUCCESS_RESET")
def test_success_resets_failure_count_before_cooldown_threshold() -> None:
    limiter = LimiterState()
    limits = _limits(cooldown_seconds=5.0, cooldown_after_failures=2)

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits, now=30.0)
    limiter.record_success(provider=Provider.NVIDIA, key_id=1, limits=limits, now=31.0)
    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits, now=32.0)

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=32.0) == 0.0

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits, now=33.0)
    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=33.0) == 5.0


@pytest.mark.verifies("TREQ_RATE_LIMIT_COOLDOWN_POLICY[revision==1]")
@pytest.mark.coverage_item("VC_RATE_LIMIT_COOLDOWN_THRESHOLD")
@pytest.mark.coverage_path("below-threshold")
def test_failure_below_cooldown_threshold_does_not_block_bucket() -> None:
    limiter = LimiterState()
    limits = _limits(cooldown_seconds=7.0, cooldown_after_failures=2)

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits, now=40.0)

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=40.0) == 0.0


@pytest.mark.verifies("TREQ_RATE_LIMIT_COOLDOWN_POLICY[revision==1]")
@pytest.mark.coverage_item("VC_RATE_LIMIT_COOLDOWN_THRESHOLD")
@pytest.mark.coverage_path("at-threshold")
def test_failure_at_cooldown_threshold_blocks_for_configured_duration() -> None:
    limiter = LimiterState()
    limits = _limits(cooldown_seconds=7.0, cooldown_after_failures=2)

    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits, now=40.0)
    limiter.record_failure(provider=Provider.NVIDIA, key_id=1, limits=limits, now=41.0)

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=41.0) == 7.0
