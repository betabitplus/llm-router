# %%
"""OpenAI-compatible async structured tool-loop workbench script.

Why:
    Shows that the `openai` SDK async client can surface tool calls, accept
    local tool results, and return final structured JSON in a real
    OpenAI-compatible loop.

Covers:
    Area: openai-compatible live async tool calling
    Behavior: async multi-round tool calling, tool-role messages, final
        structured output
    Interface: `AsyncOpenAI().chat.completions.create(...)`

Checks:
    If the first live round requests the declared tool surface, then the live tool
        protocol accepted the callable boundary.
    If `tool_trace` preserves the executed tool steps and results, then the manual run
        keeps the local execution evidence behind the loop.
    If `final_output` repeats the same `final_result` and tool-summary steps, then the
        final structured JSON stayed aligned with the executed tool trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.openai.tool_loop_structured_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.openai.tool_loop_structured_async
"""

from __future__ import annotations

from typing import Any

from tests.support.console import console
from tests.support.setup import run_async
from workbench.llm_router.openai._sdk_helpers import (
    build_async_client,
    provider_api_key_env,
)
from workbench.llm_router.openai._structured_output import TOOL_LOOP_RESPONSE_FORMAT
from workbench.llm_router.openai._tool_loop import (
    build_demo_math_tools,
    demo_math_registry,
    run_async_tool_loop,
)

# =============================================================================
# Scenario
# =============================================================================

_BASE_URL = "https://api.mistral.ai/v1"
_API_KEY_ENV = provider_api_key_env("MISTRAL")
_MODEL = "mistral-large-latest"
_PROMPT = (
    "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
    "Step 1: use add with a=2 and b=3.\n"
    "Step 2: multiply the step-1 result by 4.\n"
    "Return JSON with:\n"
    "- final_result\n"
    "- steps: a list of tool summaries with `tool_name` and `result`\n\n"
    "Return ONLY valid JSON. No markdown."
)
_TOOLS = build_demo_math_tools()


# =============================================================================
# Helpers
# =============================================================================


def _require_structured_result(
    result: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract the final JSON output and tool trace from one loop result."""
    final_output = result.get("final_output")
    tool_trace = result.get("tool_trace")
    if not isinstance(final_output, dict) or not isinstance(tool_trace, list):
        msg = "The live tool loop did not return the expected structured result."
        raise TypeError(msg)
    return final_output, tool_trace


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one real async OpenAI-compatible tool loop to final structured JSON."""
    client = build_async_client(api_key_env=_API_KEY_ENV, base_url=_BASE_URL)
    return await run_async_tool_loop(
        client=client,
        model=_MODEL,
        prompt=_PROMPT,
        tools=_TOOLS,
        registry=demo_math_registry(),
        tool_choice="required",
        max_rounds=4,
        final_response_format=TOOL_LOOP_RESPONSE_FORMAT,
    )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Running one real async OpenAI-compatible tool loop with two declared "
        "tools and a final structured JSON answer.",
        details=(
            f"Base URL: {_BASE_URL}",
            f"Model: {_MODEL}",
            "Declared tools: add(a, b), multiply(a, b)",
            "Tool choice: required",
        ),
    )

    result = await run_pipeline()
    final_output, tool_trace = _require_structured_result(result)
    console.demo_step(
        "Observed Tool Loop",
        "The live async provider requested tools, accepted local tool results, "
        "and then returned the final structured result.",
        details=(
            f"final_result: {final_output['final_result']}",
            f"tool_trace: {tool_trace}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the generic async multi-round tool protocol "
        "works in this environment.",
    )


if __name__ == "__main__":
    run_async(main())


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13 (excerpt, cut after 12 lines):
{
  "final_output": {
    "final_result": 20,
    "steps": [
      {
        "result": 5,
        "tool_name": "add"
      },
      {
        "result": 20,
        "tool_name": "multiply"
      }
    ]
  },
  "tool_trace": [
    {
""".strip()
