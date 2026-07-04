# %%
"""LLM Router e2e: AI Studio explicit tool choice.

Why:
    Verifies that AI Studio can force a specific callable tool through
    `tool_choice`.

Covers:
    Area: AI Studio provider
    Behavior: tool calling, explicit `tool_choice`
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`, `tools=[...]`

Checks:
    If forced tool choice is honored, then the visible output is `42`.
    If the tool path really runs, then the response records a non-empty tool trace.
    If only the forced tool is used, then the tool trace contains only `add`.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_aistudio_tool_choice_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_tool_choice_pipeline.py
"""

from __future__ import annotations

import pytest

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.support.console import console
from tests.support.e2e_vcr_guard import require_vcr_cassette_or_record_mode

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_tools,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# The prompt and tool list stay tiny on purpose so the only real question is
# whether forced tool choice is obeyed.


# =============================================================================
# Helpers
# =============================================================================


def normalize_number_reply(text: str) -> str:
    """Normalize short numeric replies for stable assertions."""
    return text.strip().rstrip(".")


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
        "Use ONLY add with a=40 and b=2, then reply with ONLY the number."
    )


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH_LITE, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


def run_pipeline() -> LLMRouterResponse:
    """Run the forced-tool-choice pipeline."""
    # This is the whole public workflow: one prompt, two tools, one forced choice.
    router = build_router()
    return router.query(
        [_SYSTEM_PROMPT, build_prompt()],
        tools=[add, multiply],
        tool_choice={"type": "function", "function": {"name": "add"}},
        max_tool_rounds=2,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the forced-tool-choice response."""
    # The visible answer should be the expected numeric result.
    assert normalize_number_reply(response.output_text) == "42"
    # The tool trace is the key proof that the model obeyed the forced choice
    # instead of replying directly without the tool layer.
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
    # First execute the user-facing tool-choice flow.
    response = run_pipeline()
    # Then prove the answer and tool trace tell the same story.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask AI Studio a question that should force a specific tool choice.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the exact same tool-choice path as the test.
    response = run_pipeline()

    # Reuse the assertion helper so the demo cannot drift from the test contract.
    assert_pipeline_response(response)
    console.demo_step(
        "What Happened",
        "The model answered through the expected tool-calling path.",
        details=[
            f"Answer: {response.output_text.strip()}",
            f"Tool trace: {response.tool_trace}",
        ],
    )
    console.demo_outcome(
        "This passed because the model did not just answer directly; "
        "it used the tool path the scenario is meant to validate."
    )


if __name__ == "__main__":
    main()
# %%
