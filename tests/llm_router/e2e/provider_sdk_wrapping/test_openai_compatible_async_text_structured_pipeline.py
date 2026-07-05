# %%
"""LLM Router e2e: OpenAI-compatible async text + structured output.

Why:
    Verifies that the generic OpenAI-compatible path supports direct-model
    async queries with structured output.

Covers:
    Area: OpenAI-compatible client family
    Behavior: async text input, structured output
    Interface: `LLMRouter(Model.X)`, `aquery(...)`

Checks:
    If the async structured request succeeds, then the response output is non-empty and
    parseable as `LegalCase`.
    If plaintiff extraction is correct, then the plaintiffs include Global AI Corp.
    If defendant extraction is correct, then the defendants include John Doe.
    If multi-party extraction is correct, then the defendants also include Hackers
    United.
    If case metadata is complete, then `court` is non-empty.
    If case metadata is complete, then `case_name` is non-empty.
    If issue extraction is correct, then `legal_issues` is non-empty and mention breach.
    If issue extraction is correct, then `legal_issues` also mention trade secret or
    misappropriation.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_openai_compatible_async_text_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_openai_compatible_async_text_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode, run_async

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.media.legal import (
    LegalCase,
    assert_legal_case_response,
    build_legal_case_prompt,
)

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_async,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "You are a legal assistant. Extract case details."
# The system instruction stays fixed so this file isolates async structured
# extraction on one provider family.


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the legal-case extraction prompt."""
    return build_legal_case_prompt()


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.LLAMA_MAVERICK, provider=Provider.NVIDIA)
    )


async def run_pipeline() -> LLMRouterResponse:
    """Run the async OpenAI-compatible structured-output pipeline."""
    # Keep the real public async call in one place so test and demo stay aligned.
    router = build_router()
    return await router.aquery(
        [_SYSTEM_PROMPT, build_prompt()],
        response_schema=LegalCase,
        temperature=0.0,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the structured-output response."""
    # The legal helper validates that the extracted parties, court, and issues
    # survive the public structured-output path.
    assert_legal_case_response(response)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the public async structured-output flow.
    response = await run_pipeline()
    # Then validate the legal-record contract through the shared helper.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask the OpenAI-compatible path to convert a legal-style "
        "prompt into a structured case record.",
        details=[f"Prompt preview: {build_prompt()[:150]}..."],
    )

    # Run the same async legal extraction path as the test.
    response = await run_pipeline()

    # Validate first so every printed field is already part of a checked result.
    case = assert_legal_case_response(response)
    console.demo_step(
        "What Happened",
        f"The model returned a structured case summary for '{case.case_name}'.",
        details=[
            f"Court: {case.court}",
            f"Plaintiffs: {', '.join(p.name for p in case.plaintiffs)}",
            f"Defendants: {', '.join(p.name for p in case.defendants)}",
            f"Issues: {', '.join(case.legal_issues)}",
            f"Usage: {response.usage}",
        ],
    )
    console.demo_outcome(
        "This passed because the legal record stayed structured and "
        "preserved the important parties and issues the scenario "
        "asked for."
    )


if __name__ == "__main__":
    run_async(main())
# %%
