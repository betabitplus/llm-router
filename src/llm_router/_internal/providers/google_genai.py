"""Google GenAI provider adapter.

Why:
    Owns native Google GenAI request and response translation behind the
    provider-neutral adapter port.
"""

from __future__ import annotations

import json
import mimetypes
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from llm_router._api.contracts import ToolCall
from llm_router._api.errors import ProviderError
from llm_router._api.types import Provider
from llm_router._internal.capabilities.content import (
    MediaPart,
    NormalizedMessage,
    TextPart,
)
from llm_router._internal.capabilities.media import (
    FileMedia,
    ImageMedia,
    VideoFileMedia,
)
from llm_router._internal.capabilities.tools import ToolChoice, parse_tool_call
from llm_router._internal.capabilities.usage import normalize_usage
from llm_router._internal.config.models import LLMRouterConfig
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.providers.gemini_schema import gemini_schema
from llm_router._internal.providers.retry import (
    classify_exception,
    classify_status_code,
)
from llm_router._support.error_formatting import preview_exception_message
from llm_router._support.logging import get_logger

logger = get_logger(__name__)

_ROLE_MAP = {"user": "user", "assistant": "model"}


class GoogleGenAIAdapter:
    """Native adapter for Google GenAI generate-content requests."""

    capabilities = ProviderCapabilities(
        supports_images=True,
        supports_files=True,
        supports_video=True,
        supports_json_schema=True,
        supports_tools=True,
    )

    def __init__(
        self,
        *,
        client: object | None = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        """Create an adapter with an optional fake client for tests."""
        self._client = client
        self.timeout_seconds = timeout_seconds

    def build_contents(self, request: ProviderRequest) -> list[types.Content]:
        """Build Google-native content turns from normalized messages."""
        return [_content_payload(message) for message in request.messages]

    def build_config(self, request: ProviderRequest) -> types.GenerateContentConfig:
        """Build Google-native generation config from normalized settings."""
        config_kwargs: dict[str, Any] = {}
        if request.temperature is not None:
            config_kwargs["temperature"] = request.temperature
        if request.seed is not None:
            config_kwargs["seed"] = request.seed
        if request.schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = gemini_schema(request.schema.json_schema)
        if request.tool_registry is not None and request.tool_registry.tools:
            config_kwargs["tools"] = [_tool_payload(request)]
        if request.tool_choice is not None:
            config_kwargs["tool_config"] = _tool_choice_payload(request.tool_choice)
        config_kwargs.update(dict(request.kwargs))
        return types.GenerateContentConfig(**config_kwargs)

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one synchronous Google GenAI request."""
        logger.info(
            "Provider request started",
            event_type="llm_router.provider.request.started",
            **request.log_context(),
        )
        try:
            client = self._client_for(request)
            response = client.models.generate_content(
                model=request.provider_model,
                contents=self.build_contents(request),
                config=self.build_config(request),
            )
        except Exception as exc:
            failure = _failure_from_exception(request=request, exc=exc)
            _log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            ) from exc
        return parse_google_genai_response(request=request, response=response)

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one asynchronous Google GenAI request."""
        logger.info(
            "Provider request started",
            event_type="llm_router.provider.request.started",
            **request.log_context(),
        )
        try:
            client = self._client_for(request)
            response = await client.aio.models.generate_content(
                model=request.provider_model,
                contents=self.build_contents(request),
                config=self.build_config(request),
            )
        except Exception as exc:
            failure = _failure_from_exception(request=request, exc=exc)
            _log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            ) from exc
        return parse_google_genai_response(request=request, response=response)

    def _client_for(self, request: ProviderRequest) -> Any:  # noqa: ANN401
        """Return a client for one credential without caching key material."""
        if self._client is not None:
            return self._client
        return genai.Client(api_key=request.credential.value)


def adapter_from_config(
    config: LLMRouterConfig,
    provider: Provider,
) -> GoogleGenAIAdapter:
    """Build a Google GenAI adapter from one config snapshot."""
    if provider is not Provider.GOOGLE:
        msg = f"Provider '{provider.value}' is not Google GenAI."
        raise KeyError(msg)
    timeout_seconds = config.policy.attempt_timeout_seconds or 600.0
    return GoogleGenAIAdapter(timeout_seconds=timeout_seconds)


