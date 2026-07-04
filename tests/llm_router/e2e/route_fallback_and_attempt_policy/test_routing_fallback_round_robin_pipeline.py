# %%
"""LLM Router e2e: fallback + round-robin routing.

Why:
    Verifies sync fallback and round-robin routing across multiple
    profiles.

Covers:
    Area: routing layer over NVIDIA profiles
    Behavior: fallback routing, round-robin routing
    Interface: `LLMRouter([RouterProfile(...), ...])`, `query(...)`

Checks:
    If fallback recovery succeeds on the first call, then the visible output is `OK`.
    If fallback recovery succeeds on the first call, then the response provider and
    model stay `nvidia` and `llama-maverick`.
    If the first routing trace records fallback correctly, then it shows `not-a-
    provider` failing by `ValueError` before the second route succeeds at temperature
    `0.0`.
    If round-robin state advances after that success, then the second call returns
    `12345`.
    If round-robin state advances after fallback, then the second response still uses
    provider `nvidia` and model `llama-maverick`.
    If the second call starts from the previously successful route, then its routing
    trace has exactly 1 entry at route index `1`.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.route_fallback_and_attempt_policy.test_routing_fallback_round_robin_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/route_fallback_and_attempt_policy/test_routing_fallback_round_robin_pipeline.py
"""

from __future__ import annotations

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
    pytest.mark.cap_routing,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_ASK_OK = "Reply ONLY with OK."
_ASK_NUM = "Reply ONLY with 12345."
# The two prompts are intentionally tiny so the interesting part is the routing
# decision, not content generation.


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.

# =============================================================================
# Pipeline
# =============================================================================


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        [
            RouterProfile(provider="not-a-provider", model=Model.LLAMA_MAVERICK),
            RouterProfile(provider=Provider.NVIDIA, model=Model.LLAMA_MAVERICK),
        ],
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=0.0,
                rpm=0.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            ),
        },
    )


def run_pipeline() -> tuple[LLMRouterResponse, LLMRouterResponse]:
    """Run two calls to exercise fallback and round-robin behavior."""
    router = build_router()
    # Call 1 is the fallback proof: the invalid route should fail and the valid
    # route should rescue the request.
    first_response = router.query(
        [_SYSTEM_PROMPT, _ASK_OK],
        temperature=0.0,
        seed=42,
    )
    # Call 2 is the round-robin proof: the next starting point should now be
    # the previously successful route.
    second_response = router.query(
        [_SYSTEM_PROMPT, _ASK_NUM],
        temperature=0.0,
        seed=42,
    )
    return first_response, second_response


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_responses(
    first_response: LLMRouterResponse,
    second_response: LLMRouterResponse,
) -> None:
    """Assert fallback and round-robin routing traces."""
    # Call 1 should still succeed because the router falls back to the valid
    # NVIDIA route after the invalid route fails.
    assert first_response.output_text.strip() == "OK"
    assert first_response.provider == Provider.NVIDIA.value
    assert first_response.model == Model.LLAMA_MAVERICK.value

    # The first routing trace must explicitly show the failed invalid provider
    # followed by the successful real provider.
    assert len(first_response.routing_trace) == 2
    assert first_response.routing_trace[0].provider == "not-a-provider"
    assert first_response.routing_trace[0].error_type == "ValueError"
    assert first_response.routing_trace[1].error_type is None
    assert first_response.routing_trace[1].temperature == 0.0

    # Call 2 should start from route index 1 because the router advances its
    # round-robin starting point after the previous successful fallback.
    assert second_response.output_text.strip() == "12345"
    assert second_response.provider == Provider.NVIDIA.value
    assert second_response.model == Model.LLAMA_MAVERICK.value
    assert len(second_response.routing_trace) == 1
    assert second_response.routing_trace[0].route_index == 1


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify sync fallback and round-robin behavior."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the two-call routing flow exactly once.
    first_response, second_response = run_pipeline()
    # Then explain the routing decisions through the trace assertions.
    assert_pipeline_responses(first_response, second_response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)

    # Run the same two-call flow the test validates.
    first_response, second_response = run_pipeline()

    console.demo_step(
        "What Happened",
        "Two consecutive calls used the routing profile, and the traces "
        "showed the fallback and round-robin decisions.",
        details=[
            f"Call 1 output: {first_response.output_text.strip()}",
            f"Call 1 trace: {first_response.routing_trace}",
            f"Call 2 output: {second_response.output_text.strip()}",
            f"Call 2 trace: {second_response.routing_trace}",
        ],
    )
    console.demo_outcome(
        "This passed because routing decisions changed in the expected order "
        "instead of repeatedly picking the same route blindly."
    )


if __name__ == "__main__":
    main()
# %%
