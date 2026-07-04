# %%
"""LLM Router e2e: Gemini WebAPI tools + structured output.

Why:
    Verifies that Gemini WebAPI supports the new prompt-driven multi-round tool
    loop with a final structured answer.

Covers:
    Area: Gemini WebAPI provider
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

Notes:
    Live manual runs require local browser cookies for Gemini WebAPI access.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_gemini_webapi_tools_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_tools_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.media.gemini_webapi import can_run_demo, require_runtime
from tests.support.console import console
from tests.support.e2e_vcr_guard import require_vcr_cassette_or_record_mode

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_tools,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# The prompt is deliberately procedural so the scenario proves tool orchestration
# instead of free-form arithmetic.


# =============================================================================
# Helpers
# =============================================================================


class CalculationStep(BaseModel):
    """Structured tool-step summary."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Structured result for the Gemini WebAPI tools scenario."""

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
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
        temperature=0.0,
        seed=42,
    )


def run_pipeline() -> LLMRouterResponse:
    """Run the Gemini WebAPI tools + structured-output pipeline."""
    # Keep the whole public flow visible in one call: prompt, tools, schema,
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
    # The final result is the clearest proof that both tool steps completed.
    assert parsed.final_result == 84
    assert len(parsed.steps) >= 2
    structured_tool_names = {step.tool_name for step in parsed.steps}
    traced_tool_names = {step.tool_name for step in response.tool_trace}
    # The structured answer and runtime trace must agree about what ran.
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
    require_runtime()
    # First run the tool-driven workflow end to end.
    response = run_pipeline()
    # Then check that the structured answer and trace still line up.
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
        "We ask Gemini WebAPI for a structured answer that requires two tool steps.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same end-to-end tool flow the test asserts.
    response = run_pipeline()
    assert_pipeline_response(response)

    console.demo_step(
        "What Happened",
        "The browser-backed route completed the tool loop and returned the "
        "expected final JSON.",
        details=[
            f"Answer: {response.output_text.strip()}",
            f"Tool trace: {response.tool_trace}",
            f"Usage: {response.usage}",
        ],
    )
    console.demo_outcome(
        "This passed because tool execution and the final structured answer "
        "remained aligned across the whole flow."
    )


if __name__ == "__main__":
    main()
# %%
