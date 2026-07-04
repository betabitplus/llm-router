# %%
"""LLM Router e2e: key rotation + per-key waiting.

Why:
    Verifies async key rotation together with per-key provider limits.

Covers:
    Area: routing layer over NVIDIA profiles
    Behavior: key rotation, per-key limits, async execution
    Interface: `LLMRouter(RouterProfile(..., key_id="auto"))`,
    `aquery(...)`

Checks:
    If the three async calls succeed, then the visible replies are `A`, `B`, and `C` in
    order.
    If auto rotation is working, then the first two routing traces use different key
    ids.
    If the third call waits after both keys are used, then its routing trace stays on
    provider `nvidia` and records positive `wait_seconds`.
    If wall-clock timing reflects limiter waiting, then the observed wait is at least
    the traced wait allowance.

Notes:
    Live manual runs require `NVIDIA_API_KEY_1`. When only one NVIDIA secret is
    configured, this scenario mirrors it into `NVIDIA_API_KEY_2` so the router
    can still exercise distinct key IDs.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.route_fallback_and_attempt_policy.test_routing_key_rotation_async_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/route_fallback_and_attempt_policy/test_routing_key_rotation_async_pipeline.py
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
from tests.support.setup import run_async

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_async,
    pytest.mark.cap_routing,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_ASK_1 = "Reply ONLY with A."
_ASK_2 = "Reply ONLY with B."
_ASK_3 = "Reply ONLY with C."
# The prompt set is intentionally trivial so the interesting behavior is key
# selection and waiting, not generation quality.


# =============================================================================
# Helpers
# =============================================================================


def _normalize_letter(text: str) -> str:
    """Normalize single-letter outputs."""
    return text.strip().rstrip(".")


def _prepare_second_nvidia_key() -> str | None:
    """Ensure the auto-rotation scenario has at least two NVIDIA key IDs."""
    key1 = os.getenv("NVIDIA_API_KEY_1", "").strip() or None
    if key1 is None:
        pytest.skip(  # type: ignore[too-many-positional-arguments]
            "Need NVIDIA_API_KEY_1 for the key-rotation scenario."
        )

    previous = os.environ.get("NVIDIA_API_KEY_2")
    os.environ["NVIDIA_API_KEY_2"] = key1
    return previous


# =============================================================================
# Pipeline
# =============================================================================


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.LLAMA_MAVERICK,
            key_id="auto",
        ),
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=0.5,
                rpm=1_000_000_000,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            ),
        },
    )


async def run_pipeline() -> tuple[
    LLMRouterResponse,
    LLMRouterResponse,
    LLMRouterResponse,
    float,
]:
    """Run three calls to exercise key rotation and per-key waiting."""
    # Prepare a second key id first so auto-rotation has a real choice to make.
    previous = _prepare_second_nvidia_key()
    try:
        router = build_router()
        # Call 1 should take the first available key.
        first_response = await router.aquery(
            [_SYSTEM_PROMPT, _ASK_1],
            temperature=0.0,
            seed=42,
        )
        # Call 2 should rotate to the other key instead of reusing the first one.
        second_response = await router.aquery(
            [_SYSTEM_PROMPT, _ASK_2],
            temperature=0.0,
            seed=42,
        )
        # Call 3 should wait because both keys have just been used.
        started_at = time.monotonic()
        third_response = await router.aquery(
            [_SYSTEM_PROMPT, _ASK_3],
            temperature=0.0,
            seed=42,
        )
        waited_seconds = time.monotonic() - started_at
        return first_response, second_response, third_response, waited_seconds
    finally:
        if previous is None:
            os.environ.pop("NVIDIA_API_KEY_2", None)
        else:
            os.environ["NVIDIA_API_KEY_2"] = previous


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_responses(
    first_response: LLMRouterResponse,
    second_response: LLMRouterResponse,
    third_response: LLMRouterResponse,
    waited_seconds: float,
) -> None:
    """Assert key rotation and waiting behavior."""
    # The three visible outputs tell us the three calls completed in order.
    assert _normalize_letter(first_response.data.choices[0].message.content) == "A"
    assert _normalize_letter(second_response.data.choices[0].message.content) == "B"
    assert _normalize_letter(third_response.data.choices[0].message.content) == "C"

    # Distinct key ids on the first two calls are the proof that rotation
    # happened rather than repeated use of one key.
    first_key = first_response.routing_trace[0].key_id
    second_key = second_response.routing_trace[0].key_id
    assert first_key != second_key

    # The third call should still land on NVIDIA, but only after the limiter
    # reported some positive remaining wait once both keys had been used.
    # We do not require a fixed threshold here because part of the per-key
    # interval may already have elapsed while the first two live requests were
    # still in flight.
    third_wait_seconds = third_response.routing_trace[0].wait_seconds
    assert third_response.routing_trace[0].provider == Provider.NVIDIA.value
    assert third_wait_seconds > 0.0

    # The wall-clock duration for the third call should include at least the
    # limiter wait that the routing trace recorded, even after normal timer and
    # scheduling jitter in CI.
    assert waited_seconds >= max(0.0, third_wait_seconds - 0.05)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline() -> None:
    """Verify key rotation and per-key limiting behavior."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # Run the three-call async routing flow once.
    responses = await run_pipeline()
    # Then validate rotation first and waiting second.
    assert_pipeline_responses(*responses)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)

    # Run the same three-call flow the test asserts.
    first_response, second_response, _, waited_seconds = await run_pipeline()

    console.demo_step(
        "What Happened",
        "The async routing flow rotated across keys and then waited "
        "when the limit required a pause.",
        details=[
            f"Call 1 key: {first_response.routing_trace[0].key_id}",
            f"Call 2 key: {second_response.routing_trace[0].key_id}",
            f"Wait before the next allowed call: {waited_seconds:.3f}s",
        ],
    )
    console.demo_outcome(
        "This passed because the router respected key rotation and "
        "wait policy instead of overusing one key."
    )


if __name__ == "__main__":
    run_async(main())
# %%
