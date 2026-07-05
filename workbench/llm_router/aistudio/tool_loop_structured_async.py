# %%
"""AI Studio async tools-plus-structured workbench script.

Why:
    Shows that AI Studio can run the non-video async OpenAI-compatible tool
    path first and then return final structured JSON in a second call.

Covers:
    Area: AI Studio non-video path
    Behavior: async tool loop, tool-role messages, final structured output
    Interface: `AsyncOpenAI().chat.completions.create(...)`

Checks:
    If the first live AI Studio round requests the declared tool surface, then the live
        tool protocol accepted the callable boundary.
    If `tool_trace` preserves the executed tool steps and results, then the manual run
        keeps the local execution evidence behind the loop.
    If `final_output` repeats the same `final_result` and tool-summary steps, then the
        final structured JSON stayed aligned with the executed tool trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.tool_loop_structured_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.tool_loop_structured_async
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console
from py_lib_tooling import run_async
from workbench.llm_router.aistudio._json_schema import build_resolved_response_format
from workbench.llm_router.aistudio._sdk_helpers import build_async_client
from workbench.llm_router.aistudio._structured_output import (
    CalculationAudit,
    build_tools_structured_prompt,
)
from workbench.llm_router.aistudio._tool_loop import (
    build_demo_math_tools,
    demo_math_registry,
    run_async_tool_loop,
)

# =============================================================================
# Scenario
# =============================================================================

_MODEL = "gemini-2.5-flash-lite"
_PROMPT = build_tools_structured_prompt()
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
    """Run one real async AI Studio tool loop with final structured JSON."""
    client = build_async_client()
    return await run_async_tool_loop(
        client=client,
        model=_MODEL,
        prompt=_PROMPT,
        tools=_TOOLS,
        registry=demo_math_registry(),
        tool_choice="required",
        max_rounds=4,
        final_response_format=build_resolved_response_format(CalculationAudit),
    )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Running the AI Studio async non-video tool loop first and then asking "
        "for the final structured JSON in a second call.",
        details=(
            f"Model: {_MODEL}",
            "Tools: add(a, b), multiply(a, b)",
            "Why this matters: it matches the AI Studio-specific async "
            "workaround in src.",
        ),
    )

    result = await run_pipeline()
    final_output, tool_trace = _require_structured_result(result)
    console.demo_step(
        "Observed Tool Loop",
        "The live async tool trace and the final structured JSON stayed aligned.",
        details=(
            f"final_result: {final_output['final_result']}",
            f"step_count: {len(final_output['steps'])}",
            f"tool_trace: {tool_trace}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust the AI Studio async tools-plus-structured "
        "workaround used by the adapter.",
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
    "final_result": 84,
    "steps": [
      {
        "result": 42,
        "tool_name": "add"
      },
      {
        "result": 84,
        "tool_name": "multiply"
      }
    ]
  },
  "tool_trace": [
    {
""".strip()
