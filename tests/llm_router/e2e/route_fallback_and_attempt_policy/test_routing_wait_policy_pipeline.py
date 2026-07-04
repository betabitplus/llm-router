# %%
"""LLM Router e2e: wait policy when routes are blocked by rate limits.

Why:
    Verifies routing behavior when all routes are temporarily blocked by
    rate limits.

Covers:
    Area: routing layer over NVIDIA profiles
    Behavior: cooldown waiting, blocked-route failure, blocked-route
    recovery
    Interface: `LLMRouter([RouterProfile(...), ...])`, `query(...)`

Checks:
    If waiting is disabled, then the first probe still returns `A`.
    If waiting is disabled, then the blocked second call raises `TimeoutError` with the
    blocked-route message.
    If waiting is disabled, then the blocked second call fails quickly instead of
    waiting for the cooldown window.
    If waiting is enabled, then the first and second replies normalize to `A` and `B`.
    If waiting is enabled, then timing shows the second call waited for the cooldown
    interval.
    If waiting-based recovery uses the original route, then the second routing trace
    stays on provider `nvidia` with key id `1`.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.route_fallback_and_attempt_policy.test_routing_wait_policy_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/route_fallback_and_attempt_policy/test_routing_wait_policy_pipeline.py
"""

from __future__ import annotations

import os
import time

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
)
from tests.support.console import console
from tests.support.e2e_vcr_guard import require_vcr_cassette_or_record_mode

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_resilience,
    pytest.mark.cap_routing,
]


# =============================================================================
# Scenario
# =============================================================================

# NOTE: These tests use VCR cassettes. The "no-wait" probe must *not* issue a
# second HTTP request (it should fail before calling the provider). To make that
# deterministic even on slower CI machines, use a larger spacing window so the
# second call is guaranteed to be rate-limited.
_NO_WAIT_MIN_WAIT_SECONDS = 5.0

# Keep the "wait" probe reasonably fast while still exercising the cooldown.
_WAIT_MIN_WAIT_SECONDS = 1.0
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."


# =============================================================================
# Helpers
# =============================================================================


def _normalize_letter(text: str) -> str:
    """Normalize short one-token model replies for stable assertions."""
    return text.strip().rstrip(".")


def require_nvidia_key_1() -> None:
    """Skip if the deterministic single-key routing scenario cannot run."""
    if not (os.getenv("NVIDIA_API_KEY_1", "").strip()):
        pytest.skip(  # type: ignore[too-many-positional-arguments]
            "Need NVIDIA_API_KEY_1 for the wait-policy scenario."
        )


# =============================================================================
# Pipeline
# =============================================================================


def build_router(
    *, wait_for_cooldown_if_all_blocked: bool, min_wait_seconds: float
) -> LLMRouter:
    """Build the router under test."""
    # One provider with an intentionally tight rate limit makes the wait-policy
    # decision visible with very little setup.
    return LLMRouter(
        RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.LLAMA_MAVERICK,
            key_id=1,
        ),
        wait_for_cooldown_if_all_blocked=wait_for_cooldown_if_all_blocked,
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=1.0 / min_wait_seconds,
                rpm=1_000_000_000,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            ),
        },
    )


def run_no_wait_probe() -> tuple[LLMRouterResponse, TimeoutError, float]:
    """Run two calls and fail fast when the second one is blocked."""
    router = build_router(
        wait_for_cooldown_if_all_blocked=False,
        min_wait_seconds=_NO_WAIT_MIN_WAIT_SECONDS,
    )
    # The first call proves the route itself is healthy.
    first_response = router.query([_SYSTEM_PROMPT, "Reply ONLY with A."])

    # The second call starts immediately so it collides with the rate limit.
    started_at = time.monotonic()
    with pytest.raises(TimeoutError, match="All routes are blocked") as exc_info:
        router.query([_SYSTEM_PROMPT, "Reply ONLY with B."])

    return first_response, exc_info.value, time.monotonic() - started_at


