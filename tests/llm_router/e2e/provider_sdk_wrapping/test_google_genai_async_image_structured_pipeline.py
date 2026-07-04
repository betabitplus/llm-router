# %%
"""LLM Router e2e: Google GenAI async image + structured output.

Why:
    Verifies that the native Google client supports async multimodal requests
    with structured output.

Covers:
    Area: Google GenAI provider
    Behavior: async image input, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `aquery(...)`

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
            tests.llm_router.e2e.provider_sdk_wrapping.test_google_genai_async_image_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_async_image_structured_pipeline.py
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
from tests.support.setup import run_async

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_async,
    pytest.mark.cap_image,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_IMAGE_FILENAME = "test_image.png"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# One deterministic image fixture keeps the scenario about async multimodal
# support rather than changing content.


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
        RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )


async def run_pipeline(*, image: ImageSchema) -> LLMRouterResponse:
    """Run the async Google GenAI image pipeline."""
    # Keep the real user-facing async call centralized and easy to inspect.
    router = build_router()
    return await router.aquery(
        [_SYSTEM_PROMPT, build_prompt(), image],
        response_schema=SceneSummary,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the image pipeline response."""
    assert_traffic_scene_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First exercise the public async image path once.
    response = await run_pipeline(image=build_test_image(_IMAGE_FILENAME))
    # Then validate that the returned structure matches the common scene contract.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We send one image into the native Google async path and ask "
        "for structured scene data.",
        details=[
            f"Image: {get_llm_router_test_data_path(_IMAGE_FILENAME).name}",
            f"Prompt: {build_prompt()}",
        ],
    )

    # Run the exact same async path the test uses.
    response = await run_pipeline(image=build_test_image(_IMAGE_FILENAME))

    # Validate before printing so the walkthrough stays aligned with pytest.
    parsed = assert_traffic_scene_response(response)
    console.demo_step(
        "What Happened",
        "The async Google path returned a valid structured scene summary.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the public async image path produced a "
        "complete structured result rather than just free text."
    )


if __name__ == "__main__":
    run_async(main())
# %%
