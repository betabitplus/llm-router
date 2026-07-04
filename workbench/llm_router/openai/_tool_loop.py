"""OpenAI-compatible workbench tool-loop helpers.

Why:
    Keeps the multi-round tool protocol in one place so the workbench scripts
    can inspect real tool behavior without depending on `src/` internals.

When to use:
    Import from OpenAI-compatible workbench scripts that need tool definition
    helpers, tool-call extraction, or one real tool round-trip.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from workbench.llm_router.openai._sdk_helpers import parse_message_json, response_text

if TYPE_CHECKING:
    from openai import AsyncOpenAI, OpenAI
    from openai.types.chat import ChatCompletion


class FunctionToolCall(TypedDict):
    """One parsed function call emitted by the OpenAI-compatible response."""

    id: str | None
    tool_name: str
    arguments: dict[str, Any]


class ToolTraceEntry(TypedDict):
    """One locally executed tool step recorded for workbench output."""

    tool_name: str
    arguments: dict[str, Any]
    result: object


class AssistantMessagePayload(TypedDict, total=False):
    """One assistant message payload reused in follow-up tool rounds."""

    role: Literal["assistant"]
    content: str
    tool_calls: list[dict[str, Any]]


class ToolMessagePayload(TypedDict, total=False):
    """One tool-role message payload appended after local execution."""

    role: Literal["tool"]
    content: str
    tool_call_id: str


class ToolLoopResult(TypedDict, total=False):
    """JSON-ready evidence returned by the OpenAI-compatible tool loop."""

    final_text: str
    final_output: dict[str, Any]
    tool_trace: list[ToolTraceEntry]


# ======================================================================================
# Shared Tool Declarations
# ======================================================================================


def build_function_tool(
    *,
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Build one OpenAI-compatible function tool declaration."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def demo_add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as the shared workbench demo tool payload."""
    return {"result": a + b}


