# %%
"""LLM Router e2e: OpenAI-compatible image + structured output.

Why:
    Verifies that the generic OpenAI-compatible path supports image input with
    structured output.

Covers:
    Area: OpenAI-compatible client family
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

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_openai_compatible_image_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_openai_compatible_image_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode

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
    get_llm_router_test_data_path,
)
from tests.llm_router.support.media.scene import (
    SceneSummary,
    assert_traffic_scene_response,
    build_scene_summary_prompt,
)

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_image,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_IMAGE_FILENAME = "test_image.png"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# One shared image fixture keeps this file about the OpenAI-compatible
# multimodal path rather than data variation.


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
        RouterProfile(model=Model.PIXTRAL_LARGE, provider=Provider.MISTRAL),
        temperature=0.0,
    )


def run_pipeline(*, image: ImageSchema) -> LLMRouterResponse:
    """Run the OpenAI-compatible image pipeline."""
    # This is the full public call the scenario is about: instructions plus one image.
    router = build_router()
    return router.query(
        [_SYSTEM_PROMPT, build_prompt(), image],
        response_schema=SceneSummary,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the image pipeline response."""
    # Reuse the shared scene helper so every image scenario checks the same
    # traffic-scene contract instead of drifting per provider.
    assert_traffic_scene_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First execute the public multimodal flow once.
    response = run_pipeline(image=build_test_image(_IMAGE_FILENAME))
    # Then validate it against the shared traffic-scene contract.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We send a test image into an OpenAI-compatible route and ask "
        "for a structured scene description.",
        details=[
            f"Image: {get_llm_router_test_data_path(_IMAGE_FILENAME).name}",
            f"Prompt: {build_prompt()}",
        ],
    )

    # Run the same image flow the test validates.
    response = run_pipeline(image=build_test_image(_IMAGE_FILENAME))

    # Validate before printing so the manual walkthrough remains trustworthy.
    parsed = assert_traffic_scene_response(response)
    console.demo_step(
        "What Happened",
        "The model returned the expected structured image summary.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the image path returned the exact kind of "
        "structured scene data this scenario is meant to prove."
    )


if __name__ == "__main__":
    main()
# %%
