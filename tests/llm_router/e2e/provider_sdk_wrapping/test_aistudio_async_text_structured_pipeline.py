# %%
"""LLM Router e2e: AI Studio async text + structured output.

Why:
    Verifies that AI Studio supports async structured text generation through
    the public router API.

Covers:
    Area: AI Studio provider
    Behavior: async text input, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `aquery(...)`

Checks:
    If the async structured request succeeds, then the response output is non-empty and
    parseable as `MovieRecord`.
    If title extraction is correct, then `movie_title` is `Inception`.
    If director extraction is correct, then `director` mentions Nolan.
    If the summary field is complete, then `tagline` is non-empty.
    If cast extraction is complete, then the record contains at least 3 cast entries.
    If review extraction is complete, then the record contains at least 2 reviews.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_aistudio_async_text_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_async_text_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode, run_async

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.media.movie import (
    MovieRecord,
    assert_movie_record_response,
    build_movie_prompt,
)

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_async,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "You are a movie database API."
# Keep the instructions deterministic so this scenario stays about async
# structured output, not prompt creativity.


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the movie-record prompt."""
    return build_movie_prompt()


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


async def run_pipeline() -> LLMRouterResponse:
    """Run the async AI Studio structured-output pipeline."""
    # Keep the real public async call in one place so tests and demos exercise
    # the exact same workflow.
    router = build_router()
    return await router.aquery(
        [_SYSTEM_PROMPT, build_prompt()],
        response_schema=MovieRecord,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the structured-output response."""
    # The shared movie helper verifies the important contract fields such as
    # title, director, cast, and reviews in one consistent place.
    assert_movie_record_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the exact public async flow the file is documenting.
    response = await run_pipeline()
    # Then explain success through the shared structured-output helper.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask AI Studio to turn a plain text prompt into a structured movie record.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same async path as the test so manual output mirrors pytest.
    response = await run_pipeline()

    # Validate first, then print the parsed record the assertions already trust.
    parsed = assert_movie_record_response(response)
    console.demo_step(
        "What Happened",
        f"The model returned a valid structured record for '{parsed.movie_title}'.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the response was structured, readable, "
        "and matched the movie schema expected by the scenario."
    )


if __name__ == "__main__":
    run_async(main())
# %%
