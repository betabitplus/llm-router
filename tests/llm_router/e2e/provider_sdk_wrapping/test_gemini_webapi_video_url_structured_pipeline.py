# %%
"""LLM Router e2e: Gemini WebAPI remote video URL + structured output.

Why:
    Verifies that Gemini WebAPI supports prompt-grounded remote video URLs with
    structured output.

Covers:
    Area: Gemini WebAPI provider
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

Notes:
    Live manual runs require local browser cookies for Gemini WebAPI access.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_gemini_webapi_video_url_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_video_url_structured_pipeline.py
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
    VideoUrlSchema,
)
from tests.llm_router.support.builders import build_test_video_url
from tests.llm_router.support.media.gemini_webapi import can_run_demo, require_runtime
from tests.llm_router.support.media.video import (
    VideoObservation,
    assert_indoor_video_response,
    build_indoor_video_prompt,
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
# Keep one fixed remote clip so this file stays about the URL-based path and
# not changing external inputs.


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
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, video: VideoUrlSchema) -> LLMRouterResponse:
    """Run the Gemini WebAPI remote-video pipeline."""
    # The provider turns the URL into prompt text internally, but the public
    # contract is still one prompt plus one VideoUrlSchema attachment.
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
    assert_indoor_video_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    require_runtime()
    # First execute the URL-based video workflow.
    response = run_pipeline(video=build_test_video_url())
    # Then prove the structured answer matches the expected indoor clip semantics.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    can_run, reason = can_run_demo()
    if not can_run:
        console.print(f"[warning]{reason}[/]")
        raise SystemExit(0)

    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We pass Gemini WebAPI a remote video URL and ask for a structured summary.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same remote-video path the test validates.
    response = run_pipeline(video=build_test_video_url())

    # Validate before printing so the manual walkthrough stays honest.
    parsed = assert_indoor_video_response(response)
    console.demo_step(
        "What Happened",
        "The model analyzed the remote video and returned the expected "
        "structured report.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the URL-based video path behaved like a real "
        "structured media workflow."
    )


if __name__ == "__main__":
    main()
# %%
