"""Runtime trace assembly helpers.

Why:
    Owns provider-neutral attempt trace construction before traces are exposed
    through public response DTOs.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from py_lib_runtime import preview_value

from llm_router._api.errors import ProviderError
from llm_router._api.types import Provider, RoutingAttempt, ToolCall, ToolStep
from llm_router._internal.capabilities.content import (
    NormalizedMessage,
    TextPart,
    normalize_content,
)
from llm_router._internal.capabilities.schema import SchemaSpec, build_repair_prompt
from llm_router._internal.capabilities.tools import ToolChoice
from llm_router._internal.providers.base import ProviderRequest, ProviderResult
from llm_router._internal.runtime.effective_settings import EffectiveSettings
from llm_router._internal.runtime.routes import ExpandedRoute


def build_attempt_trace(
    *,
    route: ExpandedRoute,
    settings: EffectiveSettings,
    key_id: int,
    wait_seconds: float = 0.0,
    error: Exception | None = None,
) -> RoutingAttempt:
    """Build one public routing trace entry without SDK payloads."""
    provider = (
        route.provider.value if isinstance(route.provider, Provider) else route.provider
    )
    error_type = None if error is None else type(error).__name__
    error_message = None if error is None else str(error)
    return RoutingAttempt(
        route_index=route.route_index,
        provider=provider,
        model=route.model.value,
        key_id=key_id,
        wait_seconds=wait_seconds,
        temperature=settings.temperature,
        seed=settings.seed,
        max_tool_rounds=0
        if settings.max_tool_rounds is None
        else settings.max_tool_rounds,
        error_type=error_type,
        error_message=error_message,
    )


def append_tool_result_message(
    messages: Sequence[NormalizedMessage],
    steps: Sequence[ToolStep],
    *,
    all_steps: Sequence[ToolStep],
    request: ProviderRequest,
    result: ProviderResult,
) -> tuple[NormalizedMessage, ...]:
    """Append local tool results as provider-neutral user context."""
    if _uses_openai_tool_messages(request.provider):
        return (
            *messages,
            _openai_tool_call_message(result.tool_calls),
            *_openai_tool_result_messages(
                steps,
                include_name=request.provider is Provider.AISTUDIO,
            ),
        )
    if request.provider is Provider.GOOGLE:
        return (
            *messages,
            *_google_tool_messages(tool_calls=result.tool_calls, steps=steps),
        )
    if _uses_prompted_tool_messages(request.provider):
        return (
            *messages,
            normalize_content(result.output_text, role="assistant"),
            normalize_content(
                _prompted_tool_result_text(request=request, steps=all_steps)
            ),
        )
    return (*messages, normalize_content(_tool_result_text(steps)))


def next_tool_choice_after_tool_round(
    *,
    provider: Provider,
    tool_choice: ToolChoice | None,
) -> ToolChoice | None:
    """Return the tool-choice setting for the next provider turn."""
    if _uses_prompted_tool_messages(provider):
        return tool_choice
    return ToolChoice(kind="auto")


def append_repair_message(
    messages: Sequence[NormalizedMessage],
    *,
    request: ProviderRequest,
    schema: SchemaSpec | None,
    result: ProviderResult,
    error_message: str,
) -> tuple[NormalizedMessage, ...]:
    """Append provider-neutral structured-output repair guidance."""
    if schema is None:
        return tuple(messages)
    if _uses_native_schema_repair_prompt(request.provider):
        assistant_messages = _repair_assistant_messages(request=request, result=result)
        return (
            *messages,
            *assistant_messages,
            normalize_content("Return ONLY JSON matching the response schema."),
        )
    repair_prompt = build_repair_prompt(
        spec=schema,
        invalid_output=result.output_text,
        error_message=error_message,
    )
    return (*messages, normalize_content(repair_prompt))


def structured_output_error(
    *,
    result: ProviderResult,
    message: str,
) -> ProviderError:
    """Return the public provider error for exhausted structured repair."""
    cause = ValueError(f"Structured output validation failed: {message}")
    return ProviderError(
        cause,
        result.provider,
        result.model,
        message=str(cause),
    )


def _uses_openai_tool_messages(provider: Provider) -> bool:
    """Return whether provider turns should use OpenAI-native tool messages."""
    return provider in {
        Provider.AISTUDIO,
        Provider.OPENROUTER,
        Provider.MISTRAL,
        Provider.NVIDIA,
        Provider.GROQ,
        Provider.ALIBABA,
    }


def _uses_prompted_tool_messages(provider: Provider) -> bool:
    """Return whether tool turns should stay as textual provider prompts."""
    return provider in {Provider.GEMINI_WEBAPI, Provider.QWENCHAT}


def _openai_tool_call_message(tool_calls: Sequence[ToolCall]) -> NormalizedMessage:
    """Return an assistant tool-call transcript message."""
    return NormalizedMessage(
        role="assistant",
        parts=(TextPart(kind="text", text=""),),
        meta={
            "openai_tool_calls": [
                _openai_tool_call_payload(call) for call in tool_calls
            ]
        },
    )


def _openai_tool_call_payload(call: ToolCall) -> dict[str, object]:
    """Return an OpenAI-compatible tool-call payload."""
    return {
        "id": call.id,
        "type": "function",
        "function": {
            "name": call.name,
            "arguments": call.raw_arguments
            if call.raw_arguments is not None
            else _compact_json(call.args),
        },
    }


def _openai_tool_result_messages(
    steps: Sequence[ToolStep],
    *,
    include_name: bool,
) -> tuple[NormalizedMessage, ...]:
    """Return OpenAI-compatible tool result transcript messages."""
    messages: list[NormalizedMessage] = []
    for step in steps:
        meta: dict[str, object] = {"openai_tool_call_id": step.call_id or ""}
        if include_name:
            meta["openai_tool_name"] = step.tool_name
        messages.append(
            NormalizedMessage(
                role="tool",
                parts=(TextPart(kind="text", text=_compact_json(step.result)),),
                meta=meta,
            )
        )
    return tuple(messages)


def _google_tool_messages(
    *,
    tool_calls: Sequence[ToolCall],
    steps: Sequence[ToolStep],
) -> tuple[NormalizedMessage, ...]:
    """Return Gemini-native function call/response transcript messages."""
    messages: list[NormalizedMessage] = []
    for call, step in zip(tool_calls, steps, strict=False):
        messages.append(
            NormalizedMessage(
                role="model",
                parts=(),
                meta={
                    "google_function_call": {
                        "name": call.name,
                        "args": dict(call.args),
                    }
                },
            )
        )
        messages.append(
            NormalizedMessage(
                role="user",
                parts=(),
                meta={
                    "google_function_response": {
                        "name": step.tool_name,
                        "response": step.result,
                    }
                },
            )
        )
    return tuple(messages)


def _compact_json(value: object) -> str:
    """Return deterministic compact JSON for tool transcript payloads."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=preview_value,
    )