def demo_multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as the shared workbench demo tool payload."""
    return {"result": a * b}


def build_demo_math_tools() -> list[dict[str, Any]]:
    """Build the shared add/multiply demo tools used by OpenAI scripts."""
    return [
        build_function_tool(
            name="add",
            description="Add two integers",
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        ),
        build_function_tool(
            name="multiply",
            description="Multiply two integers",
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        ),
    ]


def demo_math_registry() -> dict[str, Callable[..., Any]]:
    """Return the shared local registry for the demo math tools."""
    return {
        "add": demo_add,
        "multiply": demo_multiply,
    }


# ======================================================================================
# Response Parsing Helpers
# ======================================================================================


def extract_tool_calls(response: ChatCompletion) -> list[FunctionToolCall]:
    """Extract tool-call evidence from one assistant response."""
    tool_calls = response.choices[0].message.tool_calls or []
    extracted: list[FunctionToolCall] = []
    for tool_call in tool_calls:
        raw_args = tool_call.function.arguments
        extracted.append(
            {
                "id": tool_call.id,
                "tool_name": tool_call.function.name,
                "arguments": json.loads(raw_args) if raw_args else {},
            }
        )
    return extracted


def assistant_message_dict(response: ChatCompletion) -> AssistantMessagePayload:
    """Convert a response message into a follow-up chat message payload."""
    message = response.choices[0].message
    payload: AssistantMessagePayload = {
        "role": "assistant",
        "content": message.content or "",
    }

    raw_calls = message.tool_calls or []
    if raw_calls:
        payload["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in raw_calls
        ]

    return payload


def tool_message_dict(
    *,
    tool_call_id: str | None,
    result: object,
) -> ToolMessagePayload:
    """Build one tool-role message for a local tool result."""
    payload: ToolMessagePayload = {
        "role": "tool",
        "content": json.dumps(result, sort_keys=True),
    }
    if tool_call_id:
        payload["tool_call_id"] = tool_call_id
    return payload


# ======================================================================================
# Sync Runner
# ======================================================================================


def run_sync_tool_loop(  # noqa: PLR0913
    *,
    client: OpenAI,
    model: str,
    prompt: str,
    tools: Sequence[dict[str, Any]],
    registry: Mapping[str, Callable[..., Any]],
    tool_choice: str | dict[str, Any] | None,
    max_rounds: int,
    temperature: float = 0.0,
    seed: int | None = None,
    final_response_format: dict[str, Any] | None = None,
    final_json_prompt: str = "Return ONLY JSON matching the response schema.",
) -> ToolLoopResult:
    """Run a sync OpenAI-compatible tool loop and return JSON-ready evidence."""
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    trace: list[ToolTraceEntry] = []
    current_tool_choice = tool_choice

    for _ in range(max_rounds):
        # 1. Ask the model for the next tool-capable assistant turn.
        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": list(tools),
            "temperature": temperature,
        }
        if seed is not None:
            call_kwargs["seed"] = seed
        if current_tool_choice is not None:
            call_kwargs["tool_choice"] = current_tool_choice

        response = client.chat.completions.create(**call_kwargs)
        tool_calls = extract_tool_calls(response)
        if not tool_calls:
            # 2. If tool use is done, either return plain text or request the
            # final structured JSON in one last assistant turn.
            if final_response_format is None:
                return {
                    "final_text": response_text(response),
                    "tool_trace": trace,
                }

            messages.append(assistant_message_dict(response))
            messages.append({"role": "user", "content": final_json_prompt})
            final_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "response_format": final_response_format,
                "temperature": temperature,
            }
            if seed is not None:
                final_kwargs["seed"] = seed
            final_response = client.chat.completions.create(**final_kwargs)
            return {
                "final_output": parse_message_json(final_response),
                "tool_trace": trace,
            }

        # 3. Record the assistant tool request, execute local tools, and append
        # the corresponding tool messages for the next round.
        messages.append(assistant_message_dict(response))
        for tool_call in tool_calls:
            tool_name = tool_call["tool_name"]
            arguments = tool_call["arguments"]
            result = registry[tool_name](**arguments)
            trace_entry: ToolTraceEntry = {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
            }
            trace.append(trace_entry)
            messages.append(
                tool_message_dict(
                    tool_call_id=tool_call["id"],
                    result=result,
                )
            )

        if current_tool_choice == "required" or isinstance(current_tool_choice, dict):
            current_tool_choice = "auto"

    msg = "The live tool loop did not finish within the configured round limit."
    raise RuntimeError(msg)


# ======================================================================================
# Async Runner
# ======================================================================================


async def run_async_tool_loop(  # noqa: PLR0913
    *,
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    tools: Sequence[dict[str, Any]],
    registry: Mapping[str, Callable[..., Any]],
    tool_choice: str | dict[str, Any] | None,
    max_rounds: int,
    temperature: float = 0.0,
    seed: int | None = None,
    final_response_format: dict[str, Any] | None = None,
    final_json_prompt: str = "Return ONLY JSON matching the response schema.",
) -> ToolLoopResult:
    """Run an async OpenAI-compatible tool loop and return JSON-ready evidence."""
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    trace: list[ToolTraceEntry] = []
    current_tool_choice = tool_choice

    for _ in range(max_rounds):
        # 1. Ask the model for the next tool-capable assistant turn.
        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": list(tools),
            "temperature": temperature,
        }
        if seed is not None:
            call_kwargs["seed"] = seed
        if current_tool_choice is not None:
            call_kwargs["tool_choice"] = current_tool_choice

        response = await client.chat.completions.create(**call_kwargs)
        tool_calls = extract_tool_calls(response)
        if not tool_calls:
            # 2. If tool use is done, either return plain text or request the
            # final structured JSON in one last assistant turn.
            if final_response_format is None:
                return {
                    "final_text": response_text(response),
                    "tool_trace": trace,
                }

            messages.append(assistant_message_dict(response))
            messages.append({"role": "user", "content": final_json_prompt})
            final_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "response_format": final_response_format,
                "temperature": temperature,
            }
            if seed is not None:
                final_kwargs["seed"] = seed
            final_response = await client.chat.completions.create(**final_kwargs)
            return {
                "final_output": parse_message_json(final_response),
                "tool_trace": trace,
            }

        # 3. Record the assistant tool request, execute local tools, and append
        # the corresponding tool messages for the next round.
        messages.append(assistant_message_dict(response))
        for tool_call in tool_calls:
            tool_name = tool_call["tool_name"]
            arguments = tool_call["arguments"]
            result = registry[tool_name](**arguments)
            trace_entry: ToolTraceEntry = {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
            }
            trace.append(trace_entry)
            messages.append(
                tool_message_dict(
                    tool_call_id=tool_call["id"],
                    result=result,
                )
            )

        if current_tool_choice == "required" or isinstance(current_tool_choice, dict):
            current_tool_choice = "auto"

    msg = "The live async tool loop did not finish within the configured round limit."
    raise RuntimeError(msg)
