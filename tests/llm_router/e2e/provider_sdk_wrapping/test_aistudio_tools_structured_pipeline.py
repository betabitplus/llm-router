# %%
"""LLM Router e2e: AI Studio tools + structured output.

Why:
    Verifies that AI Studio supports multi-round tool execution followed by
    structured output in one public call.

Covers:
    Area: AI Studio provider
    Behavior: tool calling, required tool use, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`, `tools=[...]`

Checks:
    If the multi-round tool flow succeeds, then the output is parseable as
    `CalculationAudit`.
    If both tool steps complete, then `final_result` is `84`.
    If the structured answer preserves the workflow, then it contains at least 2 steps.
    If the structured answer reflects the intended workflow, then its tool names include
    both `add` and `multiply`.
    If the runtime loop actually used both steps, then the tool trace contains at least
    2 entries.
    If the structured answer and runtime trace agree, then traced tool names cover the
    structured tool names.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_aistudio_tools_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_tools_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode
from pydantic import BaseModel, Field

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_tools,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# The prompt is deliberately procedural so the scenario proves multi-round tool
# orchestration, not free-form reasoning.


# =============================================================================
# Helpers
# =============================================================================


class CalculationStep(BaseModel):
    """Structured tool-step summary."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Structured result for the AI Studio tools scenario."""

    steps: list[CalculationStep] = Field(min_length=2)
    final_result: int


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as JSON."""
    return {"result": a * b}


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the multi-round structured tool prompt."""
    return (
        "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
        "Step 1: use add with a=40 and b=2.\n"
        "Step 2: multiply the step-1 result by 2.\n"
        "Return JSON with:\n"
        "- steps: a list of tool call summaries with `tool_name` and `result`\n"
        "- final_result\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH_LITE, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


def run_pipeline() -> LLMRouterResponse:
    """Run the AI Studio tools + structured-output pipeline."""
    # Keep the entire public flow visible in one call: prompt, tools, schema,
    # and a bounded number of tool rounds.
    router = build_router()
    return router.query(
        [_SYSTEM_PROMPT, build_prompt()],
        tools=[add, multiply],
        tool_choice="required",
        response_schema=CalculationAudit,
        max_tool_rounds=4,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the structured multi-round tool response."""
    parsed = CalculationAudit.model_validate(parse_json_object(response.output_text))
    # The final result is the simplest proof that both tool steps completed.
    assert parsed.final_result == 84
    # The structured answer itself should expose both tool stages.
    assert len(parsed.steps) >= 2
    structured_tool_names = {step.tool_name for step in parsed.steps}
    traced_tool_names = {step.tool_name for step in response.tool_trace}
    # The final JSON and the runtime trace must agree about which tools ran.
    assert structured_tool_names >= {"add", "multiply"}
    assert len(response.tool_trace) >= 2
    assert traced_tool_names >= structured_tool_names


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the tool-driven workflow end to end.
    response = run_pipeline()
    # Then check that the answer and the trace still line up.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask AI Studio for a structured answer that requires local tool usage.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same end-to-end tool workflow used by the test.
    response = run_pipeline()

    # Assert first so the printed output is backed by the same contract.
    assert_pipeline_response(response)
    console.demo_step(
        "What Happened",
        "The model used the tool flow and returned the expected "
        "structured-style answer.",
        details=[
            f"Answer: {response.output_text.strip()}",
            f"Tool trace: {response.tool_trace}",
        ],
    )
    console.demo_outcome(
        "This passed because the scenario proved that tool "
        "orchestration and the final answer stayed aligned."
    )


if __name__ == "__main__":
    main()
# %%
