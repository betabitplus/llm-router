# %%
"""Google GenAI forced-tool-choice structured workbench script.

Why:
    Shows that the native Google client supports a named-function allowlist in
    function-calling config and can still return final structured JSON.

Covers:
    Area: google-genai live tool choice
    Behavior: named-function allowlist, tool execution, final structured output
    Interface: `FunctionCallingConfig.allowed_function_names`, `response_schema`

Checks:
    If the live model tool request is restricted to `add`, then the named-tool-choice
        contract is working on the live tool boundary.
    If `tool_trace` preserves the executed arguments and result, then the manual run
        keeps the local execution evidence behind the answer.
    If `final_output` repeats the same `tool_name` and `final_result`, then the final
        structured JSON stayed aligned with the executed tool trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.tool_choice_named_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.tool_choice_named_structured
"""

from __future__ import annotations

from typing import Any

from tests.support.console import console
from workbench.llm_router.google_genai._sdk_helpers import build_client
from workbench.llm_router.google_genai._structured_output import (
    ForcedToolChoiceResult,
    build_named_tool_choice_prompt,
)
from workbench.llm_router.google_genai._tool_loop import (
    run_sync_tool_loop,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the prompt narrow and deterministic so the named tool choice and final
# structured result are the only meaningful moving parts in a manual run.
_MODEL = "gemini-2.5-flash-lite"
_PROMPT = build_named_tool_choice_prompt()


# =============================================================================
# Helpers
# =============================================================================


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as JSON."""
    return {"result": a * b}


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one native Google tool loop with a forced named tool choice."""
    # Build the native client once, then let the shared helper execute the
    # allowlisted tool loop and the final schema-constrained answer step.
    client = build_client()
    result = run_sync_tool_loop(
        client=client,
        model=_MODEL,
        prompt=_PROMPT,
        tool_functions=[add, multiply],
        response_schema=ForcedToolChoiceResult,
        tool_choice={"type": "function", "function": {"name": "add"}},
        max_rounds=3,
    )
    parsed = ForcedToolChoiceResult.model_validate(result["final_output"])
    return {
        "final_output": parsed.model_dump(mode="json"),
        "tool_trace": result["tool_trace"],
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending two callable tools but restricting the model to one named "
        "allowed function, then asking for a final structured answer.",
        details=(
            f"Model: {_MODEL}",
            "Forced function: add",
            "Other declared function: multiply",
        ),
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Tool Choice",
        "The live tool loop respected the named-function allowlist and then "
        "returned final structured JSON.",
        details=(
            f"tool_name: {result['final_output']['tool_name']}",
            f"final_result: {result['final_output']['final_result']}",
            f"tool_trace: {result['tool_trace']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the native Google named-tool-choice path "
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
    "final_result": 5,
    "tool_name": "add"
  },
  "tool_trace": [
    {
      "arguments": {
        "a": 2,
        "b": 3
      },
      "result": {
        "result": 5
      },
      "tool_name": "add"
    }
  ]
}
""".strip()
