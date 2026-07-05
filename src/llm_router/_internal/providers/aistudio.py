"""AI Studio provider adapter.

Why:
    Owns AI Studio dispatch between the OpenAI-compatible non-media path and
    Gemini-native PDF/video HTTP payloads.
"""

from __future__ import annotations

import base64
import contextlib
import json
import mimetypes
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx

from llm_router._internal.contracts.errors import ProviderError
from llm_router._internal.contracts.types import Provider
from llm_router._internal.capabilities.content import MediaPart, TextPart
from llm_router._internal.capabilities.media import (
    FileMedia,
    ImageMedia,
    VideoFileMedia,
    VideoUrlMedia,
)
from llm_router._internal.capabilities.schema import (
    with_schema_transform,
)
from llm_router._internal.capabilities.usage import normalize_usage
from llm_router._internal.config.models import LLMRouterConfig
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.providers.gemini_schema import gemini_schema
from llm_router._internal.providers.openai_compatible import (
    OpenAICompatibleAdapter,
    adapter_from_config as openai_adapter_from_config,
)
from llm_router._internal.providers.retry import (
    classify_exception,
    classify_status_code,
)
from py_lib_runtime import preview_exception_message, preview_text
from py_lib_runtime import get_logger

logger = get_logger(__name__)

_HTTP_ERROR_STATUS_MIN = 400


class AIStudioAdapter:
    """AI Studio adapter with OpenAI-compatible and native media branches."""

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
        base_url: str,
        openai_adapter: OpenAICompatibleAdapter,
        timeout_seconds: float = 600.0,
    ) -> None:
        """Create an AI Studio dispatcher for one configured base URL."""
        self.base_url = base_url.rstrip("/")
        self.openai_adapter = openai_adapter
        self.timeout_seconds = timeout_seconds

    def uses_native_media(self, request: ProviderRequest) -> bool:
        """Return whether this request must use the native Gemini media path."""
        return request_requires_native_media(request)

    def build_native_payload(self, request: ProviderRequest) -> dict[str, Any]:
        """Build a Gemini-native AI Studio request payload."""
        parts = [
            _native_part(part) for message in request.messages for part in message.parts
        ]
        payload: dict[str, Any] = {"contents": [{"parts": parts}]}
        generation_config: dict[str, Any] = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = gemini_schema(
                inline_schema_refs(request.schema.json_schema)
            )
        if generation_config:
            payload["generationConfig"] = generation_config
        payload.update(dict(request.kwargs))
        return payload

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one synchronous AI Studio request."""
        routed_request = _request_with_inlined_schema(request)
        if not self.uses_native_media(routed_request):
            return self.openai_adapter.execute(routed_request)
        payload = self.build_native_payload(routed_request)
        _log_provider_start(routed_request)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    _native_endpoint(
                        base_url=self.base_url,
                        model=routed_request.provider_model,
                    ),
                    headers=_native_headers(routed_request),
                    json=payload,
                )
        except Exception as exc:
            failure = _transport_failure(request=routed_request, exc=exc)
            _log_provider_failure(request=routed_request, failure=failure)
            raise ProviderError(
                failure,
                routed_request.provider,
                routed_request.model,
                message=failure.message,
            ) from exc
        return _parse_native_response(request=routed_request, response=response)

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one asynchronous AI Studio request."""
        routed_request = _request_with_inlined_schema(request)
        if not self.uses_native_media(routed_request):
            return await self.openai_adapter.aexecute(routed_request)
        payload = self.build_native_payload(routed_request)
        _log_provider_start(routed_request)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    _native_endpoint(
                        base_url=self.base_url,
                        model=routed_request.provider_model,
                    ),
                    headers=_native_headers(routed_request),
                    json=payload,
                )
        except Exception as exc:
            failure = _transport_failure(request=routed_request, exc=exc)
            _log_provider_failure(request=routed_request, failure=failure)
            raise ProviderError(
                failure,
                routed_request.provider,
                routed_request.model,
                message=failure.message,
            ) from exc
        return _parse_native_response(request=routed_request, response=response)


