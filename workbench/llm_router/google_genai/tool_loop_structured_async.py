# %%
"""Google GenAI async tool-calling workbench script.

Why:
    Shows that the native Google async client can run a callable-based tool
    loop and then produce a final structured JSON answer.

Covers:
    Area: google-genai live async tool calling
    Behavior: callable declaration, async function response, final structured output
    Interface: `Client.aio.models.generate_content(...)`, `FunctionResponse`

Checks:
    If the live async model requests the declared tool surface, then the live tool
        protocol accepted the callable boundary.
    If `tool_trace` preserves the executed tool steps and results, then the manual run
        keeps the local execution evidence behind the loop.
    If `final_output` repeats the same `final_result` and tool-summary steps, then the
        final structured JSON stayed aligned with the executed tool trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.tool_loop_structured_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.tool_loop_structured_async
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console
from py_lib_tooling import run_async
from workbench.llm_router.google_genai._sdk_helpers import build_client
from workbench.llm_router.google_genai._structured_output import (
    CalculationAudit,
    build_tool_audit_prompt,
)
from workbench.llm_router.google_genai._tool_loop import run_async_tool_loop

# =============================================================================
# Scenario
# =============================================================================

# Keep the lightweight flash-lite model fixed so the async tool loop stays fast
# and the async tool protocol itself is the main thing under inspection.
_MODEL = "gemini-2.5-flash-lite"
_PROMPT = build_tool_audit_prompt()


# =============================================================================
# Helpers
# =============================================================================


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as JSON."""
    return {"result": a * b}


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one real native Google async tool loop with a final schema step."""
    # Build the native client once, then let the shared helper execute the full
    # async function-call/function-response loop.
    client = build_client()
    # The helper returns only the final structured result and tool trace this
    # manual script needs to expose.
    return await run_async_tool_loop(
        client=client,
        model=_MODEL,
        prompt=_PROMPT,
        tool_functions=[multiply],
        response_schema=CalculationAudit,
        tool_choice="required",
        max_rounds=4,
    )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Running one native Google async tool loop with a callable "
        "declaration and a final structured JSON response.",
        details=(
            f"Model: {_MODEL}",
            "Callable tool: multiply(a, b)",
            "Tool choice: required",
        ),
    )

    result = run_async(run_pipeline())
    final_output = result["final_output"]
    console.demo_step(
        "Observed Async Tool Loop",
        "The live Google async model requested the tool, consumed the function "
        "response, and then returned the final structured result.",
        details=(
            f"final_result: {final_output['final_result']}",
            f"tool_trace: {result['tool_trace']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the native async callable tool protocol "
        "works end to end in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, cut after 12 lines):
{
  "final_output": {
    "final_result": 323,
    "tool_calls": [
      {
        "result": 323,
        "tool_name": "multiply"
      }
    ]
  },
  "tool_trace": [
    {
""".strip()
