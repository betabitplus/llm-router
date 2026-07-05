"""Prompt-led provider helper functions.

Why:
    Shares the small JSON-instruction and textual-tool seams used by providers
    that do not expose native structured-output or tool-call APIs.
"""

from __future__ import annotations

import base64
import inspect
import json
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from llm_router._api.types import ToolCall
from llm_router._internal.capabilities.content import (
    NormalizedMessage,
    TextPart,
)
from llm_router._internal.capabilities.media import (
    FileMedia,
    ImageMedia,
    VideoFileMedia,
    VideoUrlMedia,
)
from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    validate_schema_output,
)
from llm_router._internal.capabilities.tools import ToolChoice, ToolRegistry
from llm_router._internal.providers.base import ProviderRequest

_TEXTUAL_TOOL_CALL_RE = re.compile(r"^(?P<tool_name>\w+)\((?P<args>.*)\)$")
_POSITIONAL_TOOL_ARG_NAMES = ("a", "b")
QwenChatMediaUploader = Callable[[ImageMedia | FileMedia | VideoFileMedia], object]


def build_json_instruction(spec: SchemaSpec) -> str:
    """Build a compact JSON-only instruction for prompt-led schema providers."""
    schema = json.dumps(dict(spec.json_schema), ensure_ascii=False)
    return (
        "You are a JSON API. Output MUST be valid JSON and MUST conform to this "
        "JSON Schema.\n\n"
        "Return ONLY the JSON (no markdown, no code fences, no extra text).\n\n"
        f"JSON Schema:\n{schema}"
    )


def parse_prompted_structured_data(
    *,
    spec: SchemaSpec,
    text: str,
) -> object | None:
    """Return parsed structured data from prompt-led model text when valid."""
    for candidate in _structured_candidates(text):
        result = validate_schema_output(spec, candidate)
        if result.valid:
            return result.value
    return None


