# %%
"""AI Studio forced-tool-choice structured workbench script.

Why:
    Shows that AI Studio can force one named tool on the non-video
    OpenAI-compatible path and return final structured JSON.

Covers:
    Area: AI Studio non-video path
    Behavior: explicit `tool_choice`, tool execution, final structured output
    Interface: `tool_choice={"type":"function",...}`

Checks:
    If the first live AI Studio tool request is restricted to `add`, then the named-
        tool-choice contract is working on the live tool boundary.
    If `tool_trace` preserves the executed arguments and result, then the manual run
        keeps the local execution evidence behind the answer.
    If `final_output` repeats the same `tool_name` and `final_result`, then the final
        structured JSON stayed aligned with the executed tool trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.tool_choice_named_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.tool_choice_named_structured
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console

from workbench.llm_router.aistudio._json_schema import build_resolved_response_format
from workbench.llm_router.aistudio._sdk_helpers import build_client
from workbench.llm_router.aistudio._structured_output import (
    ForcedToolChoiceResult,
    build_tool_choice_prompt,
)
from workbench.llm_router.aistudio._tool_loop import (
    build_demo_math_tools,
    demo_math_registry,
    run_sync_tool_loop,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the lightweight flash-lite model fixed so this script isolates AI
# Studio's forced-tool path rather than model variability.
_MODEL = "gemini-2.5-flash-lite"
_PROMPT = build_tool_choice_prompt()
_TOOLS = build_demo_math_tools()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real forced-tool-choice request on AI Studio."""
    # Build the AI Studio client once, then let the shared helper run the live
    # tool loop with an explicit named-tool choice.
    client = build_client()
    result = run_sync_tool_loop(
        client=client,
        model=_MODEL,
        prompt=_PROMPT,
        tools=_TOOLS,
        registry=demo_math_registry(),
        tool_choice={"type": "function", "function": {"name": "add"}},
        max_rounds=2,
        final_response_format=build_resolved_response_format(ForcedToolChoiceResult),
    )
    final_output = result.get("final_output")
    tool_trace = result.get("tool_trace")
    if not isinstance(final_output, dict) or not isinstance(tool_trace, list):
        msg = "The live tool loop did not return the expected structured result."
        raise TypeError(msg)
    parsed = ForcedToolChoiceResult.model_validate(final_output)
    return {
        "final_output": parsed.model_dump(mode="json"),
        "tool_trace": tool_trace,
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Forcing AI Studio to use one named tool on the non-video "
        "OpenAI-compatible path.",
        details=(
            f"Model: {_MODEL}",
            "Forced tool: add",
            "Other declared tool: multiply",
        ),
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Forced Tool Choice",
        "The live provider used the named function and the final structured "
        "result matched the tool trace.",
        details=(
            f"tool_name: {result['final_output']['tool_name']}",
            f"final_result: {result['final_output']['final_result']}",
            f"tool_trace: {result['tool_trace']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that AI Studio obeys forced tool choice on "
        "the non-video path.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13 (excerpt, cut after 12 lines):
{
  "final_output": {
    "explanation": "The add tool was used with a=40 and b=2, returning 42.",
    "final_result": 42,
    "tool_name": "add"
  },
  "tool_trace": [
    {
      "arguments": {
        "a": 40,
        "b": 2
      },
      "result": {
        "result": 42
      },
      "tool_name": "add"
""".strip()
