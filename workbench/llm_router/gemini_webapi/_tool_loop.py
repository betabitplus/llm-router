# %%
"""Gemini WebAPI workbench tool-loop helpers.

Why:
    Keeps the prompt-driven tool-assisted loop in one place so multiple
    Gemini WebAPI scripts can inspect the same nonstandard behavior without
    depending on `src/` internals.

When to use:
    Import from Gemini WebAPI workbench scripts that need to parse exact
    textual function calls or continue a prompt-driven tool conversation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from typing import Any, TypedDict

_CALL_RE = re.compile(r"^(?P<tool_name>\w+)\((?P<args>.*)\)$")


class TextualToolCall(TypedDict):
    """One parsed textual function call from the Gemini WebAPI path."""

    tool_name: str
    arguments: dict[str, Any]


class ToolExecution(TypedDict):
    """One locally executed tool call with JSON-ready evidence."""

    tool_name: str
    arguments: dict[str, Any]
    result: Any


# ======================================================================================
# Textual Tool-Call Parsing
# ======================================================================================


def parse_tool_call(
    text: str,
    *,
    positional_names: tuple[str, ...] = ("a", "b"),
) -> TextualToolCall:
    """Parse one exact textual function call like `add(a=2, b=3)`."""
    match = _CALL_RE.fullmatch(text.strip())
    if match is None:
        msg = f"The live response did not expose the expected function call: {text!r}"
        raise RuntimeError(msg)

    raw_args = match.group("args").strip()
    arguments: dict[str, Any] = {}
    if raw_args:
        positional_index = 0
        for item in raw_args.split(","):
            cleaned = item.strip()
            if "=" in cleaned:
                name, raw_value = cleaned.split("=", 1)
                arguments[name.strip()] = int(raw_value.strip())
                continue

            if positional_index >= len(positional_names):
                msg = (
                    "The live response used more positional arguments than this "
                    f"workbench parser supports: {text!r}"
                )
                raise RuntimeError(msg)
            arguments[positional_names[positional_index]] = int(cleaned)
            positional_index += 1

    return {
        "tool_name": match.group("tool_name"),
        "arguments": arguments,
    }


# ======================================================================================
# Demo Tools
# ======================================================================================


def demo_add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as the shared Gemini WebAPI demo tool payload."""
    return {"result": a + b}


def demo_multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as the shared Gemini WebAPI demo tool payload."""
    return {"result": a * b}


def demo_math_registry() -> dict[str, Callable[..., Any]]:
    """Return the shared local registry for Gemini WebAPI demo tools."""
    return {
        "add": demo_add,
        "multiply": demo_multiply,
    }


# ======================================================================================
# Prompt Builders
# ======================================================================================


def tool_loop_follow_up_prompt() -> str:
    """Build the shared follow-up prompt for the two-step tool loop."""
    return (
        "You are still completing the original two-step plan.\n"
        "If more tools are needed, reply with exactly one function call and "
        "nothing else.\n"
        "Do not stop until both tool steps are complete.\n"
        "If all tools are finished, return ONLY valid JSON with:\n"
        "- steps: a list of tool call summaries with `tool_name` and `result`\n"
        "- final_result\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def tool_loop_final_json_prompt() -> str:
    """Build the shared final JSON-only prompt for the tool loop."""
    return (
        "Return ONLY valid JSON with:\n"
        "- steps: a list of tool call summaries with `tool_name` and `result`\n"
        "- final_result\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def named_tool_final_json_prompt() -> str:
    """Build the shared final JSON-only prompt for named tool choice."""
    return (
        "Return ONLY valid JSON with:\n"
        "- tool_name\n"
        "- final_result\n"
        "- explanation\n\n"
        "Return ONLY valid JSON. No markdown."
    )


# ======================================================================================
# Local Execution
# ======================================================================================


def tool_result_prompt(
    *,
    tool_name: str,
    result: object,
    final_instruction: str,
    original_task: str | None = None,
    prior_steps: list[ToolExecution] | None = None,
) -> str:
    """Build the follow-up prompt carrying one local tool result."""
    payload = result if isinstance(result, dict) else {"result": result}
    parts: list[str] = []
    if original_task:
        parts.append(f"Original task:\n{original_task}")
    if prior_steps:
        parts.append(
            "Completed tool steps so far:\n"
            + json.dumps(prior_steps, indent=2, sort_keys=True)
        )
    parts.append(
        f"Tool {tool_name} returned {json.dumps(payload, sort_keys=True)}.\n\n"
        f"{final_instruction}"
    )
    return "\n\n".join(parts)


def execute_tool_call(
    *,
    call: TextualToolCall,
    registry: Mapping[str, Callable[..., Any]],
) -> ToolExecution:
    """Execute one parsed tool call from the local registry."""
    tool_name = str(call["tool_name"])
    arguments = dict(call["arguments"])
    result = registry[tool_name](**arguments)
    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
    }