def json_safe_value(value: object) -> object:
    """Convert common parsed values into JSON-safe evidence."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): json_safe_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [json_safe_value(item) for item in value]
    return value


def build_tool_instruction(
    *,
    registry: ToolRegistry,
    choice: ToolChoice | None,
) -> str:
    """Build prompt guidance for exact textual tool-call providers."""
    lines = [
        "You can use local tools.",
        "",
        "Available tools:",
    ]
    for definition in registry.tools.values():
        parameters = ", ".join(_parameter_names(definition.parameters))
        signature = (
            f"{definition.name}({parameters})" if parameters else definition.name
        )
        description = f": {definition.description}" if definition.description else ""
        lines.append(f"- {signature}{description}")
    lines.extend(
        [
            "",
            (
                "When a tool is needed, reply with exactly one function call "
                "and nothing else."
            ),
            "Use the format tool_name(arg=value) or tool_name(value1, value2).",
        ]
    )
    if choice is not None:
        if choice.kind == "none":
            lines.append("Do not call any tool.")
        elif choice.kind in {"named", "raw"} and choice.name:
            lines.append(
                f"You MUST use only the tool `{choice.name}` when a tool is used."
            )
        elif choice.kind == "required":
            lines.append("You MUST use tools before giving the final answer.")
    lines.extend(
        [
            "Do not solve tool work yourself.",
            "If all required tool work is complete, return ONLY valid JSON.",
        ]
    )
    return "\n".join(lines)


def textual_tool_call_from_text(
    *,
    text: str,
    registry: ToolRegistry | None,
) -> ToolCall | None:
    """Parse one exact textual function call from model text when present."""
    match = _TEXTUAL_TOOL_CALL_RE.fullmatch(text.strip())
    if match is None:
        return None
    tool_name = match.group("tool_name")
    if registry is not None and tool_name not in registry.tools:
        return None
    raw_args = match.group("args").strip()
    return ToolCall(
        name=tool_name,
        args=_parse_textual_args(raw_args),
        raw_arguments=raw_args,
    )


def qwenchat_uses_textual_tool_prompt(request: ProviderRequest) -> bool:
    """Return whether this Qwen request should prompt for textual tool calls."""
    return bool(
        request.tool_registry is not None
        and request.tool_registry.tools
        and request.tool_choice is not None
        and request.tool_choice.kind != "none"
    )


def qwenchat_tool_choice_payload(request: ProviderRequest) -> object:
    """Translate normalized tool choice to a QwenChat/OpenAI-like shape."""
    choice = request.tool_choice
    if choice is None:
        return "auto"
    if choice.kind in {"auto", "none", "required"}:
        return choice.kind
    if choice.kind == "named" and choice.name:
        return {"type": "function", "function": {"name": choice.name}}
    if choice.kind == "raw":
        return dict(choice.raw or {})
    return "auto"


def qwenchat_message_payload(
    *,
    request: ProviderRequest,
    message: NormalizedMessage,
    uploader: QwenChatMediaUploader | None,
    include_schema: bool,
) -> dict[str, object]:
    """Translate one normalized message into a QwenChat message."""
    content = _qwenchat_message_content(
        request=request,
        message=message,
        uploader=uploader,
        include_schema=include_schema,
    )
    return {"role": message.role, "content": content}


async def qwenchat_amessage_payload(
    *,
    request: ProviderRequest,
    message: NormalizedMessage,
    uploader: QwenChatMediaUploader | None,
    include_schema: bool,
) -> dict[str, object]:
    """Translate one normalized message into an async QwenChat message."""
    content = await _qwenchat_amessage_content(
        request=request,
        message=message,
        uploader=uploader,
        include_schema=include_schema,
    )
    return {"role": message.role, "content": content}


def qwenchat_initial_user_prefix(
    messages: Sequence[NormalizedMessage],
) -> tuple[tuple[NormalizedMessage, ...], tuple[NormalizedMessage, ...]]:
    """Split initial user task messages from later assistant/tool-loop turns."""
    prefix: list[NormalizedMessage] = []
    for message in messages:
        if message.role != "user":
            break
        prefix.append(message)
    return tuple(prefix), tuple(messages[len(prefix) :])


def qwenchat_combined_initial_message(
    *,
    request: ProviderRequest,
    messages: Sequence[NormalizedMessage],
) -> NormalizedMessage:
    """Combine initial task turns behind prompt-led Qwen instructions."""
    lead = _qwenchat_initial_instruction_text(request=request, messages=messages)
    parts = [TextPart(kind="text", text=lead)] if lead else []
    for message in messages:
        parts.extend(message.parts)
    return NormalizedMessage(role="user", parts=tuple(parts), meta={})


def _qwenchat_initial_instruction_text(
    *,
    request: ProviderRequest,
    messages: Sequence[NormalizedMessage],
) -> str:
    """Return schema/tool instructions prepended to the first Qwen message."""
    sections: list[str] = []
    if qwenchat_uses_textual_tool_prompt(request):
        sections.append(
            build_tool_instruction(
                registry=request.tool_registry,
                choice=request.tool_choice,
            )
        )
    if request.schema is not None:
        sections.append(build_json_instruction(request.schema))
    if qwenchat_uses_textual_tool_prompt(request):
        sections.append(f"Original task:\n{_qwenchat_message_text(messages)}")
    return "\n\n".join(section for section in sections if section)


def _qwenchat_message_text(messages: Sequence[NormalizedMessage]) -> str:
    """Return joined text from provider-neutral messages."""
    chunks: list[str] = []
    for message in messages:
        chunks.extend(part.text for part in message.parts if isinstance(part, TextPart))
    return "\n\n".join(chunks)


def _qwenchat_message_content(
    *,
    request: ProviderRequest,
    message: NormalizedMessage,
    uploader: QwenChatMediaUploader | None,
    include_schema: bool,
) -> str | list[dict[str, str]]:
    """Build one QwenChat string or mixed content array."""
    parts: list[dict[str, str]] = []
    text_buffer: list[str] = []

    def flush_text() -> None:
        """Move buffered text into the mixed content list."""
        if not text_buffer:
            return
        parts.append({"type": "text", "text": "\n\n".join(text_buffer)})
        text_buffer.clear()

    if include_schema and request.schema is not None:
        text_buffer.append(build_json_instruction(request.schema))

    for part in message.parts:
        if isinstance(part, TextPart):
            text_buffer.append(part.text)
            continue
        flush_text()
        parts.append(_qwenchat_media_content_part(part.media, uploader=uploader))

    flush_text()
    if len(parts) == 1 and parts[0]["type"] == "text":
        return parts[0]["text"]
    return parts


async def _qwenchat_amessage_content(
    *,
    request: ProviderRequest,
    message: NormalizedMessage,
    uploader: QwenChatMediaUploader | None,
    include_schema: bool,
) -> str | list[dict[str, str]]:
    """Build one async QwenChat string or mixed content array."""
    parts: list[dict[str, str]] = []
    text_buffer: list[str] = []

    def flush_text() -> None:
        """Move buffered text into the async mixed content list."""
        if not text_buffer:
            return
        parts.append({"type": "text", "text": "\n\n".join(text_buffer)})
        text_buffer.clear()

    if include_schema and request.schema is not None:
        text_buffer.append(build_json_instruction(request.schema))

    for part in message.parts:
        if isinstance(part, TextPart):
            text_buffer.append(part.text)
            continue
        flush_text()
        parts.append(await _qwenchat_amedia_content_part(part.media, uploader=uploader))

    flush_text()
    if len(parts) == 1 and parts[0]["type"] == "text":
        return parts[0]["text"]
    return parts


def _qwenchat_media_content_part(
    media: ImageMedia | FileMedia | VideoFileMedia | VideoUrlMedia,
    *,
    uploader: QwenChatMediaUploader | None,
) -> dict[str, str]:
    """Translate one media descriptor to a QwenChat uploaded part."""
    if isinstance(media, VideoUrlMedia):
        return {"type": "file", "file": media.url}
    if uploader is None:
        url = _qwenchat_offline_media_url(media)
    else:
        uploaded = uploader(media)
        if inspect.isawaitable(uploaded):
            msg = "Async QwenChat uploaders cannot be used in sync payload builds."
            raise TypeError(msg)
        url = str(uploaded)
    if isinstance(media, ImageMedia):
        return {"type": "image", "image": url}
    return {"type": "file", "file": url}


async def _qwenchat_amedia_content_part(
    media: ImageMedia | FileMedia | VideoFileMedia | VideoUrlMedia,
    *,
    uploader: QwenChatMediaUploader | None,
) -> dict[str, str]:
    """Translate one media descriptor to an async QwenChat uploaded part."""
    if isinstance(media, VideoUrlMedia):
        return {"type": "file", "file": media.url}
    if uploader is None:
        url = _qwenchat_offline_media_url(media)
    else:
        uploaded = uploader(media)
        if inspect.isawaitable(uploaded):
            uploaded = await uploaded
        url = str(uploaded)
    if isinstance(media, ImageMedia):
        return {"type": "image", "image": url}
    return {"type": "file", "file": url}


def _qwenchat_offline_media_url(media: ImageMedia | FileMedia | VideoFileMedia) -> str:
    """Return a deterministic media URL for unit payload construction."""
    if isinstance(media, ImageMedia):
        return "qwen-upload://image.png"
    path = Path(media.path)
    encoded = base64.urlsafe_b64encode(str(path).encode("utf-8")).decode("ascii")
    return f"qwen-upload://{encoded}"


def _structured_candidates(text: str) -> tuple[str, ...]:
    """Return raw, fenced, and embedded JSON object candidates."""
    cleaned = text.strip()
    unfenced = cleaned.removeprefix("```json").removeprefix("```")
    unfenced = unfenced.removesuffix("```").strip()
    candidates = [cleaned]
    if unfenced != cleaned:
        candidates.append(unfenced)
    embedded = _extract_json_object(unfenced)
    if embedded is not None and embedded not in candidates:
        candidates.append(embedded)
    return tuple(candidate for candidate in candidates if candidate)


def _extract_json_object(text: str) -> str | None:
    """Extract one object-like JSON substring from model text."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _parameter_names(parameters: Mapping[str, Any]) -> tuple[str, ...]:
    """Return stable parameter names from a JSON-schema-like parameter mapping."""
    properties = parameters.get("properties")
    if isinstance(properties, Mapping):
        return tuple(str(name) for name in properties)
    return ()


def _parse_textual_args(raw_args: str) -> dict[str, object]:
    """Parse `a=1, b=2` or positional `1, 2` textual tool arguments."""
    if not raw_args:
        return {}
    parsed: dict[str, object] = {}
    positional_index = 0
    for item in raw_args.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        if "=" in cleaned:
            name, raw_value = cleaned.split("=", 1)
            parsed[name.strip()] = _parse_scalar(raw_value.strip())
            continue
        if positional_index >= len(_POSITIONAL_TOOL_ARG_NAMES):
            break
        parsed[_POSITIONAL_TOOL_ARG_NAMES[positional_index]] = _parse_scalar(cleaned)
        positional_index += 1
    return parsed


def _parse_scalar(value: str) -> object:
    """Parse one scalar textual tool argument with a string fallback."""
    with_json = value
    try:
        return json.loads(with_json)
    except json.JSONDecodeError:
        pass
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value.strip("\"'")
