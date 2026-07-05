# %%
"""LLM Router e2e: QwenChat tool choice + structured output.

Why:
    Verifies that QwenChat supports the new textual named-tool flow with a
    final structured answer.

Covers:
    Area: QwenChat provider
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
            tests.llm_router.e2e.provider_sdk_wrapping.test_qwenchat_tool_choice_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_qwenchat_tool_choice_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

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

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# The setup is intentionally small so the only real question is whether the
# named textual tool flow is obeyed.


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
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


def run_pipeline() -> LLMRouterResponse:
    """Run the QwenChat forced-tool-choice pipeline."""
    # Keep the public call shape explicit even though the provider uses a
    # textual tool workaround behind the adapter.
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
    # The structured answer should identify the forced tool and final result.
    assert parsed.tool_name == "add"
    assert parsed.final_result == 42
    assert parsed.explanation.strip()
    # The runtime trace is the proof that the textual tool path actually ran.
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
        "We ask QwenChat to use one named tool and then return a structured answer.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same forced-tool path the test validates.
    response = run_pipeline()
    assert_pipeline_response(response)

    console.demo_step(
        "What Happened",
        "The model followed the named textual tool path and returned the "
        "expected final structure.",
        details=[
            f"Answer: {response.output_text.strip()}",
            f"Tool trace: {response.tool_trace}",
            f"Usage: {response.usage}",
        ],
    )
    console.demo_outcome(
        "This passed because the named-tool contract and the final structured "
        "answer stayed aligned."
    )


if __name__ == "__main__":
    main()
# %%
