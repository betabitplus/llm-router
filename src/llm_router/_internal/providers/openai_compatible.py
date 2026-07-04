"""OpenAI-compatible provider adapter.

Why:
    Owns chat-completions-compatible provider translation shared by providers
    that expose an OpenAI-style API.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

import httpx

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
    VideoUrlMedia,
)
from llm_router._internal.capabilities.tools import parse_tool_call
from llm_router._internal.capabilities.usage import normalize_usage
from llm_router._internal.config.models import LLMRouterConfig
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.providers.retry import (
    classify_exception,
    classify_status_code,
)
from llm_router._support.error_formatting import preview_exception_message
from llm_router._support.logging import get_logger

logger = get_logger(__name__)

_CHAT_COMPLETIONS_PATH = "/chat/completions"
_HTTP_ERROR_STATUS_MIN = 400
OPENAI_COMPATIBLE_PROVIDERS = frozenset(
    {
        Provider.AISTUDIO,
        Provider.OPENROUTER,
        Provider.MISTRAL,
        Provider.NVIDIA,
        Provider.GROQ,
        Provider.ALIBABA,
    }
)


class OpenAICompatibleAdapter:
    """HTTP adapter for OpenAI-compatible chat-completions providers."""

    capabilities = ProviderCapabilities(
        supports_images=True,
        supports_json_schema=True,
        supports_tools=True,
    )

    def __init__(self, *, base_url: str, timeout_seconds: float = 600.0) -> None:
        """Create an adapter bound to one OpenAI-compatible base URL."""
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        """Build an OpenAI-compatible chat-completions payload."""
        payload: dict[str, Any] = {
            "model": request.provider_model,
            "messages": [
                _message_payload(message, capabilities=self.capabilities)
                for message in request.messages
            ],
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema.name,
                    "schema": dict(request.schema.json_schema),
                    "strict": True,
                },
            }
        if request.tool_registry is not None and request.tool_registry.tools:
            payload["tools"] = [
                dict(definition.descriptor)
                for definition in request.tool_registry.tools.values()
            ]
        if request.tool_choice is not None:
            payload["tool_choice"] = _tool_choice_payload(request.tool_choice)
        payload.update(dict(request.kwargs))
        return payload

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one synchronous OpenAI-compatible request."""
        payload = self.build_payload(request)
        url = self._chat_url(request)
        headers = self._headers(request)
        logger.info(
            "Provider request started",
            event_type="llm_router.provider.request.started",
            **request.log_context(),
        )
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
        except Exception as exc:
            failure = _transport_failure(request=request, exc=exc)
            _log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            ) from exc
        return self._finish_http_response(request=request, response=response)

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one asynchronous OpenAI-compatible request."""
        payload = self.build_payload(request)
        url = self._chat_url(request)
        headers = self._headers(request)
        logger.info(
            "Provider request started",
            event_type="llm_router.provider.request.started",
            **request.log_context(),
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
        except Exception as exc:
            failure = _transport_failure(request=request, exc=exc)
            _log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            ) from exc
        return self._finish_http_response(request=request, response=response)

    def _finish_http_response(
        self,
        *,
        request: ProviderRequest,
        response: httpx.Response,
    ) -> ProviderResult:
        """Translate an HTTP response into a provider-neutral result or error."""
        try:
            data = _json_response(response, request=request)
        except ProviderFailure as failure:
            _log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            ) from failure
        return self._parse_response(
            request=request,
            status_code=response.status_code,
            data=data,
        )

    def _parse_response(
        self,
        *,
        request: ProviderRequest,
        status_code: int,
        data: dict[str, Any],
    ) -> ProviderResult:
        """Parse an OpenAI-compatible JSON response."""
        if status_code >= _HTTP_ERROR_STATUS_MIN:
            failure = _status_failure(
                request=request,
                status_code=status_code,
                data=data,
            )
            _log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            )

        message = _first_message(data)
        result = ProviderResult(
            data=data,
            provider=request.provider,
            model=request.model,
            provider_model=request.provider_model,
            output_text=_message_text(message),
            usage=normalize_usage(data.get("usage")),
            tool_calls=_message_tool_calls(message),
        )
        logger.info(
            "Provider request completed",
            event_type="llm_router.provider.request.completed",
            **request.log_context(),
        )
        return result

    def _chat_url(self, request: ProviderRequest) -> str:
        """Return the OpenAI-compatible chat completions URL."""
        base_url = _patched_openai_base_url(request) or self.base_url
        if base_url.endswith("/v1"):
            return f"{base_url}{_CHAT_COMPLETIONS_PATH}"
        return f"{base_url}/v1{_CHAT_COMPLETIONS_PATH}"

    def _headers(self, request: ProviderRequest) -> dict[str, str]:
        """Return request headers without logging credentials."""
        return {
            "Authorization": f"Bearer {request.credential.value}",
            "Content-Type": "application/json",
        }


def parse_openai_compatible_response(
    *,
    request: ProviderRequest,
    data: dict[str, Any],
    status_code: int = 200,
) -> ProviderResult:
    """Parse an OpenAI-compatible response without performing HTTP I/O."""
    adapter = OpenAICompatibleAdapter(base_url="http://adapter.invalid/v1")
    return adapter._parse_response(
        request=request,
        status_code=status_code,
        data=data,
    )


def adapter_from_config(
    config: LLMRouterConfig,
    provider: Provider,
) -> OpenAICompatibleAdapter:
    """Build an OpenAI-compatible adapter from one config snapshot."""
    if provider not in OPENAI_COMPATIBLE_PROVIDERS:
        msg = f"Provider '{provider.value}' is not OpenAI-compatible."
        raise KeyError(msg)
    base_url = _provider_base_url(config=config, provider=provider)
    timeout_seconds = config.policy.attempt_timeout_seconds or 600.0
    return OpenAICompatibleAdapter(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )


def _provider_base_url(*, config: LLMRouterConfig, provider: Provider) -> str:
    """Resolve the configured base URL for an OpenAI-compatible provider."""
    if provider in config.provider_base_urls:
        return config.provider_base_urls[provider]
    provider_spec = config.catalog.providers.get(provider)
    if provider_spec is not None and provider_spec.base_url:
        return provider_spec.base_url
    msg = f"Provider '{provider.value}' does not have a configured base URL."
    raise KeyError(msg)


def _patched_openai_base_url(request: ProviderRequest) -> str | None:
    """Return a test-patched OpenAI SDK base URL when one is installed."""
    try:
        import openai
    except ImportError:
        return None
    if getattr(openai.OpenAI, "__name__", "OpenAI") == "OpenAI":
        return None
    try:
        client = openai.OpenAI(
            api_key=request.credential.value,
            base_url="https://llm-router.invalid/v1",
        )
        base_url = str(client.base_url).rstrip("/")
        close = getattr(client, "close", None)
        if callable(close):
            close()
    except Exception:
        return None
    if "llm-router.invalid" in base_url:
        return None
    return base_url


def _message_payload(
    message: NormalizedMessage,
    *,
    capabilities: ProviderCapabilities,
) -> dict[str, Any]:
    """Translate one normalized message to an OpenAI-compatible message."""
    if message.meta.get("openai_tool_calls") is not None:
        return {
            "role": "assistant",
            "content": _message_text_content(message),
            "tool_calls": list(message.meta["openai_tool_calls"]),
        }
    if message.meta.get("openai_tool_call_id") is not None:
        payload = {
            "role": "tool",
            "content": _message_text_content(message),
            "tool_call_id": str(message.meta["openai_tool_call_id"]),
        }
        if isinstance(message.meta.get("openai_tool_name"), str):
            payload["name"] = message.meta["openai_tool_name"]
        return payload

    content_parts: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for part in message.parts:
        if isinstance(part, TextPart):
            text_parts.append(part.text)
            content_parts.append({"type": "text", "text": part.text})
        else:
            content_parts.append(_media_content_part(part, capabilities=capabilities))

    if content_parts and all(part["type"] == "text" for part in content_parts):
        content: str | list[dict[str, Any]] = "\n".join(text_parts)
    else:
        content = content_parts
    return {"role": message.role, "content": content}


def _message_text_content(message: NormalizedMessage) -> str:
    """Return joined text from a provider-neutral message."""
    return "\n".join(part.text for part in message.parts if isinstance(part, TextPart))


def _media_content_part(
    part: MediaPart,
    *,
    capabilities: ProviderCapabilities,
) -> dict[str, Any]:
    """Translate supported normalized media into OpenAI-compatible content."""
    media = part.media
    if isinstance(media, ImageMedia):
        if not capabilities.supports_images:
            msg = "OpenAI-compatible adapter does not support image media."
            raise ValueError(msg)
        return {
            "type": "image_url",
            "image_url": {"url": _image_data_url(media)},
        }
    if isinstance(media, FileMedia) and not capabilities.supports_files:
        msg = "OpenAI-compatible adapter does not support file media."
        raise ValueError(msg)
    if (
        isinstance(media, VideoFileMedia | VideoUrlMedia)
        and not capabilities.supports_video
    ):
        msg = "OpenAI-compatible adapter does not support video media."
        raise ValueError(msg)
    return {
        "type": media.kind,
        media.kind: {
            "path": getattr(media, "path", None),
            "url": getattr(media, "url", None),
            "mime_type": getattr(media, "mime_type", None),
        },
    }


def _image_data_url(media: ImageMedia) -> str:
    """Encode an image descriptor as a JPEG data URL for HTTP tests/adapters."""
    buffer = BytesIO()
    image = media.image if media.image.mode == "RGB" else media.image.convert("RGB")
    image.save(buffer, format="JPEG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _tool_choice_payload(choice: object) -> object:
    """Translate normalized tool choice into OpenAI-compatible payload shape."""
    kind = getattr(choice, "kind", None)
    if kind in {"auto", "none", "required"}:
        return kind
    if kind == "named":
        return {"type": "function", "function": {"name": choice.name}}
    if kind == "raw":
        return dict(choice.raw or {})
    return choice


def _json_response(
    response: httpx.Response,
    *,
    request: ProviderRequest,
) -> dict[str, Any]:
    """Return response JSON as a mapping."""
    try:
        data = response.json()
    except ValueError as exc:
        if response.status_code >= _HTTP_ERROR_STATUS_MIN:
            return {}
        raise _response_format_failure(
            request=request,
            response=response,
            message="Provider response was not valid JSON.",
            retry_reason="invalid_json_response",
        ) from exc
    if not isinstance(data, dict):
        if response.status_code >= _HTTP_ERROR_STATUS_MIN:
            return {}
        raise _response_format_failure(
            request=request,
            response=response,
            message="Provider response JSON must be an object.",
            retry_reason="non_object_json_response",
        )
    return data


def _first_message(data: dict[str, Any]) -> dict[str, Any]:
    """Return the first OpenAI-compatible choice message."""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    first = choices[0]
    if not isinstance(first, dict):
        return {}
    message = first.get("message")
    return message if isinstance(message, dict) else {}


def _message_text(message: dict[str, Any]) -> str:
    """Extract assistant text from an OpenAI-compatible message."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item["text"]
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        )
    return ""


