"""LLM Router e2e: AI Studio remote video URL + structured output.

Why:
    Verifies that AI Studio supports remote video URLs with structured output.

Covers:
    Area: AI Studio provider
    Behavior: `VideoUrlSchema`, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If the video response succeeds, then the output is non-empty and parseable as
    `VideoObservation`.
    If activity extraction is grounded correctly, then `action` is non-empty.
    If location extraction is grounded correctly, then `location` mentions a gym,
    studio, indoor, training, or dance context.
    If evidence extraction is grounded correctly, then the combined evidence mentions
    activity cues or indoor-scene cues.

"""

from __future__ import annotations

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
    VideoUrlSchema,
)
from tests.llm_router.support.builders import build_test_video_url
from tests.llm_router.support.media.video import (
    VideoObservation,
    assert_indoor_video_response,
    build_indoor_video_prompt,
)

pytestmark = [
    pytest.mark.cap_video,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# Using one fixed remote clip keeps the scenario about URL-based video support,
# not fixture variability.


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the remote-video prompt."""
    return build_indoor_video_prompt()


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, video: VideoUrlSchema) -> LLMRouterResponse:
    """Run the AI Studio remote-video pipeline."""
    # This is the exact public call we care about: prompt plus remote video URL.
    router = build_router()
    return router.query(
        [_SYSTEM_PROMPT, build_prompt(), video],
        response_schema=VideoObservation,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the remote-video response."""
    # Keep the pass/fail logic identical to the Google scenario so this file
    # proves provider parity rather than a different contract.
    assert_indoor_video_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    # First execute the URL-based video workflow.
    response = run_pipeline(video=build_test_video_url())
    # Then prove the structured answer matches the expected indoor clip semantics.
    assert_pipeline_response(response)
