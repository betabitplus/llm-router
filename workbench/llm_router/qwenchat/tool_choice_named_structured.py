# %%
"""QwenChat nonstandard forced-tool-choice structured workbench script.

Why:
    Shows that the direct QwenChat proxy can follow a prompt-driven named-tool
    choice, emit a textual function call, and return final structured JSON
    after local execution.

Covers:
    Area: qwenchat direct tool choice
    Behavior: prompt-driven named tool choice, textual function invocation,
        final structured output
    Interface: `POST /chat/completions`

Checks:
    If the direct proxy emits textual `add(...)` in `tool_call_text`, then the prompt-
        driven named-tool steering worked on the nonstandard tool seam.
    If `tool_trace` preserves the executed arguments and result, then the manual run
        keeps the local execution evidence behind the answer.
    If `final_output` repeats the same `tool_name` and `final_result`, then the final
        structured JSON stayed aligned with the emitted tool call.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.qwenchat.tool_choice_named_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.qwenchat.tool_choice_named_structured
"""

from __future__ import annotations

import json
from typing import Any

from py_lib_tooling import console

from workbench.llm_router.qwenchat._runtime import build_sync_client, qwenchat_base_url
from workbench.llm_router.qwenchat._structured_output import (
    ForcedToolChoiceResult,
)
from workbench.llm_router.qwenchat._tool_loop import (
    QwenToolMessage,
    ToolExecution,
    demo_math_registry,
    run_sync_textual_tool_flow,
)

# =============================================================================
# Scenario
# =============================================================================

_MODEL = "qwen-max-latest"
_SYSTEM_PROMPT = (
    "You may call the provided tool by replying with exactly one function call "
    "and nothing else."
)
_INITIAL_PROMPT = (
    "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
    "Use ONLY add with a=40 and b=2.\n"
    "Reply with only the function call."
)
_FOLLOW_UP_INSTRUCTION = (
    "Tool add returned {tool_result}. "
    "Return JSON with:\n"
    "- tool_name\n"
    "- final_result\n"
    "- explanation\n\n"
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
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two integers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        },
    },
]


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real direct QwenChat named-tool-choice flow."""

    def build_follow_up(tool_execution: ToolExecution) -> str:
        """Build the follow-up message from one local tool result."""
        return _FOLLOW_UP_INSTRUCTION.format(
            tool_result=json.dumps(tool_execution["result"], sort_keys=True)
        )

    initial_messages: list[QwenToolMessage] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _INITIAL_PROMPT},
    ]
    with build_sync_client() as client:
        result = run_sync_textual_tool_flow(
            client=client,
            model=_MODEL,
            initial_messages=initial_messages,
            tools=_TOOLS,
            follow_up_content_builder=build_follow_up,
            schema_model=ForcedToolChoiceResult,
            registry=demo_math_registry(),
        )

    return {
        "base_url": qwenchat_base_url(),
        "final_output": result["final_output"],
        "tool_call_text": result["call_text"],
        "tool_trace": [
            {
                "tool_name": result["tool_execution"]["tool_name"],
                "arguments": result["tool_execution"]["arguments"],
                "result": result["tool_execution"]["result"],
            }
        ],
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Declaring two tools to the QwenChat proxy but steering the model to "
        "one named add call before the final structured answer.",
        details=(
            f"Base URL: {qwenchat_base_url()}",
            f"Model: {_MODEL}",
            "Forced function: add",
            "Other declared function: multiply",
        ),
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Tool Choice",
        "The live proxy emitted the named add call and then returned final "
        "structured JSON.",
        details=(
            f"tool_name: {result['final_output']['tool_name']}",
            f"final_result: {result['final_output']['final_result']}",
            f"tool_trace: {result['tool_trace']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the direct QwenChat proxy supports a "
        "nonstandard named-tool structured flow in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13 (excerpt, cut after 12 lines):
{
  "base_url": "http://localhost:3264/api",
  "final_output": {
    "explanation": "The tool 'add' was used and the final result ...",
    "final_result": 42,
    "tool_name": "add"
  },
  "tool_call_text": "add(40, 2)",
  "tool_trace": [
    {
      "arguments": {
        "a": 40,
        "b": 2
      },
      "result": {
""".strip()
