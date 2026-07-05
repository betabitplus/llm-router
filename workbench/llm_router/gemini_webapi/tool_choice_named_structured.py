# %%
"""Gemini WebAPI nonstandard forced-tool-choice structured workbench script.

Why:
    Shows that `gemini-webapi` can follow a prompt-driven named-tool choice
    where the model emits an exact textual function call and returns final
    structured JSON after local execution.

Covers:
    Area: gemini-webapi live tool choice
    Behavior: prompt-driven named tool choice, local tool execution,
        final structured output
    Interface: `GeminiClient.generate_content(...)`

Checks:
    If the first live browser-authenticated tool request is restricted to `add`, then
        the named-tool-choice contract is working on the live tool boundary.
    If `tool_trace` preserves the executed arguments and result, then the manual run
        keeps the local execution evidence behind the answer.
    If `final_output` repeats the same `tool_name` and `final_result`, then the final
        structured JSON stayed aligned with the executed tool trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.tool_choice_named_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.tool_choice_named_structured
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console, run_async

from workbench.llm_router.gemini_webapi._opera_cookie_client import managed_client
from workbench.llm_router.gemini_webapi._structured_output import (
    ForcedToolChoiceResult,
    build_named_tool_choice_prompt,
    parse_model_output_json,
)
from workbench.llm_router.gemini_webapi._tool_loop import (
    demo_math_registry,
    execute_tool_call,
    named_tool_final_json_prompt,
    parse_tool_call,
    tool_result_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

_MODEL = "gemini-3.0-flash"
_PROMPT = build_named_tool_choice_prompt()
_FOLLOW_UP_PROMPT = named_tool_final_json_prompt()
_INIT_TIMEOUT_SECONDS = 120.0


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one real Gemini WebAPI prompt-driven named-tool flow."""
    async with managed_client(init_timeout_seconds=_INIT_TIMEOUT_SECONDS) as client:
        first_output = await client.generate_content(_PROMPT, model=_MODEL)
        first_text = first_output.text.strip()
        if first_text.startswith("{"):
            final_output = ForcedToolChoiceResult.model_validate(
                parse_model_output_json(first_text)
            ).model_dump(mode="json")
            return {
                "final_output": final_output,
                "tool_trace": [],
            }

        first_call = execute_tool_call(
            call=parse_tool_call(first_text),
            registry=demo_math_registry(),
        )
        if first_call["tool_name"] != "add":
            msg = (
                f"The live response did not respect the named add choice: {first_call}"
            )
            raise RuntimeError(msg)

        second_prompt = tool_result_prompt(
            tool_name=first_call["tool_name"],
            result=first_call["result"],
            final_instruction=_FOLLOW_UP_PROMPT,
            original_task=_PROMPT,
            prior_steps=[first_call],
        )
        second_output = await client.generate_content(second_prompt, model=_MODEL)
        final_output = ForcedToolChoiceResult.model_validate(
            parse_model_output_json(second_output.text)
        ).model_dump(mode="json")
        return {
            "final_output": final_output,
            "tool_trace": [first_call],
        }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Running one prompt-driven Gemini WebAPI named-tool choice with two "
        "declared local tools and a final structured JSON answer.",
        details=(
            f"Model: {_MODEL}",
            "Forced function: add",
            "Other declared function: multiply",
        ),
    )

    result = run_async(run_pipeline())
    console.demo_step(
        "Observed Tool Choice",
        "The live session respected the named add choice and returned final "
        "structured JSON, either after a local tool step or directly as a "
        "structured named-tool result.",
        details=(
            f"tool_name: {result['final_output']['tool_name']}",
            f"final_result: {result['final_output']['final_result']}",
            f"tool_trace: {result['tool_trace']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "Gemini WebAPI can support a prompt-driven named-tool structured flow "
        "in this environment.",
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
    }
  ]
}
""".strip()