def run_wait_probe() -> tuple[LLMRouterResponse, LLMRouterResponse, float, float]:
    """Run two calls and wait for the second blocked call to become available."""
    router = build_router(
        wait_for_cooldown_if_all_blocked=True,
        min_wait_seconds=_WAIT_MIN_WAIT_SECONDS,
    )
    first_started_at = time.monotonic()
    # The first call establishes the blocked state for the next request.
    first_response = router.query([_SYSTEM_PROMPT, "Reply ONLY with A."])

    # The second call should now wait instead of failing immediately.
    second_started_at = time.monotonic()
    second_response = router.query([_SYSTEM_PROMPT, "Reply ONLY with B."])
    second_call_seconds = time.monotonic() - second_started_at
    total_elapsed_seconds = time.monotonic() - first_started_at

    return first_response, second_response, second_call_seconds, total_elapsed_seconds


# =============================================================================
# Assertions
# =============================================================================


def assert_no_wait_probe(
    first_response: LLMRouterResponse,
    error: TimeoutError,
    waited_seconds: float,
) -> None:
    """Assert blocked routes fail fast when waiting is disabled."""
    # The first request proves the route itself is otherwise healthy.
    assert _normalize_letter(first_response.output_text) == "A"

    # The second request should fail with the explicit blocked-route message.
    assert "All routes are blocked" in str(error)

    # Disabling waiting means the failure should happen quickly.
    assert waited_seconds < (_NO_WAIT_MIN_WAIT_SECONDS * 0.1)


def assert_wait_probe(
    first_response: LLMRouterResponse,
    second_response: LLMRouterResponse,
    second_call_seconds: float,
    total_elapsed_seconds: float,
) -> None:
    """Assert blocked routes wait and then recover."""
    # Both requests should eventually succeed when waiting is enabled.
    assert _normalize_letter(first_response.output_text) == "A"
    assert _normalize_letter(second_response.output_text) == "B"

    # The timing checks are the proof that we actually waited for the cooldown
    # window rather than succeeding immediately by accident.
    assert second_call_seconds > 0.0
    assert total_elapsed_seconds >= (_WAIT_MIN_WAIT_SECONDS * 0.9)

    # The routing trace should show we resumed the same configured provider/key
    # once that route became available again.
    assert len(second_response.routing_trace) == 1
    assert second_response.routing_trace[0].provider == Provider.NVIDIA.value
    assert second_response.routing_trace[0].key_id == 1


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_blocked_route_raises_without_waiting() -> None:
    """Verify blocked routes fail fast when waiting is disabled."""
    require_vcr_cassette_or_record_mode(
        test_file=__file__,
        test_name="test_blocked_route_raises_without_waiting",
    )
    require_nvidia_key_1()
    # Run the fail-fast variant first.
    first_response, error, waited_seconds = run_no_wait_probe()
    # Then prove the blocked route surfaced quickly.
    assert_no_wait_probe(first_response, error, waited_seconds)


@pytest.mark.hermetic
@pytest.mark.vcr
def test_blocked_route_waits_then_recovers() -> None:
    """Verify blocked routes wait for the rate-limit interval and recover."""
    require_vcr_cassette_or_record_mode(
        test_file=__file__,
        test_name="test_blocked_route_waits_then_recovers",
    )
    require_nvidia_key_1()
    # Run the wait-enabled variant.
    first_response, second_response, second_call_seconds, total_elapsed_seconds = (
        run_wait_probe()
    )
    # Then prove the router waited long enough to recover.
    assert_wait_probe(
        first_response,
        second_response,
        second_call_seconds,
        total_elapsed_seconds,
    )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)

    (
        first_response,
        second_response,
        second_call_seconds,
        total_elapsed_seconds,
    ) = run_wait_probe()

    console.demo_step(
        "What Happened",
        "The first call succeeded immediately, and the next blocked "
        "call waited long enough to recover instead of failing instantly.",
        details=[
            f"Call 1 output: {first_response.output_text.strip()}",
            f"Call 2 output: {second_response.output_text.strip()}",
            f"Call 2 duration: {second_call_seconds:.3f}s",
            f"Total elapsed time: {total_elapsed_seconds:.3f}s",
        ],
    )
    console.demo_outcome(
        "This passed because the cooldown wait policy behaved like a "
        "user would expect: wait when recovery is reasonable, rather "
        "than fail too early."
    )


if __name__ == "__main__":
    main()
# %%