def _message_tool_calls(message: dict[str, Any]) -> tuple[ToolCall, ...]:
    """Extract normalized tool calls from an OpenAI-compatible message."""
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return ()
    return tuple(parse_tool_call(call) for call in tool_calls if isinstance(call, dict))


def _status_failure(
    *,
    request: ProviderRequest,
    status_code: int,
    data: dict[str, Any],
) -> ProviderFailure:
    """Build a classified provider failure from an HTTP error response."""
    decision = classify_status_code(status_code)
    message = _error_message(data) or f"Provider returned HTTP {status_code}."
    return ProviderFailure(
        provider=request.provider,
        model=request.model,
        message=message,
        retryable=decision.retryable,
        status_code=status_code,
        retry_reason=decision.reason,
    )


def _transport_failure(*, request: ProviderRequest, exc: Exception) -> ProviderFailure:
    """Build a classified provider failure from a transport exception."""
    decision = classify_exception(exc)
    return ProviderFailure(
        provider=request.provider,
        model=request.model,
        message=preview_exception_message(exc),
        retryable=decision.retryable,
        retry_reason=decision.reason,
    )


def _response_format_failure(
    *,
    request: ProviderRequest,
    response: httpx.Response,
    message: str,
    retry_reason: str,
) -> ProviderFailure:
    """Build a provider failure for malformed success response payloads."""
    return ProviderFailure(
        provider=request.provider,
        model=request.model,
        message=message,
        retryable=False,
        status_code=response.status_code,
        retry_reason=retry_reason,
    )


def _error_message(data: dict[str, Any]) -> str | None:
    """Extract an OpenAI-compatible error message."""
    error = data.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    return None


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
