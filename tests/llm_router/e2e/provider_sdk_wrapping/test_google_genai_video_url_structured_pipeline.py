# %%
"""LLM Router e2e: Google GenAI remote video URL + structured output.

Why:
    Verifies that the native Google client supports remote video URLs with
    structured output.

Covers:
    Area: Google GenAI provider
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

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_google_genai_video_url_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_video_url_structured_pipeline.py
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
from py_lib_tooling import console
from py_lib_tooling import require_vcr_cassette_or_record_mode

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_video,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# A single remote clip keeps the scenario narrow: can the public URL-based
# video path produce structured output?


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
        RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, video: VideoUrlSchema) -> LLMRouterResponse:
    """Run the Google GenAI remote-video pipeline."""
    # Keep the real user-facing call readable: prompt plus remote video URL.
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
    # The shared video helper checks that the action is non-empty and the
    # location matches the expected indoor setting.
    assert_indoor_video_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the exact remote-video path.
    response = run_pipeline(video=build_test_video_url())
    # Then validate the action/location contract shared across providers.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We give the native Google path a remote video URL and ask "
        "for a structured summary.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same URL-based workflow the test uses.
    response = run_pipeline(video=build_test_video_url())

    # Validate before printing so the demo is backed by the same contract.
    parsed = assert_indoor_video_response(response)
    console.demo_step(
        "What Happened",
        "The model returned the expected structured report for the remote video.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the remote-video path produced the same quality "
        "of structured result we expect from a real user workflow."
    )


if __name__ == "__main__":
    main()
# %%
