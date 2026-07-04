# %%
"""Gemini WebAPI async nonstandard structured tool-loop workbench script.

Why:
    Shows that `gemini-webapi` can run one explicitly async prompt-driven tool
    loop where the model emits exact textual function calls and returns final
    structured JSON after local tool execution.

Covers:
    Area: gemini-webapi live async tool-assisted flow
    Behavior: textual function invocation, local tool execution, final structured output
    Interface: `GeminiClient.generate_content(...)`

Checks:
    If the live async session requests the declared tool surface, then the live tool
        protocol accepted the callable boundary.
    If `tool_trace` preserves the executed tool steps and results, then the manual run
        keeps the local execution evidence behind the loop.
    If `final_output` repeats the same `final_result` and tool-summary steps, then the
        final structured JSON stayed aligned with the executed tool trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.tool_loop_structured_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.tool_loop_structured_async
"""

from __future__ import annotations

from typing import Any

from tests.support.console import console
from tests.support.setup import run_async
from workbench.llm_router.gemini_webapi._opera_cookie_client import managed_client
from workbench.llm_router.gemini_webapi._structured_output import (
    CalculationAudit,
    build_tool_loop_prompt,
    parse_model_output_json,
)
from workbench.llm_router.gemini_webapi._tool_loop import (
    demo_math_registry,
    execute_tool_call,
    parse_tool_call,
    tool_loop_final_json_prompt,
    tool_loop_follow_up_prompt,
    tool_result_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

_MODEL = "gemini-3.0-flash"
_PROMPT = build_tool_loop_prompt()
_FOLLOW_UP_PROMPT = tool_loop_follow_up_prompt()
_INIT_TIMEOUT_SECONDS = 120.0


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one real async Gemini WebAPI prompt-driven tool loop."""
    async with managed_client(init_timeout_seconds=_INIT_TIMEOUT_SECONDS) as client:
        first_output = await client.generate_content(_PROMPT, model=_MODEL)
        first_call = execute_tool_call(
            call=parse_tool_call(first_output.text),
            registry=demo_math_registry(),
        )

        second_prompt = tool_result_prompt(
            tool_name=first_call["tool_name"],
            result=first_call["result"],
            final_instruction=_FOLLOW_UP_PROMPT,
            original_task=_PROMPT,
            prior_steps=[first_call],
        )
        second_output = await client.generate_content(second_prompt, model=_MODEL)
        second_text = second_output.text.strip()

        trace = [first_call]
        if second_text.startswith("{"):
            final_output = CalculationAudit.model_validate(
                parse_model_output_json(second_text)
            ).model_dump(mode="json")
            return {
                "final_output": final_output,
                "tool_trace": trace,
            }

        second_call = execute_tool_call(
            call=parse_tool_call(second_text),
            registry=demo_math_registry(),
        )
        trace.append(second_call)
        third_prompt = tool_result_prompt(
            tool_name=second_call["tool_name"],
            result=second_call["result"],
            final_instruction=tool_loop_final_json_prompt(),
            original_task=_PROMPT,
            prior_steps=trace,
        )
        third_output = await client.generate_content(third_prompt, model=_MODEL)
        final_output = CalculationAudit.model_validate(
            parse_model_output_json(third_output.text)
        ).model_dump(mode="json")
        return {
            "final_output": final_output,
            "tool_trace": trace,
        }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Running one explicit async Gemini WebAPI tool loop with two declared "
        "local tools and a final structured JSON answer.",
        details=(
            f"Model: {_MODEL}",
            "Declared tools: add(a, b), multiply(a, b)",
        ),
    )

    result = run_async(run_pipeline())
    final_output = result["final_output"]
    console.demo_step(
        "Observed Tool Loop",
        "The live async session emitted textual function calls, accepted local "
        "tool results, and then returned final structured JSON.",
        details=(
            f"final_result: {final_output['final_result']}",
            f"tool_trace: {result['tool_trace']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "Gemini WebAPI can support an explicit async prompt-driven structured "
        "tool loop in this environment.",
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
""".strip()