def parse_google_genai_response(
    *,
    request: ProviderRequest,
    response: object,
) -> ProviderResult:
    """Parse a Google GenAI response into the provider-neutral result port."""
    data = _response_data(response)
    result = ProviderResult(
        data=data,
        provider=request.provider,
        model=request.model,
        provider_model=request.provider_model,
        output_text=_response_text(response, data=data),
        usage=normalize_usage(_response_usage(response)),
        tool_calls=_response_tool_calls(response),
    )
    logger.info(
        "Provider request completed",
        event_type="llm_router.provider.request.completed",
        **request.log_context(),
    )
    return result


def _part_payload(part: TextPart | MediaPart) -> types.Part:
    """Translate one normalized part to a Google-native part."""
    if isinstance(part, TextPart):
        return types.Part(text=part.text)
    media = part.media
    if isinstance(media, ImageMedia):
        return types.Part(
            inline_data=types.Blob(
                data=_image_bytes(media),
                mime_type="image/png",
            )
        )
    if isinstance(media, FileMedia):
        path = Path(media.path)
        return types.Part(
            inline_data=types.Blob(
                data=path.read_bytes(),
                mime_type=media.mime_type or _mime_type(path.name),
            )
        )
    if isinstance(media, VideoFileMedia):
        path = Path(media.path)
        return types.Part(
            inline_data=types.Blob(
                data=path.read_bytes(),
                mime_type=_video_mime_type(path.name),
            ),
            video_metadata=_video_metadata(
                fps=media.fps,
                start_offset=media.start_offset,
                end_offset=media.end_offset,
            ),
        )
    return types.Part(
        file_data=types.FileData(
            file_uri=media.url,
        ),
        video_metadata=_video_metadata(
            fps=media.fps,
            start_offset=media.start_offset,
            end_offset=media.end_offset,
        ),
    )


def _tool_payload(request: ProviderRequest) -> types.Tool:
    """Translate normalized tools to Google function declarations."""
    if request.tool_registry is None:
        msg = "Google tool payload requires a tool registry."
        raise ValueError(msg)
    declarations = [
        types.FunctionDeclaration(
            name=definition.name,
            description=definition.description or "",
            parameters=gemini_schema(
                definition.parameters,
                include_titles=False,
                include_property_ordering=False,
            ),
        )
        for definition in request.tool_registry.tools.values()
    ]
    return types.Tool(function_declarations=declarations)


def _content_payload(message: NormalizedMessage) -> types.Content:
    """Build one Google-native content turn, including tool-loop turns."""
    function_call = message.meta.get("google_function_call")
    if isinstance(function_call, Mapping):
        function_args = function_call.get("args")
        args = dict(function_args) if isinstance(function_args, Mapping) else {}
        return types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name=str(function_call.get("name") or ""),
                        args=args,
                    )
                )
            ],
        )
    function_response = message.meta.get("google_function_response")
    if isinstance(function_response, Mapping):
        return types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        name=str(function_response.get("name") or ""),
                        response=_function_response_payload(
                            function_response.get("response")
                        ),
                    )
                )
            ],
        )
    text_parts = message.meta.get("google_text_parts")
    if isinstance(text_parts, list):
        return types.Content(
            role="model",
            parts=[
                types.Part(text=text) for text in text_parts if isinstance(text, str)
            ],
        )
    return types.Content(
        role=_ROLE_MAP.get(message.role, "user"),
        parts=[_part_payload(part) for part in message.parts],
    )


def _function_response_payload(value: object) -> dict[str, object]:
    """Return a Gemini function-response object payload."""
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {"result": value}


def _tool_choice_payload(choice: ToolChoice) -> types.ToolConfig:
    """Translate normalized tool choice to Google tool config."""
    mode_lookup = {
        "auto": "AUTO",
        "none": "NONE",
        "required": "ANY",
        "named": "ANY",
        "raw": "ANY",
    }
    allowed = [choice.name] if choice.name else None
    return types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode=mode_lookup[choice.kind],
            allowed_function_names=allowed,
        )
    )


