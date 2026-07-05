# %%
"""OpenAI-compatible named-tool-choice workbench script.

Why:
    Shows that the `openai` SDK can force one named function through
    `tool_choice` and still return final structured JSON.

Covers:
    Area: openai-compatible live tool choice
    Behavior: named-function tool choice, final structured output
    Interface: `tool_choice={"type":"function",...}`

Checks:
    If the first live tool request is restricted to `add`, then the named-tool-choice
        contract is working on the live tool boundary.
    If `tool_trace` preserves the executed arguments and result, then the manual run
        keeps the local execution evidence behind the answer.
    If `final_output` repeats the same `tool_name` and `final_result`, then the final
        structured JSON stayed aligned with the executed tool trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.openai.tool_choice_named_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.openai.tool_choice_named_structured
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console

from workbench.llm_router.openai._sdk_helpers import build_client, provider_api_key_env
from workbench.llm_router.openai._structured_output import (
    FORCED_TOOL_RESPONSE_FORMAT,
)
from workbench.llm_router.openai._tool_loop import (
    build_demo_math_tools,
    demo_math_registry,
    run_sync_tool_loop,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep NVIDIA's OpenAI-compatible endpoint fixed because it is the cleanest
# live path here for forced named-tool choice plus final structured output.
_BASE_URL = "https://integrate.api.nvidia.com/v1"
_API_KEY_ENV = provider_api_key_env("NVIDIA")
_MODEL = "meta/llama-4-maverick-17b-128e-instruct"
# Keep the prompt narrow so the first tool choice is the main thing a manual
# reader needs to confirm.
_PROMPT = (
    "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
    "Use ONLY add with a=40 and b=2, then return JSON with:\n"
    "- tool_name\n"
    "- final_result\n"
    "- explanation\n\n"
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


def run_pipeline() -> dict[str, Any]:
    """Run one real forced-tool-choice loop with final structured JSON."""
    # Build the client exactly as the generic OpenAI-compatible suite does for
    # live provider calls.
    client = build_client(api_key_env=_API_KEY_ENV, base_url=_BASE_URL)
    try:
        # Let the shared helper run the forced-tool loop, then keep the
        # validated structured result for the manual walkthrough.
        return run_sync_tool_loop(
            client=client,
            model=_MODEL,
            prompt=_PROMPT,
            tools=_TOOLS,
            registry=demo_math_registry(),
            tool_choice={"type": "function", "function": {"name": "add"}},
            max_rounds=2,
            final_response_format=FORCED_TOOL_RESPONSE_FORMAT,
        )
    finally:
        client.close()


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending two tools but forcing the OpenAI-compatible provider to use one "
        "named function before the final JSON answer.",
        details=(
            f"Base URL: {_BASE_URL}",
            f"Model: {_MODEL}",
            "Forced tool: add",
            "Other declared tool: multiply",
        ),
    )

    result = run_pipeline()
    final_output, tool_trace = _require_structured_result(result)
    console.demo_step(
        "Observed Named Tool Choice",
        "The live provider used the named function and the final JSON answer "
        "agreed with the tool trace.",
        details=(
            f"tool_name: {final_output['tool_name']}",
            f"final_result: {final_output['final_result']}",
            f"tool_trace: {tool_trace}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that named-function tool choice works in this "
        "environment.",
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
    "explanation": "Used add function with a=40 and b=2",
    "final_result": 42,
    "tool_name": "add"
  },
  "tool_trace": [
    {
      "arguments": {
        "a": 40,
        "b": 2
      },
""".strip()
