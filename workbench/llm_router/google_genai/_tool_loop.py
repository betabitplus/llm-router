# %%
"""Google GenAI workbench tool-loop helpers.

Why:
    Keeps the native function-call loop in one place so multiple workbench
    scripts can inspect tool behavior without depending on `src/` internals.

When to use:
    Import from Google GenAI workbench scripts that need callable declarations,
    tool-choice config, function-call extraction, or one real tool round-trip.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypedDict

from google.genai import types
from pydantic import BaseModel

from workbench.llm_router.google_genai._sdk_helpers import parsed_response_dict

_RESPONSE_SCHEMA_PROMPT = "Return ONLY JSON matching the response schema."


class FunctionCall(TypedDict):
    """One parsed function call emitted by the Google GenAI response."""

    tool_name: str
    arguments: dict[str, Any]
    id: str | None


class ToolTraceEntry(TypedDict):
    """One locally executed tool step recorded for workbench output."""

    tool_name: str
    arguments: dict[str, Any]
    result: object


class ToolLoopResult(TypedDict):
    """JSON-ready evidence returned by the native Google tool loop."""

    tool_trace: list[ToolTraceEntry]
    final_output: dict[str, Any]


# ======================================================================================
# Tool-Configuration Helpers
# ======================================================================================


def build_tool_config(
    *,
    tool_functions: Sequence[Callable[..., Any]],
    tool_choice: str | dict[str, Any] | None,
) -> types.GenerateContentConfig:
    """Build one native Google tool config for the given functions."""
    declarations = [
        types.FunctionDeclaration.from_callable_with_api_option(callable=fn)
        for fn in tool_functions
    ]
    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=declarations)],
        temperature=0,
    )

    if tool_choice is None:
        return config

    if isinstance(tool_choice, str) and tool_choice in {
        "auto",
        "none",
        "required",
    }:
        mode_lookup = {
            "auto": "AUTO",
            "none": "NONE",
            "required": "ANY",
        }
        config.tool_config = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=mode_lookup[tool_choice]
            )
        )
        return config

    function_name = str(tool_choice["function"]["name"])
    config.tool_config = types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[function_name],
        )
    )
    return config


# ======================================================================================
# Response Parsing Helpers
# ======================================================================================


def extract_function_calls(response: object) -> list[FunctionCall]:
    """Extract function calls from one native Google SDK response."""
    try:
        parts = response.candidates[0].content.parts
    except Exception as exc:
        msg = "The live response did not expose content parts."
        raise RuntimeError(msg) from exc

    tool_calls: list[FunctionCall] = []
    for part in parts:
        function_call = getattr(part, "function_call", None)
        if function_call is None:
            continue
        tool_calls.append(
            {
                "tool_name": str(function_call.name),
                "arguments": dict(function_call.args or {}),
                "id": getattr(function_call, "id", None),
            }
        )
    return tool_calls


def _validate_final_output(
    *,
    final_output: dict[str, Any],
    response_schema: type[BaseModel],
) -> dict[str, Any]:
    """Validate one final tool-loop payload against the declared schema."""
    return response_schema.model_validate(final_output).model_dump(mode="json")


# ======================================================================================
# Conversation Assembly
# ======================================================================================


def _append_model_turn(
    *,
    contents: list[Any],
    response: object,
) -> None:
    """Append one model response as a content turn."""
    model_parts = list(response.candidates[0].content.parts)
    contents.append(types.Content(role="model", parts=model_parts))


def _append_function_responses(
    *,
    contents: list[Any],
    tool_calls: list[FunctionCall],
    tool_functions: Sequence[Callable[..., Any]],
    trace: list[ToolTraceEntry],
) -> None:
    """Execute tool calls, update the trace, and append function responses."""
    response_parts = []
    for call in tool_calls:
        tool_name = str(call["tool_name"])
        tool_args = dict(call["arguments"])
        function = next(fn for fn in tool_functions if fn.__name__ == tool_name)
        result = function(**tool_args)
        response_payload = result if isinstance(result, dict) else {"result": result}
        trace_entry: ToolTraceEntry = {
            "tool_name": tool_name,
            "arguments": tool_args,
            "result": result,
        }
        trace.append(trace_entry)
        response_parts.append(
            types.Part(
                function_response=types.FunctionResponse(
                    name=tool_name,
                    response=response_payload,
                )
            )
        )
    contents.append(types.Content(role="user", parts=response_parts))


# ======================================================================================
# Sync Runner
# ======================================================================================


def run_sync_tool_loop(  # noqa: PLR0913
    *,
    client: Any,  # noqa: ANN401
    model: str,
    prompt: str,
    tool_functions: Sequence[Callable[..., Any]],
    response_schema: type[BaseModel],
    tool_choice: str | dict[str, Any] | None,
    max_rounds: int,
) -> ToolLoopResult:
    """Run a native Google sync tool loop and return JSON-ready evidence."""
    contents: list[Any] = [prompt]
    trace: list[ToolTraceEntry] = []
    current_tool_choice = tool_choice

    for _ in range(max_rounds):
        # 1. Ask the model for the next turn with live tool calling enabled.
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=build_tool_config(
                tool_functions=tool_functions,
                tool_choice=current_tool_choice,
            ),
        )
        tool_calls = extract_function_calls(response)
        if not tool_calls:
            # 2. Once tool calls stop, request one final schema-constrained JSON
            # answer from the same conversation state.
            _append_model_turn(contents=contents, response=response)
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=_RESPONSE_SCHEMA_PROMPT)],
                )
            )
            final_response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0,
                ),
            )
            final_output = _validate_final_output(
                final_output=parsed_response_dict(final_response),
                response_schema=response_schema,
            )
            return {
                "tool_trace": trace,
                "final_output": final_output,
            }

        # 3. Persist the model turn, execute local tools, and append their
        # function responses for the next round.
        _append_model_turn(contents=contents, response=response)
        _append_function_responses(
            contents=contents,
            tool_calls=tool_calls,
            tool_functions=tool_functions,
            trace=trace,
        )
        if current_tool_choice == "required" or isinstance(current_tool_choice, dict):
            current_tool_choice = "auto"

    msg = "The native tool loop did not finish within the configured round limit."
    raise RuntimeError(msg)


# ======================================================================================
# Async Runner
# ======================================================================================


async def run_async_tool_loop(  # noqa: PLR0913
    *,
    client: Any,  # noqa: ANN401
    model: str,
    prompt: str,
    tool_functions: Sequence[Callable[..., Any]],
    response_schema: type[BaseModel],
    tool_choice: str | dict[str, Any] | None,
    max_rounds: int,
) -> ToolLoopResult:
    """Run a native Google async tool loop and return JSON-ready evidence."""
    contents: list[Any] = [prompt]
    trace: list[ToolTraceEntry] = []
    current_tool_choice = tool_choice

    for _ in range(max_rounds):
        # 1. Ask the model for the next turn with live tool calling enabled.
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=build_tool_config(
                tool_functions=tool_functions,
                tool_choice=current_tool_choice,
            ),
        )
        tool_calls = extract_function_calls(response)
        if not tool_calls:
            # 2. Once tool calls stop, request one final schema-constrained JSON
            # answer from the same conversation state.
            _append_model_turn(contents=contents, response=response)
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=_RESPONSE_SCHEMA_PROMPT)],
                )
            )
            final_response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0,
                ),
            )
            final_output = _validate_final_output(
                final_output=parsed_response_dict(final_response),
                response_schema=response_schema,
            )
            return {
                "tool_trace": trace,
                "final_output": final_output,
            }

        # 3. Persist the model turn, execute local tools, and append their
        # function responses for the next round.
        _append_model_turn(contents=contents, response=response)
        _append_function_responses(
            contents=contents,
            tool_calls=tool_calls,
            tool_functions=tool_functions,
            trace=trace,
        )
        if current_tool_choice == "required" or isinstance(current_tool_choice, dict):
            current_tool_choice = "auto"

    msg = "The native async tool loop did not finish within the configured round limit."
    raise RuntimeError(msg)
