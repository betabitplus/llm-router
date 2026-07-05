# %%
"""QwenChat async nonstandard structured tool-loop workbench script.

Why:
    Shows the direct QwenChat proxy seam behind the current adapter limit:
    when given `tools`, the model can emit a textual function invocation that
    a caller can parse, execute locally, and complete with a structured
    follow-up through the async HTTP path.

Covers:
    Area: qwenchat direct async tool-assisted flow
    Behavior: tools payload, textual function invocation, local tool follow-up
    Interface: `POST /chat/completions`

Checks:
    If the direct async proxy emits textual `add(...)` in `tool_call_text`, then the
        nonstandard tool-request seam produced a parseable tool call.
    If `tool_arguments` and `tool_result` preserve the locally executed call, then the
        manual run keeps the exact evidence fed into the follow-up request.
    If `final_output` repeats the same `final_result` and step summary, then the
        structured follow-up stayed aligned with the executed tool call.
    If the result also exposes both `initial_usage` and `final_usage`, then the manual
        run shows token accounting for both phases of the two-step flow.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.qwenchat.tool_loop_structured_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.qwenchat.tool_loop_structured_async
"""

from __future__ import annotations

import json
from typing import Any

from py_lib_tooling import console, run_async

from workbench.llm_router.qwenchat._runtime import build_async_client, qwenchat_base_url
from workbench.llm_router.qwenchat._structured_output import (
    CalculationAudit,
)
from workbench.llm_router.qwenchat._tool_loop import (
    QwenToolMessage,
    ToolExecution,
    demo_math_registry,
    run_async_textual_tool_flow,
)

# =============================================================================
# Scenario
# =============================================================================

_MODEL = "qwen-max-latest"
_SYSTEM_PROMPT = (
    "You may call the provided tool by replying with exactly one function call "
    "and nothing else."
)
_INITIAL_PROMPT = "Use add with a=20 and b=22. Reply with only the function call."
_FOLLOW_UP_INSTRUCTION = (
    "Tool add returned {tool_result}. "
    "Return JSON with:\n"
    "- steps: a list with one object containing `tool_name` and `result`\n"
    "- final_result\n\n"
    "Return ONLY valid JSON. No markdown."
)
_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two integers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        },
    }
]


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one real direct async QwenChat tool-assisted flow."""

    def build_follow_up(tool_execution: ToolExecution) -> str:
        """Build the follow-up message from one local tool result."""
        return _FOLLOW_UP_INSTRUCTION.format(
            tool_result=json.dumps(tool_execution["result"], sort_keys=True)
        )

    initial_messages: list[QwenToolMessage] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _INITIAL_PROMPT},
    ]
    async with build_async_client() as client:
        result = await run_async_textual_tool_flow(
            client=client,
            model=_MODEL,
            initial_messages=initial_messages,
            tools=_TOOLS,
            follow_up_content_builder=build_follow_up,
            schema_model=CalculationAudit,
            registry=demo_math_registry(),
        )

    return {
        "base_url": qwenchat_base_url(),
        "model": _MODEL,
        "tool_call_text": result["call_text"],
        "tool_arguments": result["tool_execution"]["arguments"],
        "tool_result": result["tool_execution"]["result"],
        "final_output": result["final_output"],
        "initial_usage": result["initial_usage"],
        "final_usage": result["final_usage"],
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Declaring one tool directly to the QwenChat proxy, letting the model "
        "emit a textual function call, then completing the loop with an async "
        "follow-up request that asks for final structured JSON.",
        details=(
            f"Base URL: {qwenchat_base_url()}",
            f"Model: {_MODEL}",
            "Declared tool: add(a, b)",
        ),
    )

    result = await run_pipeline()
    final_output = result["final_output"]
    console.demo_step(
        "Observed Tool-Assisted Flow",
        "The live async proxy first emitted a textual add(...) call, and the "
        "follow-up request returned final structured JSON after local execution.",
        details=(
            f"tool_call_text: {result['tool_call_text']}",
            f"tool_result: {result['tool_result']}",
            f"final_result: {final_output['final_result']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the direct async QwenChat proxy supports a "
        "nonstandard structured tool-assisted flow in this environment.",
    )


if __name__ == "__main__":
    run_async(main())


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13:
{
  "base_url": "http://localhost:3264/api",
  "final_output": {
    "final_result": 42,
    "steps": [
      {
        "result": 42,
        "tool_name": "add"
      }
    ]
  },
  "final_usage": {
    "input_tokens": 230,
    "output_tokens": 42,
    "total_tokens": 272
  },
  "initial_usage": {
    "input_tokens": 627,
    "output_tokens": 11,
    "total_tokens": 638
  },
  "model": "qwen-max-latest",
  "tool_arguments": {
    "a": 20,
    "b": 22
  },
  "tool_call_text": "add(a=20, b=22)",
  "tool_result": {
    "result": 42
  }
}
""".strip()
