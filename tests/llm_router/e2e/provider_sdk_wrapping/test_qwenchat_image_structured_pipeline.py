# %%
"""LLM Router e2e: QwenChat image + structured output.

Why:
    Verifies that the QwenChat image-upload path works together with structured
    output.

Covers:
    Area: QwenChat provider
    Behavior: image input, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`, `response_schema=...`

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
            tests.llm_router.e2e.provider_sdk_wrapping.test_qwenchat_image_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_qwenchat_image_structured_pipeline.py
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
    get_llm_router_test_data_path,
)
from tests.llm_router.support.media.scene import (
    SceneSummary,
    assert_traffic_scene_response,
    build_scene_summary_prompt,
)
from tests.support.console import console
from tests.support.e2e_vcr_guard import require_vcr_cassette_or_record_mode

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
# One stable fixture keeps the scenario about Qwen image handling rather than
# content variation.


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
        RouterProfile(model=Model.QWEN3_VL_PLUS, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, image: ImageSchema) -> LLMRouterResponse:
    """Run the QwenChat image pipeline."""
    # Keep the real public multimodal call explicit.
    router = build_router()
    return router.query(
        [f"{_SYSTEM_PROMPT}\n\n{build_prompt()}", image],
        response_schema=SceneSummary,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the structured image response."""
    # Shared validation keeps Qwen image behavior aligned with the rest of the
    # image provider-wrapping slice.
    assert_traffic_scene_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the public image workflow once.
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
        "We send a test image to QwenChat and ask for a structured scene summary.",
        details=[
            f"Image: {get_llm_router_test_data_path(_IMAGE_FILENAME).name}",
            f"Prompt: {build_prompt()}",
        ],
    )

    # Run the same image path the test validates.
    response = run_pipeline(image=build_test_image(_IMAGE_FILENAME))

    # Validate before printing so the walkthrough stays backed by assertions.
    parsed = assert_traffic_scene_response(response)
    console.demo_step(
        "What Happened",
        "QwenChat returned a structured description of the image.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the image analysis returned the fields "
        "and evidence the scenario expects."
    )


if __name__ == "__main__":
    main()
# %%