def adapter_from_config(
    config: LLMRouterConfig,
    provider: Provider,
) -> AIStudioAdapter:
    """Build an AI Studio adapter from one config snapshot."""
    if provider is not Provider.AISTUDIO:
        msg = f"Provider '{provider.value}' is not AI Studio."
        raise KeyError(msg)
    provider_spec = config.catalog.providers.get(provider)
    base_url = config.provider_base_urls.get(provider)
    if base_url is None and provider_spec is not None:
        base_url = provider_spec.base_url
    if base_url is None:
        msg = f"Provider '{provider.value}' does not have a configured base URL."
        raise KeyError(msg)
    timeout_seconds = config.policy.attempt_timeout_seconds or 600.0
    return AIStudioAdapter(
        base_url=base_url,
        openai_adapter=openai_adapter_from_config(config, provider),
        timeout_seconds=timeout_seconds,
    )


def request_requires_native_media(request: ProviderRequest) -> bool:
    """Return whether a request contains media owned by the native branch."""
    for message in request.messages:
        for part in message.parts:
            if not isinstance(part, MediaPart):
                continue
            if isinstance(part.media, FileMedia | VideoFileMedia | VideoUrlMedia):
                return True
    return False


def inline_schema_refs(schema: object) -> object:
    """Return a copy of a JSON schema with local `$ref` values inlined."""
    defs = schema.get("$defs") if isinstance(schema, Mapping) else {}
    if not isinstance(defs, Mapping):
        defs = {}
    return _inline_schema_refs(schema, defs=defs)


def _inline_schema_refs(schema: object, *, defs: object) -> object:
    """Recursively inline `$ref` values from a schema object."""
    if isinstance(schema, Mapping):
        ref = schema.get("$ref")
        if isinstance(ref, str) and isinstance(defs, Mapping):
            ref_name = ref.rsplit("/", maxsplit=1)[-1]
            target = defs.get(ref_name)
            if target is not None:
                return _inline_schema_refs(target, defs=defs)
        return {
            key: _inline_schema_refs(value, defs=defs)
            for key, value in schema.items()
            if key != "$defs"
        }
    if isinstance(schema, list):
        return [_inline_schema_refs(item, defs=defs) for item in schema]
    return schema


def _request_with_inlined_schema(request: ProviderRequest) -> ProviderRequest:
    """Inline AI Studio schema refs while preserving the parser contract."""
    if request.schema is None:
        return request
    transformed = with_schema_transform(request.schema, inline_schema_refs)
    return replace(request, schema=transformed)


