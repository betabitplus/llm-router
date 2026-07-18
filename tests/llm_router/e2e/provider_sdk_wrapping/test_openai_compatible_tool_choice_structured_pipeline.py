# %%
"""LLM Router e2e: OpenAI-compatible tool choice + structured output.

Why:
    Verifies that an OpenAI-compatible route can force one callable tool and
    still return structured output.

Covers:
    Area: OpenAI-compatible client family
    Behavior: tool calling, explicit `tool_choice`, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`, `tools=[...]`

Checks:
    If the forced structured tool flow succeeds, then the output is parseable as
    `ToolResult`.
    If the named-tool contract is honored, then `tool_name` is `add`.
    If the forced call performs the intended math, then `final_result` is `42`.
    If the structured answer is complete, then `explanation` is non-empty.
    If the runtime tool path really runs, then the response records a non-empty tool
    trace.
    If only the forced tool is used, then the tool trace contains only `add`.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_openai_compatible_tool_choice_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_openai_compatible_tool_choice_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode
from pydantic import BaseModel

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
# The setup is intentionally small so the scenario stays about forced tool
# choice rather than prompt complexity.


# =============================================================================
# Helpers
# =============================================================================


class ToolResult(BaseModel):
    """Structured result for the forced-tool-choice scenario."""

    tool_name: str
    final_result: int
    explanation: str


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
    """Build the forced-tool-choice prompt."""
    return (
        "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
        "Use ONLY add with a=40 and b=2, then return JSON with:\n"
        "- tool_name\n"
        "- final_result\n"
        "- explanation\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.LLAMA_8B, provider=Provider.NVIDIA),
        temperature=0.0,
        seed=42,
    )


def run_pipeline() -> LLMRouterResponse:
    """Run the OpenAI-compatible forced-tool-choice pipeline."""
    # Keep the real user workflow visible in one call: prompt, tools, forced
    # choice, schema, and tool-round limit.
    router = build_router()
    return router.query(
        [_SYSTEM_PROMPT, build_prompt()],
        tools=[add, multiply],
        tool_choice={"type": "function", "function": {"name": "add"}},
        response_schema=ToolResult,
        max_tool_rounds=2,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the structured forced-tool-choice response."""
    parsed = ToolResult.model_validate(parse_json_object(response.output_text))
    # First prove the model reported the tool path we intentionally forced.
    assert parsed.tool_name == "add"
    # Then prove the actual math outcome came from that forced call.
    assert parsed.final_result == 42
    # We still require a non-empty explanation so the answer is not a stub.
    assert parsed.explanation.strip()
    # Finally, verify the runtime trace agrees with the structured answer.
    assert response.tool_trace
    assert {step.tool_name for step in response.tool_trace} == {"add"}


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the exact forced-tool workflow.
    response = run_pipeline()
    # Then prove the structured result and runtime trace agree.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask an OpenAI-compatible route a question that should force "
        "a specific tool choice.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same forced-tool path the test asserts.
    response = run_pipeline()

    # Reuse the assertion helper before printing so the demo stays in sync.
    assert_pipeline_response(response)
    console.demo_step(
        "What Happened",
        "The model used the expected tool flow and then produced the final answer.",
        details=[
            f"Answer: {response.output_text.strip()}",
            f"Tool trace: {response.tool_trace}",
            f"Usage: {response.usage}",
        ],
    )
    console.demo_outcome(
        "This passed because the model respected the tool-choice contract "
        "instead of bypassing the tool layer."
    )


if __name__ == "__main__":
    main()
# %%
