# %%
"""LLM Router e2e: AI Studio local video + structured output.

Why:
    Verifies that AI Studio supports local video input with structured output.

Covers:
    Area: AI Studio provider
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
            tests.llm_router.e2e.provider_sdk_wrapping.test_aistudio_video_file_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_video_file_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode

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
    pytest.mark.e2e_contract,
    pytest.mark.cap_video,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# One fixed prompt and one fixed clip keep this file focused on local video
# handling rather than content variation.


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
        RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, video: VideoSchema) -> LLMRouterResponse:
    """Run the AI Studio local-video pipeline."""
    # This mirrors the real public workflow: prompt plus one uploaded video file.
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
    # The shared rooftop-video helper proves both the action and location match
    # the expected local clip semantics.
    assert_rooftop_video_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First exercise the public local-video path.
    response = run_pipeline(video=build_test_video_file())
    # Then validate the rooftop/action contract through the shared helper.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We upload a local video file and ask AI Studio to summarize "
        "it in a structured format.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same upload flow that pytest asserts.
    response = run_pipeline(video=build_test_video_file())

    # Validate before printing so the demo stays aligned with the assertions.
    parsed = assert_rooftop_video_response(response)
    console.demo_step(
        "What Happened",
        "The model returned a valid structured summary of the uploaded video.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the local video path produced the "
        "structured evidence the scenario expects."
    )


if __name__ == "__main__":
    main()
# %%
