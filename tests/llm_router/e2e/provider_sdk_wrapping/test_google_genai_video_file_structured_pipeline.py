"""LLM Router e2e: Google GenAI local video + structured output.

Why:
    Verifies that the native Google client supports local video input with
    structured output.

Covers:
    Area: Google GenAI provider
    Behavior: `VideoSchema`, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If the video response succeeds, then the output is non-empty and parseable as
    `VideoObservation`.
    If action extraction is grounded correctly, then `action` mentions a jump or leap.
    If location extraction is grounded correctly, then `location` mentions a rooftop,
    building, skyscraper, or high-rise context.
    If evidence extraction is grounded correctly, then the combined evidence mentions
    motion, jump, air, landing, roof, or building cues.

"""

from __future__ import annotations

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
    VideoSchema,
)
from tests.llm_router.support.builders import build_test_video_file
from tests.llm_router.support.media.video import (
    VideoObservation,
    assert_rooftop_video_response,
    build_rooftop_video_prompt,
)

pytestmark = [
    pytest.mark.cap_video,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# One stable clip keeps this file about local-video capability, not fixture noise.


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the local-video prompt."""
    return build_rooftop_video_prompt()


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, video: VideoSchema) -> LLMRouterResponse:
    """Run the Google GenAI local-video pipeline."""
    # This is the full public flow: prompt plus one uploaded local video.
    router = build_router()
    return router.query(
        [_SYSTEM_PROMPT, build_prompt(), video],
        response_schema=VideoObservation,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the local-video response."""
    # Keep the local-video contract identical to the AI Studio scenario so the
    # test difference is provider behavior, not assertion drift.
    assert_rooftop_video_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    # First exercise the public local-video workflow.
    response = run_pipeline(video=build_test_video_file())
    # Then validate that the structured answer matches the shared rooftop contract.
    assert_pipeline_response(response)
