# %%
"""LLM Router e2e: Google GenAI profile tools + structured output.

Why:
    Verifies that profile-level tools, required tool use, and structured output
    work together on the native Google path.

Covers:
    Area: Google GenAI provider
    Behavior: profile-level tools, required tool use, structured output
    Interface: `LLMRouter(RouterProfile(..., tools=[...]))`, `query(...)`

Checks:
    If the profile-backed tool flow succeeds, then the output is parseable as
    `CalculationAudit`.
    If the tool calculation is correct, then `final_result` is `323`.
    If the structured answer preserves tool usage, then `tool_calls` is non-empty.
    If the structured answer reports the real tool step, then the first tool-call name
    is `multiply`.
    If the runtime tool path really runs, then the response records a non-empty tool
    trace.
    If the scenario stays on its single configured route, then the routing trace has
    exactly 1 entry from provider `google`.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_google_genai_profile_tools_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_profile_tools_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object
from py_lib_tooling import console
from py_lib_tooling import require_vcr_cassette_or_record_mode

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_tools,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_TOOL_PROMPT = (
    "You have a tool named multiply(a, b) that returns {result}.\n"
    "Compute 17*19 using the tool.\n"
    "Then return JSON with:\n"
    "- final_result\n"
    "- tool_calls: a list of tool call summaries with `tool_name` and `result`\n\n"
    "Return ONLY valid JSON. No markdown."
)
# The prompt is intentionally explicit so we can judge whether profile-level
# tools, required tool use, and structured output stayed aligned.


# =============================================================================
# Helpers
# =============================================================================


class ToolCallSummary(BaseModel):
    """Structured tool-call summary for the final JSON response."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Structured result for the profile-tools scenario."""

    final_result: int
    tool_calls: list[ToolCallSummary] = Field(min_length=1)


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as JSON."""
    return {"result": a * b}


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the profile-tools prompt."""
    return _TOOL_PROMPT


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(
            provider=Provider.GOOGLE,
            model=Model.GEMINI_FLASH_LITE,
            tools=[multiply],
        ),
        temperature=0.0,
        seed=42,
    )


def run_pipeline() -> LLMRouterResponse:
    """Run the profile-tools pipeline."""
    # Keep the public call compact: prompt, required tool use, schema, and
    # a bounded tool loop.
    router = build_router()
    return router.query(
        build_prompt(),
        tool_choice="required",
        response_schema=CalculationAudit,
        max_tool_rounds=4,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the profile-tools structured response."""
    parsed = CalculationAudit.model_validate(parse_json_object(response.output_text))
    # The structured answer must report the correct final calculation.
    assert parsed.final_result == 323
    # The final JSON must also acknowledge at least one tool step.
    assert parsed.tool_calls
    assert parsed.tool_calls[0].tool_name == "multiply"
    # The runtime trace must confirm the tool path actually happened.
    assert response.tool_trace
    # This scenario is about one Google route only, so the trace must stay on
    # that single configured provider.
    assert len(response.routing_trace) == 1
    assert response.routing_trace[0].provider == Provider.GOOGLE.value


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the exact public tool workflow.
    response = run_pipeline()
    # Then prove the structured answer, tool trace, and route all agree.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask the Google profile route for a structured answer that "
        "depends on tool usage.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same profile-tools flow that pytest asserts.
    response = run_pipeline()

    # Validate first so the demo cannot drift from the checked contract.
    assert_pipeline_response(response)
    console.demo_step(
        "What Happened",
        "The request went through the intended tool path and returned "
        "a valid final answer.",
        details=[
            f"Answer: {response.output_text.strip()}",
            f"Tool trace: {response.tool_trace}",
            f"Routing trace: {response.routing_trace}",
        ],
    )
    console.demo_outcome(
        "This passed because routing, tool usage, and the final "
        "answer all lined up with the scenario contract."
    )


if __name__ == "__main__":
    main()
# %%
