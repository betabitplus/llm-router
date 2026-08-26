"""LLM Router e2e: Gemini WebAPI image + structured output.

Why:
    Verifies that the browser-backed Gemini route supports image input with
    local structured-output validation.

Covers:
    Area: Gemini WebAPI provider
    Behavior: image input, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If the image response succeeds, then the output is non-empty and parseable as
    `SceneSummary`.
    If evidence extraction is complete, then every evidence item is non-empty.
    If the scene is grounded correctly, then the combined evidence mentions road,
    highway, street, traffic, car, or lane cues.
    If setting extraction is correct, then `setting` mentions a road, highway, street,
    or traffic context.
    If subject extraction is correct, then the combined subject, objects, and evidence
    mention cars or vehicles.
    If object grounding is correct, then the combined objects and evidence mention lanes
    or traffic.
    If fixture-specific grounding is correct, then the combined objects and evidence
    mention a cue such as a van, guardrail, barrier, road sign, or dashed marking.

Notes:
    Live execution requires local browser cookies for Gemini WebAPI access.

"""

from __future__ import annotations

import pytest

from llm_router import (
    ImageSchema,
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
)
from tests.llm_router.support.builders import (
    build_test_image,
)
from tests.llm_router.support.media.gemini_webapi import require_runtime
from tests.llm_router.support.media.scene import (
    SceneSummary,
    assert_traffic_scene_response,
    build_scene_summary_prompt,
)

pytestmark = [
    pytest.mark.cap_image,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_IMAGE_FILENAME = "test_image.png"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# One shared fixture keeps this file focused on provider behavior, not image variance.


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the structured-image prompt."""
    return build_scene_summary_prompt()


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, image: ImageSchema) -> LLMRouterResponse:
    """Run the Gemini WebAPI image pipeline."""
    # Keep the public multimodal call easy to read: instructions plus one image.
    router = build_router()
    return router.query(
        [_SYSTEM_PROMPT, build_prompt(), image],
        response_schema=SceneSummary,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the structured image response."""
    assert_traffic_scene_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_runtime()
    # First run the exact public image workflow.
    response = run_pipeline(image=build_test_image(_IMAGE_FILENAME))
    # Then validate it against the shared traffic-scene contract.
    assert_pipeline_response(response)
