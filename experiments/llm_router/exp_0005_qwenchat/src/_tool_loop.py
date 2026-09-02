# %%
"""QwenChat experiment tool-loop helpers.

Why:
    QwenChat has exposed both textual function calls and native OpenAI-style
    `tool_calls` on this local proxy path. These helpers normalize either form
    so the tool scripts stay small and comparable.

When to use:
    Import from QwenChat experiment scripts that need prompt-driven tool choice
    or a two-step tool-assisted flow.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from typing import Any, Literal, TypedDict

import httpx
from _chat_completions import (
    post_completion_async,
    post_completion_sync,
    response_text,
    usage_snapshot,
)
from _structured_output import validate_json_text
from pydantic import BaseModel

_TOOL_CALL_RE = re.compile(r"^(?P<tool_name>\w+)\((?P<args>.*)\)$")


class QwenToolMessage(TypedDict):
    """One direct message in the prompt-driven QwenChat tool flow."""

    role: Literal["system", "user", "assistant"]
    content: str


class TextualToolCall(TypedDict):
    """One parsed textual tool call from a QwenChat assistant reply."""

    tool_name: str
    arguments: dict[str, int]


class ToolExecution(TypedDict):
    """One locally executed tool call with JSON-ready evidence."""

    tool_name: str
    arguments: dict[str, int]
    result: Any


class TextualToolFlowResult(TypedDict):
    """JSON-ready evidence returned by the textual tool-flow helpers."""

    call_text: str
    tool_execution: ToolExecution
    final_output: dict[str, Any]
    initial_usage: dict[str, int] | None
    final_usage: dict[str, int] | None


# ======================================================================================
# Demo Tools
# ======================================================================================


def demo_add(*, a: int, b: int) -> int:
    """Return a+b as the shared QwenChat demo tool result."""
    return a + b


def demo_multiply(*, a: int, b: int) -> int:
    """Return a*b as the shared QwenChat demo tool result."""
    return a * b


def demo_math_registry() -> dict[str, Callable[..., Any]]:
    """Return the shared local registry for the QwenChat demo tools."""
    return {
        "add": demo_add,
        "multiply": demo_multiply,
    }


def build_tool_payload(
    *,
    model: str,
    messages: list[QwenToolMessage],
    tools: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Build one direct QwenChat completion payload for tool demos."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": 0.0,
        "seed": 42,
    }
    if tools:
        payload["tools"] = tools
    return payload


# ======================================================================================
# Textual Tool-Call Parsing
# ======================================================================================


def parse_tool_call(text: str) -> TextualToolCall:
    """Parse one textual tool call like `add(a=1, b=2)` or `add(1, 2)`."""
    match = _TOOL_CALL_RE.fullmatch(text.strip())
    if match is None:
        msg = f"The live response did not expose the expected tool call: {text!r}"
        raise RuntimeError(msg)

    raw_args = match.group("args").strip()
    arguments: dict[str, int] = {}
    if raw_args:
        positional_names = ("a", "b")
        positional_index = 0
        for item in raw_args.split(","):
            cleaned = item.strip()
            if "=" in cleaned:
                name, raw_value = cleaned.split("=", 1)
                arguments[name.strip()] = int(raw_value.strip())
                continue
            if positional_index >= len(positional_names):
                msg = f"The live response used unsupported positional args: {text!r}"
                raise RuntimeError(msg)
            arguments[positional_names[positional_index]] = int(cleaned)
            positional_index += 1

    return {
        "tool_name": match.group("tool_name"),
        "arguments": arguments,
    }


def response_tool_call(response: dict[str, Any]) -> tuple[str, TextualToolCall]:
    """Normalize one native or textual QwenChat tool call."""
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message")
        if isinstance(message, dict):
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                tool_call = tool_calls[0]
                if isinstance(tool_call, dict):
                    function = tool_call.get("function")
                    if isinstance(function, dict):
                        tool_name = function.get("name")
                        raw_arguments = function.get("arguments")
                        if isinstance(raw_arguments, str):
                            raw_arguments = json.loads(raw_arguments)
                        if isinstance(tool_name, str) and isinstance(
                            raw_arguments, dict
                        ):
                            arguments = {
                                str(name): int(value)
                                for name, value in raw_arguments.items()
                            }
                            call_text = (
                                f"{tool_name}("
                                + ", ".join(
                                    f"{name}={value}"
                                    for name, value in arguments.items()
                                )
                                + ")"
                            )
                            return call_text, {
                                "tool_name": tool_name,
                                "arguments": arguments,
                            }

    call_text = response_text(response)
    return call_text, parse_tool_call(call_text)


# ======================================================================================
# Local Execution Helpers
# ======================================================================================


def execute_tool_call(
    *,
    call: TextualToolCall,
    registry: Mapping[str, Callable[..., Any]],
) -> ToolExecution:
    """Execute one parsed textual tool call from the local registry."""
    tool_name = str(call["tool_name"])
    arguments = dict(call["arguments"])
    result = registry[tool_name](**arguments)
    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
    }


def _follow_up_messages(
    *,
    initial_messages: list[QwenToolMessage],
    call_text: str,
    follow_up_content: str,
) -> list[QwenToolMessage]:
    """Append the assistant tool call and follow-up user instruction."""
    return [
        *initial_messages,
        {"role": "assistant", "content": call_text},
        {"role": "user", "content": follow_up_content},
    ]


# ======================================================================================
# Sync Runner
# ======================================================================================


def run_sync_textual_tool_flow(  # noqa: PLR0913
    *,
    client: httpx.Client,
    model: str,
    initial_messages: list[QwenToolMessage],
    tools: list[dict[str, Any]],
    follow_up_content_builder: Callable[[ToolExecution], str],
    schema_model: type[BaseModel],
    registry: Mapping[str, Callable[..., Any]],
) -> TextualToolFlowResult:
    """Run one sync textual tool-assisted flow and return JSON-ready evidence."""
    # 1. Ask the model for one tool call and normalize native/textual forms.
    initial_response = post_completion_sync(
        client=client,
        payload=build_tool_payload(
            model=model,
            messages=initial_messages,
            tools=tools,
        ),
    )
    call_text, tool_call = response_tool_call(initial_response)
    tool_execution = execute_tool_call(
        call=tool_call,
        registry=registry,
    )
    follow_up_content = follow_up_content_builder(tool_execution)
    follow_up_messages = _follow_up_messages(
        initial_messages=initial_messages,
        call_text=call_text,
        follow_up_content=follow_up_content,
    )
    # 2. Feed the tool result back into the conversation and validate the
    # final JSON response against the declared schema.
    final_response = post_completion_sync(
        client=client,
        payload=build_tool_payload(
            model=model,
            messages=follow_up_messages,
            tools=None,
        ),
    )
    final_output = validate_json_text(
        response_text(final_response),
        schema_model,
    ).model_dump(mode="json")
    return {
        "call_text": call_text,
        "tool_execution": tool_execution,
        "final_output": final_output,
        "initial_usage": usage_snapshot(initial_response),
        "final_usage": usage_snapshot(final_response),
    }


# ======================================================================================
# Async Runner
# ======================================================================================


async def run_async_textual_tool_flow(  # noqa: PLR0913
    *,
    client: httpx.AsyncClient,
    model: str,
    initial_messages: list[QwenToolMessage],
    tools: list[dict[str, Any]],
    follow_up_content_builder: Callable[[ToolExecution], str],
    schema_model: type[BaseModel],
    registry: Mapping[str, Callable[..., Any]],
) -> TextualToolFlowResult:
    """Run one async textual tool-assisted flow and return JSON-ready evidence."""
    # 1. Ask the model for one tool call and normalize native/textual forms.
    initial_response = await post_completion_async(
        client=client,
        payload=build_tool_payload(
            model=model,
            messages=initial_messages,
            tools=tools,
        ),
    )
    call_text, tool_call = response_tool_call(initial_response)
    tool_execution = execute_tool_call(
        call=tool_call,
        registry=registry,
    )
    follow_up_content = follow_up_content_builder(tool_execution)
    follow_up_messages = _follow_up_messages(
        initial_messages=initial_messages,
        call_text=call_text,
        follow_up_content=follow_up_content,
    )
    # 2. Feed the tool result back into the conversation and validate the
    # final JSON response against the declared schema.
    final_response = await post_completion_async(
        client=client,
        payload=build_tool_payload(
            model=model,
            messages=follow_up_messages,
            tools=None,
        ),
    )
    final_output = validate_json_text(
        response_text(final_response),
        schema_model,
    ).model_dump(mode="json")
    return {
        "call_text": call_text,
        "tool_execution": tool_execution,
        "final_output": final_output,
        "initial_usage": usage_snapshot(initial_response),
        "final_usage": usage_snapshot(final_response),
    }
