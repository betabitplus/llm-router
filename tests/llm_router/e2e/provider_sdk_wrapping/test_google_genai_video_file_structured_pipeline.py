# %%
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

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_google_genai_video_file_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_video_file_structured_pipeline.py
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
from tests.support.console import console
from tests.support.e2e_vcr_guard import require_vcr_cassette_or_record_mode

pytestmark = [
    pytest.mark.e2e_contract,
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
        RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.GOOGLE),
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
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First exercise the public local-video workflow.
    response = run_pipeline(video=build_test_video_file())
    # Then validate that the structured answer matches the shared rooftop contract.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We upload a local video file to the native Google path and ask "
        "for a structured summary.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same local-video flow the test documents.
    response = run_pipeline(video=build_test_video_file())

    # Validate before printing so the manual walkthrough stays grounded.
    parsed = assert_rooftop_video_response(response)
    console.demo_step(
        "What Happened",
        "The model returned a structured description of the local video.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the local video workflow produced the structured "
        "facts and evidence the scenario expects."
    )


if __name__ == "__main__":
    main()
# %%
