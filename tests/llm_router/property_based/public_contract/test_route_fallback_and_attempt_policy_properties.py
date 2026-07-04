"""Property-based tests for route fallback and attempt policy invariants.

Why:
    Protects stable public routing-policy helpers through many generated policy
    combinations and rate-limit shapes.

How:
    Exercises the supported public policy/value objects without relying on routing
    execution or provider calls.
"""

from __future__ import annotations

from math import isclose

from hypothesis import given, strategies as st

from llm_router import Provider, ProviderLimits, RouterPolicy

# =============================================================================
# Strategies
# =============================================================================


_OPTIONAL_BOOL = st.one_of(st.none(), st.booleans())
_LIMITS = st.builds(
    ProviderLimits,
    rps=st.floats(
        min_value=0.0,
        max_value=20.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    rpm=st.floats(
        min_value=0.0,
        max_value=600.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    cooldown_seconds=st.floats(
        min_value=0.0,
        max_value=120.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    cooldown_after_failures=st.integers(min_value=0, max_value=10),
)
_OPTIONAL_LIMITS = st.one_of(st.none(), _LIMITS)
_LIMITS_BY_PROVIDER = st.one_of(
    st.none(),
    st.dictionaries(
        keys=st.sampled_from(list(Provider)),
        values=_LIMITS,
        max_size=min(3, len(list(Provider))),
    ),
)


# =============================================================================
# Assertions
# =============================================================================


def assert_router_policy_kwargs(
    result: dict[str, object],
    *,
    max_attempts: int | None,
    attempt_timeout_seconds: float | None,
    wait_for_cooldown_if_all_blocked: bool | None,
    round_robin_start: bool | None,
    shuffle_fallbacks: bool | None,
    default_limits: ProviderLimits | None,
    limits_by_provider: dict[Provider, ProviderLimits] | None,
) -> None:
    """Assert the public omission and preservation contract for policy bundles."""
    assert ("max_attempts" in result) is (max_attempts is not None)
    assert ("attempt_timeout_seconds" in result) is (
        attempt_timeout_seconds is not None
    )
    assert ("wait_for_cooldown_if_all_blocked" in result) is (
        wait_for_cooldown_if_all_blocked is not None
    )
    assert ("round_robin_start" in result) is (round_robin_start is not None)
    assert ("shuffle_fallbacks" in result) is (shuffle_fallbacks is not None)
    assert ("default_limits" in result) is (default_limits is not None)
    assert ("limits_by_provider" in result) is (limits_by_provider is not None)

    if max_attempts is not None:
        assert result["max_attempts"] == max_attempts
    if attempt_timeout_seconds is not None:
        assert result["attempt_timeout_seconds"] == attempt_timeout_seconds
    if wait_for_cooldown_if_all_blocked is not None:
        assert (
            result["wait_for_cooldown_if_all_blocked"]
            == wait_for_cooldown_if_all_blocked
        )
    if round_robin_start is not None:
        assert result["round_robin_start"] == round_robin_start
    if shuffle_fallbacks is not None:
        assert result["shuffle_fallbacks"] == shuffle_fallbacks
    if default_limits is not None:
        assert result["default_limits"] == default_limits
    if limits_by_provider is not None:
        assert result["limits_by_provider"] == limits_by_provider
        assert result["limits_by_provider"] is not limits_by_provider


# =============================================================================
# Properties
# =============================================================================


@given(limits=_LIMITS)
def test_provider_limits_min_interval_matches_public_formula(
    limits: ProviderLimits,
) -> None:
    """`min_interval_seconds()` should match the public rate formula."""
    # The public contract here is mathematical: the conservative interval is
    # whichever rate limit forces the slower request cadence.
    expected_candidates: list[float] = []
    if limits.rps > 0:
        expected_candidates.append(1.0 / limits.rps)
    if limits.rpm > 0:
        expected_candidates.append(60.0 / limits.rpm)
    expected = max(expected_candidates) if expected_candidates else 0.0

    assert isclose(limits.min_interval_seconds(), expected)
    assert limits.min_interval_seconds() >= 0.0


@given(
    max_attempts=st.one_of(st.none(), st.integers(min_value=1, max_value=5)),
    attempt_timeout_seconds=st.one_of(
        st.none(),
        st.floats(
            min_value=0.1,
            max_value=30.0,
            allow_nan=False,
            allow_infinity=False,
        ),
    ),
    wait_for_cooldown_if_all_blocked=_OPTIONAL_BOOL,
    round_robin_start=_OPTIONAL_BOOL,
    shuffle_fallbacks=_OPTIONAL_BOOL,
    default_limits=_OPTIONAL_LIMITS,
    limits_by_provider=_LIMITS_BY_PROVIDER,
)
def test_router_policy_as_kwargs_keeps_only_explicit_values(
    *,
    max_attempts: int | None,
    attempt_timeout_seconds: float | None,
    wait_for_cooldown_if_all_blocked: bool | None,
    round_robin_start: bool | None,
    shuffle_fallbacks: bool | None,
    default_limits: ProviderLimits | None,
    limits_by_provider: dict[Provider, ProviderLimits] | None,
) -> None:
    """`RouterPolicy.as_kwargs()` should preserve explicit policy values only."""
    # Policy bundles follow the same omission rule as generation bundles.
    # Property-based coverage is useful here because mixed optional fields are
    # where accidental leakage of `None` values is most likely.
    policy = RouterPolicy(
        max_attempts=max_attempts,
        attempt_timeout_seconds=attempt_timeout_seconds,
        wait_for_cooldown_if_all_blocked=wait_for_cooldown_if_all_blocked,
        round_robin_start=round_robin_start,
        shuffle_fallbacks=shuffle_fallbacks,
        default_limits=default_limits,
        limits_by_provider=limits_by_provider,
    )

    result = policy.as_kwargs()

    assert_router_policy_kwargs(
        result,
        max_attempts=max_attempts,
        attempt_timeout_seconds=attempt_timeout_seconds,
        wait_for_cooldown_if_all_blocked=wait_for_cooldown_if_all_blocked,
        round_robin_start=round_robin_start,
        shuffle_fallbacks=shuffle_fallbacks,
        default_limits=default_limits,
        limits_by_provider=limits_by_provider,
    )
