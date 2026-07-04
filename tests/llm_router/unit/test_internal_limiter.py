from __future__ import annotations

from math import isclose

from llm_router import Provider, ProviderLimits
from llm_router._internal.runtime.limiter import LimiterState


def test_success_records_conservative_rps_and_rpm_interval() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=2.0,
        rpm=60.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=0,
    )

    limiter.record_success(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=10.0,
    )

    assert isclose(
        limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=10.25),
        0.75,
    )


def test_limiter_buckets_are_separate_per_provider_and_key() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=1.0,
        rpm=1_000.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=0,
    )

    limiter.record_success(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=20.0,
    )

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=2, now=20.1) == 0.0
    assert limiter.wait_seconds(provider=Provider.GROQ, key_id=1, now=20.1) == 0.0
    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=20.1) > 0.0


def test_failure_cooldown_opens_after_configured_failure_count() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=2,
    )

    limiter.record_failure(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=30.0,
    )
    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=30.0) == 0.0

    limiter.record_failure(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=31.0,
    )

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=31.0) == 5.0


def test_success_clears_failure_count_but_keeps_rate_interval() -> None:
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=10.0,
        rpm=1_000.0,
        cooldown_seconds=5.0,
        cooldown_after_failures=2,
    )

    limiter.record_failure(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=40.0,
    )
    limiter.record_success(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=41.0,
    )
    limiter.record_failure(
        provider=Provider.NVIDIA,
        key_id=1,
        limits=limits,
        now=41.1,
    )

    assert limiter.wait_seconds(provider=Provider.NVIDIA, key_id=1, now=41.1) == 0.0