def _native_part(part: TextPart | MediaPart) -> dict[str, Any]:
    """Translate one normalized part to a Gemini-native HTTP part."""
    if isinstance(part, TextPart):
        return {"text": part.text}
    media = part.media
    if isinstance(media, ImageMedia):
        return {
            "inlineData": {
                "mimeType": "image/png",
                "data": _image_b64(media),
            }
        }
    if isinstance(media, FileMedia):
        path = Path(media.path)
        return {
            "inlineData": {
                "mimeType": media.mime_type or _mime_type(path.name),
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        }
    if isinstance(media, VideoFileMedia):
        path = Path(media.path)
        part_payload: dict[str, Any] = {
            "inlineData": {
                "mimeType": _video_mime_type(path.name),
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        }
        metadata = _video_metadata(
            fps=media.fps,
            start_offset=media.start_offset,
            end_offset=media.end_offset,
        )
        if metadata:
            part_payload["videoMetadata"] = metadata
        return part_payload
    part_payload = {
        "fileData": {
            "mimeType": _video_mime_type(media.url),
            "fileUri": media.url,
        }
    }
    metadata = _video_metadata(
        fps=media.fps,
        start_offset=media.start_offset,
        end_offset=media.end_offset,
    )
    if metadata:
        part_payload["videoMetadata"] = metadata
    return part_payload
    msg = f"Unsupported AI Studio media part: {type(media).__name__}."
    raise TypeError(msg)


def _parse_native_response(
    *,
    request: ProviderRequest,
    response: httpx.Response,
) -> ProviderResult:
    """Parse one native AI Studio HTTP response."""
    if response.status_code >= _HTTP_ERROR_STATUS_MIN:
        failure = _status_failure(request=request, response=response)
        _log_provider_failure(request=request, failure=failure)
        raise ProviderError(
            failure,
            request.provider,
            request.model,
            message=failure.message,
        )
    lines = response.text.splitlines()
    output_text = parse_stream_text(lines)
    usage = normalize_usage({"usageMetadata": parse_usage_metadata(lines)})
    data: dict[str, Any] = {
        "text": output_text,
        "usage": usage.model_dump() if usage is not None else None,
    }
    result = ProviderResult(
        data=data,
        provider=request.provider,
        model=request.model,
        provider_model=request.provider_model,
        output_text=output_text,
        usage=usage,
    )
    logger.info(
        "Provider request completed",
        event_type="llm_router.provider.request.completed",
        **request.log_context(),
    )
    return result


def _log_provider_start(request: ProviderRequest) -> None:
    """Log one native AI Studio request start with safe fields."""
    logger.info(
        "Provider request started",
        event_type="llm_router.provider.request.started",
        **request.log_context(),
    )


def parse_stream_text(lines: list[str]) -> str:
    """Parse Gemini streamed response lines into text."""
    payloads = _parse_stream_payloads(lines)
    texts: list[str] = []
    for payload in payloads:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            continue
        content = candidates[0].get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        texts.extend(
            part["text"]
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    return "".join(texts)


def parse_usage_metadata(lines: list[str]) -> dict[str, int]:
    """Extract Gemini usage metadata from streamed response lines."""
    for payload in reversed(_parse_stream_payloads(lines)):
        usage = payload.get("usageMetadata")
        if isinstance(usage, dict):
            return {
                "promptTokenCount": int(usage.get("promptTokenCount", 0) or 0),
                "candidatesTokenCount": int(usage.get("candidatesTokenCount", 0) or 0),
                "totalTokenCount": int(usage.get("totalTokenCount", 0) or 0),
            }
    return {
        "promptTokenCount": 0,
        "candidatesTokenCount": 0,
        "totalTokenCount": 0,
    }


def _parse_stream_payloads(lines: list[str]) -> list[dict[str, Any]]:
    """Parse SSE or joined JSON Gemini response bodies."""
    sse_payloads: list[dict[str, Any]] = []
    for line in lines:
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(data)
            if isinstance(payload, dict):
                sse_payloads.append(payload)
    if sse_payloads:
        return sse_payloads

    joined = "\n".join(lines).strip()
    with contextlib.suppress(json.JSONDecodeError):
        payload = json.loads(joined)
        if isinstance(payload, dict):
            return [payload]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
    return []


def _status_failure(
    *,
    request: ProviderRequest,
    response: httpx.Response,
) -> ProviderFailure:
    """Build a classified failure from a native HTTP error response."""
    decision = classify_status_code(response.status_code)
    message = _error_message(response.text) or (
        f"Provider returned HTTP {response.status_code}."
    )
    return ProviderFailure(
        provider=request.provider,
        model=request.model,
        message=message,
        retryable=decision.retryable,
        status_code=response.status_code,
        retry_reason=decision.reason,
    )


def _transport_failure(*, request: ProviderRequest, exc: Exception) -> ProviderFailure:
    """Build a classified failure from a native transport exception."""
    decision = classify_exception(exc)
    return ProviderFailure(
        provider=request.provider,
        model=request.model,
        message=preview_exception_message(exc),
        retryable=decision.retryable,
        retry_reason=decision.reason,
    )


def _error_message(text: str) -> str | None:
    """Extract a Gemini error message from a response body."""
    with contextlib.suppress(json.JSONDecodeError):
        payload = json.loads(text)
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            error = item.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"]
    stripped = text.strip()
    return preview_text(stripped) if stripped else None


def _native_endpoint(*, base_url: str, model: str) -> str:
    """Build the Gemini-native stream endpoint from an OpenAI-style base URL."""
    root = _native_root(base_url)
    api_model = model if model.startswith("models/") else f"models/{model}"
    return f"{root}/v1beta/{api_model}:streamGenerateContent"


def _native_root(base_url: str) -> str:
    """Return the Gemini-native root for a configured AI Studio base URL."""
    normalized = base_url.rstrip("/")
    for suffix in ("/v1beta/openai", "/v1/openai", "/v1", "/openai"):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _native_headers(request: ProviderRequest) -> dict[str, str]:
    """Return native AI Studio headers without logging credentials."""
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": request.credential.value,
    }


def _image_b64(media: ImageMedia) -> str:
    """Encode an image as base64 PNG for native inline data."""
    from io import BytesIO

    buffer = BytesIO()
    media.image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _video_metadata(
    *,
    fps: int,
    start_offset: int | None,
    end_offset: int | None,
) -> dict[str, Any]:
    """Build Gemini-native video metadata."""
    metadata: dict[str, Any] = {}
    if fps != 1:
        metadata["fps"] = fps
    if start_offset is not None:
        metadata["startOffset"] = f"{start_offset}s"
    if end_offset is not None:
        metadata["endOffset"] = f"{end_offset}s"
    return metadata


def _mime_type(name: str) -> str:
    """Guess a MIME type with a safe fallback."""
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