def _response_data(response: object) -> dict[str, Any]:
    """Return JSON-safe response evidence without SDK objects."""
    data: dict[str, Any] = {}
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, BaseModel):
        data["parsed"] = parsed.model_dump(mode="json")
    elif isinstance(parsed, Mapping):
        data["parsed"] = dict(parsed)
    text = str(getattr(response, "text", "") or "")
    if text:
        data["text"] = text
    text_parts = [
        part_text
        for part in _candidate_parts(response)
        if isinstance(part_text := getattr(part, "text", None), str)
    ]
    if text_parts:
        data["text_parts"] = text_parts
    usage = normalize_usage(_response_usage(response))
    if usage is not None:
        data["usage"] = usage.model_dump()
    return data


def _response_text(response: object, *, data: dict[str, Any]) -> str:
    """Extract assistant text from native Google response shapes."""
    text = str(getattr(response, "text", "") or "")
    if text:
        return text
    parsed = data.get("parsed")
    if parsed is not None:
        return json.dumps(parsed, sort_keys=True)
    return _text_from_parts(response)


def _text_from_parts(response: object) -> str:
    """Extract text from candidate content parts when `.text` is absent."""
    texts: list[str] = []
    for part in _candidate_parts(response):
        text = getattr(part, "text", None)
        if isinstance(text, str):
            texts.append(text)
    return "".join(texts)


def _response_tool_calls(response: object) -> tuple[ToolCall, ...]:
    """Extract normalized tool calls from native Google function calls."""
    calls: list[ToolCall] = []
    for part in _candidate_parts(response):
        function_call = getattr(part, "function_call", None)
        if function_call is None:
            continue
        calls.append(
            parse_tool_call(
                {
                    "id": getattr(function_call, "id", None),
                    "functionCall": {
                        "name": getattr(function_call, "name", None),
                        "args": getattr(function_call, "args", None) or {},
                    },
                }
            )
        )
    return tuple(calls)


def _candidate_parts(response: object) -> list[object]:
    """Return the first candidate's parts from SDK-like response objects."""
    candidates = getattr(response, "candidates", None)
    if not candidates:
        return []
    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None)
    return list(parts or [])


def _response_usage(response: object) -> object | None:
    """Return the native usage metadata object when present."""
    return getattr(response, "usage_metadata", None)


def _failure_from_exception(
    *,
    request: ProviderRequest,
    exc: Exception,
) -> ProviderFailure:
    """Build a classified provider failure from SDK exceptions."""
    status_code = _exception_status_code(exc)
    decision = (
        classify_status_code(status_code)
        if status_code is not None
        else classify_exception(exc)
    )
    return ProviderFailure(
        provider=request.provider,
        model=request.model,
        message=preview_exception_message(exc),
        retryable=decision.retryable,
        status_code=status_code,
        retry_reason=decision.reason,
    )


def _exception_status_code(exc: Exception) -> int | None:
    """Extract an HTTP status code from common SDK exception shapes."""
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _image_bytes(media: ImageMedia) -> bytes:
    """Encode an image as PNG bytes for native inline data."""
    buffer = BytesIO()
    media.image.save(buffer, format="PNG")
    return buffer.getvalue()


def _video_metadata(
    *,
    fps: int,
    start_offset: int | None,
    end_offset: int | None,
) -> types.VideoMetadata:
    """Build Google video metadata from normalized public hints."""
    return types.VideoMetadata(
        fps=float(fps),
        start_offset=_offset(start_offset),
        end_offset=_offset(end_offset),
    )


def _offset(value: int | None) -> str | None:
    """Format second offsets for Gemini video metadata."""
    return None if value is None else f"{value}s"


def _mime_type(name: str) -> str:
    """Guess a file MIME type with a safe fallback."""
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def _video_mime_type(name_or_url: str) -> str:
    """Guess a video MIME type with MP4 as the default."""
    return "video/quicktime" if name_or_url.lower().endswith(".mov") else "video/mp4"


def _log_provider_failure(
    *,
    request: ProviderRequest,
    failure: ProviderFailure,
) -> None:
    """Log one provider failure with safe fields."""
    logger.warning(
        "Provider request failed",
        event_type="llm_router.provider.request.failed",
        **request.log_context(),
        error_type=type(failure).__name__,
        error_message=failure.message,
        result_status=failure.status_code,
        retryable=failure.retryable,
        retry_reason=failure.retry_reason,
    )