def _prompted_tool_result_text(
    *,
    request: ProviderRequest,
    steps: Sequence[ToolStep],
) -> str:
    """Return textual tool-loop context for prompt-led providers."""
    latest = steps[-1] if steps else None
    lines = [
        "Original task:",
        _initial_task_text(request.messages),
        "",
        "Completed tool steps so far:",
        _compact_json(
            [
                {
                    "args": step.args,
                    "call_id": step.call_id,
                    "result": step.result,
                    "tool_name": step.tool_name,
                }
                for step in steps
            ]
        ),
    ]
    if latest is not None:
        lines.extend(
            [
                "",
                f"Tool {latest.tool_name} returned {_compact_json(latest.result)}.",
            ]
        )
    lines.extend(
        [
            (
                "If another tool is needed, reply with exactly one function call "
                "and nothing else."
            ),
            "If all required tool work is complete, return ONLY valid JSON.",
        ]
    )
    if request.schema is not None:
        from llm_router._internal.providers._prompted import build_json_instruction

        lines.extend(["", build_json_instruction(request.schema)])
    return "\n".join(lines)


def _initial_task_text(messages: Sequence[NormalizedMessage]) -> str:
    """Return the initial user task text before assistant/tool-loop turns."""
    chunks: list[str] = []
    for message in messages:
        if message.role != "user":
            break
        chunks.extend(part.text for part in message.parts if isinstance(part, TextPart))
    return "\n\n".join(chunks)


def _tool_result_text(steps: Sequence[ToolStep]) -> str:
    """Return bounded tool-result context for a follow-up model turn."""
    payload = [
        {
            "tool_name": step.tool_name,
            "args": step.args,
            "result": step.result,
            "call_id": step.call_id,
        }
        for step in steps
    ]
    rendered_payload = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=preview_value,
    )
    return (
        "Tool results from the previous assistant tool call:\n"
        f"{rendered_payload}\n"
        "Use these tool results to continue the answer."
    )


def _uses_native_schema_repair_prompt(provider: Provider) -> bool:
    """Return whether native schema support should use a short repair turn."""
    return provider in {
        Provider.AISTUDIO,
        Provider.GOOGLE,
        Provider.OPENROUTER,
        Provider.MISTRAL,
        Provider.NVIDIA,
        Provider.GROQ,
        Provider.ALIBABA,
    }


def _repair_assistant_messages(
    *,
    request: ProviderRequest,
    result: ProviderResult,
) -> tuple[NormalizedMessage, ...]:
    """Return provider-aware assistant context for a schema repair turn."""
    if request.provider is Provider.GOOGLE and isinstance(
        result.data.get("text_parts"),
        list,
    ):
        return (
            NormalizedMessage(
                role="assistant",
                parts=(),
                meta={"google_text_parts": list(result.data["text_parts"])},
            ),
        )
    if not result.output_text:
        return ()
    return (normalize_content(result.output_text, role="assistant"),)
