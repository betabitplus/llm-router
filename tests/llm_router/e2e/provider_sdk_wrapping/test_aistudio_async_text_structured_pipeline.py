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

"""

from __future__ import annotations

import pytest

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.media.movie import (
    MovieRecord,
    assert_movie_record_response,
    build_movie_prompt,
)

pytestmark = [
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
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
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
    # First run the exact public async flow the file is documenting.
    response = await run_pipeline()
    # Then explain success through the shared structured-output helper.
    assert_pipeline_response(response)
