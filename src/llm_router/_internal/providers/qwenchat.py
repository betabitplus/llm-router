"""QwenChat provider adapter.

Why:
    Owns local proxy request execution for QwenChat routes while adjacent
    private modules keep payload and transport helpers small.
"""

from __future__ import annotations

import json
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

from llm_router._api.errors import ProviderError
from llm_router._api.types import Provider
from llm_router._internal.capabilities.media import (
    FileMedia,
    ImageMedia,
    VideoFileMedia,
)
from llm_router._internal.capabilities.usage import normalize_usage
from llm_router._internal.config.models import LLMRouterConfig
from llm_router._internal.providers._prompted import (
    QwenChatMediaUploader as MediaUploader,
    json_safe_value,
    parse_prompted_structured_data,
    qwenchat_amessage_payload,
    qwenchat_combined_initial_message,
    qwenchat_initial_user_prefix,
    qwenchat_message_payload,
    qwenchat_tool_choice_payload as tool_choice_payload,
    qwenchat_uses_textual_tool_prompt as uses_textual_tool_prompt,
    textual_tool_call_from_text,
)
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
from py_lib_runtime import preview_exception_message
from py_lib_runtime import get_logger

__all__ = [
    "QwenChatAdapter",
    "adapter_from_config",
    "encode_multipart_single_file",
    "parse_qwenchat_response",
]

_CHAT_COMPLETIONS_PATH = "/chat/completions"
_FILES_UPLOAD_PATH = "/files/upload"
_HTTP_ERROR_STATUS_MIN = 400
_UPLOAD_BOUNDARY = "llm-router-qwenchat-upload"

logger = get_logger(__name__)


class QwenChatAdapter:
    """HTTP adapter for the local QwenChat proxy."""

    capabilities = ProviderCapabilities(
        supports_images=True,
        supports_files=True,
        supports_video=True,
        supports_json_schema=True,
        supports_tools=True,
    )

    def __init__(self, *, base_url: str, timeout_seconds: float = 600.0) -> None:
        """Create a QwenChat adapter bound to one proxy base URL."""
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def build_payload(
        self,
        request: ProviderRequest,
        *,
        uploader: MediaUploader | None = None,
    ) -> dict[str, Any]:
        """Build a QwenChat completion payload without opening HTTP clients."""
        messages = message_payloads(request=request, uploader=uploader)
        payload: dict[str, Any] = {
            "model": request.provider_model,
            "messages": messages,
            "stream": False,
        }
        if request.temperature is not None:
            payload["temperature"] = float(request.temperature)
        if request.seed is not None:
            payload["seed"] = int(request.seed)
        if request.tool_registry is not None and request.tool_registry.tools:
            payload["tools"] = [
                dict(definition.descriptor)
                for definition in request.tool_registry.tools.values()
            ]
        if request.tool_choice is not None and not uses_textual_tool_prompt(request):
            payload["tool_choice"] = tool_choice_payload(request)
        payload.update(dict(request.kwargs))
        return payload

    async def abuild_payload(
        self,
        request: ProviderRequest,
        *,
        uploader: MediaUploader | None = None,
    ) -> dict[str, Any]:
        """Build a QwenChat completion payload with async media uploads."""
        messages = await amessage_payloads(request=request, uploader=uploader)
        payload: dict[str, Any] = {
            "model": request.provider_model,
            "messages": messages,
            "stream": False,
        }
        if request.temperature is not None:
            payload["temperature"] = float(request.temperature)
        if request.seed is not None:
            payload["seed"] = int(request.seed)
        if request.tool_registry is not None and request.tool_registry.tools:
            payload["tools"] = [
                dict(definition.descriptor)
                for definition in request.tool_registry.tools.values()
            ]
        if request.tool_choice is not None and not uses_textual_tool_prompt(request):
            payload["tool_choice"] = tool_choice_payload(request)
        payload.update(dict(request.kwargs))
        return payload

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one synchronous QwenChat proxy request."""
        log_provider_start(request)
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                payload = self.build_payload(
                    request,
                    uploader=lambda media: upload_media_sync(
                        client=client,
                        request=request,
                        base_url=self.base_url,
                        media=media,
                    ),
                )
                response = client.post(
                    _chat_url(self.base_url),
                    headers=json_headers(request),
                    json=payload,
                )
        except ProviderError:
            raise
        except Exception as exc:
            failure = transport_failure(request=request, exc=exc)
            log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            ) from exc
        return parse_qwenchat_response(
            request=request,
            status_code=response.status_code,
            text=response.text,
        )

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one asynchronous QwenChat proxy request."""
        log_provider_start(request)
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                trust_env=False,
            ) as client:
                payload = await self.abuild_payload(
                    request,
                    uploader=lambda media: upload_media_async(
                        client=client,
                        request=request,
                        base_url=self.base_url,
                        media=media,
                    ),
                )
                response = await client.post(
                    _chat_url(self.base_url),
                    headers=json_headers(request),
                    json=payload,
                )
        except ProviderError:
            raise
        except Exception as exc:
            failure = transport_failure(request=request, exc=exc)
            log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            ) from exc
        return parse_qwenchat_response(
            request=request,
            status_code=response.status_code,
            text=response.text,
        )


def adapter_from_config(config: LLMRouterConfig, provider: Provider) -> QwenChatAdapter:
    """Build a QwenChat adapter from one config snapshot."""
    if provider is not Provider.QWENCHAT:
        msg = f"Provider '{provider.value}' is not QwenChat."
        raise KeyError(msg)
    provider_spec = config.catalog.providers.get(provider)
    base_url = config.provider_base_urls.get(provider)
    if base_url is None and provider_spec is not None:
        base_url = provider_spec.base_url
    if base_url is None:
        msg = f"Provider '{provider.value}' does not have a configured base URL."
        raise KeyError(msg)
    timeout_seconds = config.policy.attempt_timeout_seconds or 600.0
    return QwenChatAdapter(base_url=base_url, timeout_seconds=timeout_seconds)


def _chat_url(base_url: str) -> str:
    """Build the QwenChat chat-completions URL."""
    return f"{base_url.rstrip('/')}{_CHAT_COMPLETIONS_PATH}"


def message_payloads(
    *,
    request: ProviderRequest,
    uploader: MediaUploader | None,
) -> list[dict[str, object]]:
    """Build QwenChat messages, folding initial user instructions when needed."""
    prefix, rest = qwenchat_initial_user_prefix(request.messages)
    messages: list[dict[str, object]] = []
    if prefix and (request.schema is not None or uses_textual_tool_prompt(request)):
        messages.append(
            qwenchat_message_payload(
                request=request,
                message=qwenchat_combined_initial_message(
                    request=request,
                    messages=prefix,
                ),
                uploader=uploader,
                include_schema=False,
            )
        )
    else:
        rest = request.messages
    messages.extend(
        qwenchat_message_payload(
            request=request,
            message=message,
            uploader=uploader,
            include_schema=False,
        )
        for message in rest
    )
    return messages


async def amessage_payloads(
    *,
    request: ProviderRequest,
    uploader: MediaUploader | None,
) -> list[dict[str, object]]:
    """Build async QwenChat messages with the same folding rules."""
    prefix, rest = qwenchat_initial_user_prefix(request.messages)
    messages: list[dict[str, object]] = []
    if prefix and (request.schema is not None or uses_textual_tool_prompt(request)):
        messages.append(
            await qwenchat_amessage_payload(
                request=request,
                message=qwenchat_combined_initial_message(
                    request=request,
                    messages=prefix,
                ),
                uploader=uploader,
                include_schema=False,
            )
        )
    else:
        rest = request.messages
    messages.extend(
        [
            await qwenchat_amessage_payload(
                request=request,
                message=message,
                uploader=uploader,
                include_schema=False,
            )
            for message in rest
        ]
    )
    return messages


def encode_multipart_single_file(
    *,
    filename: str,
    content_type: str,
    content: bytes,
) -> tuple[bytes, str]:
    """Encode one deterministic multipart upload body for QwenChat."""
    boundary = _UPLOAD_BOUNDARY.encode("utf-8")
    crlf = b"\r\n"
    body = crlf.join(
        [
            b"--" + boundary,
            (
                f'Content-Disposition: form-data; name="file"; filename="{filename}"'
            ).encode(),
            f"Content-Type: {content_type}".encode(),
            b"",
            content,
            b"--" + boundary + b"--",
            b"",
        ]
    )
    return body, f"multipart/form-data; boundary={_UPLOAD_BOUNDARY}"


def parse_qwenchat_response(
    *,
    request: ProviderRequest,
    status_code: int,
    text: str,
) -> ProviderResult:
    """Parse a QwenChat HTTP response into the provider-neutral result port."""
    data = _json_mapping(text=text, request=request, status_code=status_code)
    if status_code >= _HTTP_ERROR_STATUS_MIN:
        failure = _status_failure(
            request=request,
            status_code=status_code,
            data=data,
        )
        log_provider_failure(request=request, failure=failure)
        raise ProviderError(
            failure,
            request.provider,
            request.model,
            message=failure.message,
        )

    output_text = _response_text(data)
    parsed = (
        parse_prompted_structured_data(spec=request.schema, text=output_text)
        if request.schema is not None
        else None
    )
    result_data = dict(data)
    normalized_output_text = output_text
    if parsed is not None:
        parsed_value = json_safe_value(parsed)
        result_data["parsed"] = parsed_value
        normalized_output_text = json.dumps(parsed_value, ensure_ascii=False)
    tool_call = textual_tool_call_from_text(
        text=output_text,
        registry=request.tool_registry,
    )
    result = ProviderResult(
        data=result_data,
        provider=request.provider,
        model=request.model,
        provider_model=request.provider_model,
        output_text=normalized_output_text,
        usage=normalize_usage(data.get("usage")),
        tool_calls=() if tool_call is None else (tool_call,),
    )
    logger.info(
        "Provider request completed",
        event_type="llm_router.provider.request.completed",
        **request.log_context(),
    )
    return result


def upload_media_sync(
    *,
    client: httpx.Client,
    request: ProviderRequest,
    base_url: str,
    media: ImageMedia | FileMedia | VideoFileMedia,
) -> str:
    """Upload one sync media item and return the proxy URL."""
    filename, content_type, content = _media_upload_spec(media)
    body, multipart_type = encode_multipart_single_file(
        filename=filename,
        content_type=content_type,
        content=content,
    )
    log_upload_started(request)
    try:
        response = client.post(
            _upload_url(base_url=base_url),
            headers=upload_headers(request, content_type=multipart_type),
            content=body,
        )
    except Exception as exc:
        failure = transport_failure(request=request, exc=exc)
        log_provider_failure(request=request, failure=failure)
        raise ProviderError(
            failure,
            request.provider,
            request.model,
            message=failure.message,
        ) from exc
    return _finish_upload_response(request=request, response=response)


async def upload_media_async(
    *,
    client: httpx.AsyncClient,
    request: ProviderRequest,
    base_url: str,
    media: ImageMedia | FileMedia | VideoFileMedia,
) -> str:
    """Upload one async media item and return the proxy URL."""
    filename, content_type, content = _media_upload_spec(media)
    body, multipart_type = encode_multipart_single_file(
        filename=filename,
        content_type=content_type,
        content=content,
    )
    log_upload_started(request)
    try:
        response = await client.post(
            _upload_url(base_url=base_url),
            headers=upload_headers(request, content_type=multipart_type),
            content=body,
        )
    except Exception as exc:
        failure = transport_failure(request=request, exc=exc)
        log_provider_failure(request=request, failure=failure)
        raise ProviderError(
            failure,
            request.provider,
            request.model,
            message=failure.message,
        ) from exc
    return _finish_upload_response(request=request, response=response)


def json_headers(request: ProviderRequest) -> dict[str, str]:
    """Return QwenChat JSON headers without logging credentials."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if request.credential.value:
        headers["Authorization"] = f"Bearer {request.credential.value}"
    return headers


def upload_headers(
    request: ProviderRequest,
    *,
    content_type: str,
) -> dict[str, str]:
    """Return QwenChat upload headers without logging credentials."""
    headers = {"Content-Type": content_type, "Accept": "application/json"}
    if request.credential.value:
        headers["Authorization"] = f"Bearer {request.credential.value}"
    return headers


def transport_failure(*, request: ProviderRequest, exc: Exception) -> ProviderFailure:
    """Build a classified QwenChat transport failure."""
    decision = classify_exception(exc)
    return ProviderFailure(
        provider=request.provider,
        model=request.model,
        message=preview_exception_message(exc),
        retryable=decision.retryable,
        retry_reason=decision.reason,
    )


def log_provider_start(request: ProviderRequest) -> None:
    """Log one QwenChat request start with safe fields."""
    logger.info(
        "Provider request started",
        event_type="llm_router.provider.request.started",
        **request.log_context(),
    )


def log_upload_started(request: ProviderRequest) -> None:
    """Log one QwenChat upload start with safe fields."""
    logger.info(
        "Provider upload started",
        event_type="llm_router.provider.upload.started",
        **request.log_context(),
    )


def log_provider_failure(
    *,
    request: ProviderRequest,
    failure: ProviderFailure,
) -> None:
    """Log one QwenChat failure with safe fields."""
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


def _media_upload_spec(
    media: ImageMedia | FileMedia | VideoFileMedia,
) -> tuple[str, str, bytes]:
    """Return filename, MIME type, and bytes for one uploadable media value."""
    if isinstance(media, ImageMedia):
        buffer = BytesIO()
        media.image.save(buffer, format="PNG")
        return "image.png", "image/png", buffer.getvalue()
    path = Path(media.path)
    content_type = (
        media.mime_type if isinstance(media, FileMedia) else _video_mime_type(path.name)
    )
    return path.name, content_type or _mime_type(path.name), path.read_bytes()


def _finish_upload_response(
    *,
    request: ProviderRequest,
    response: httpx.Response,
) -> str:
    """Parse one upload response or raise a classified provider error."""
    data = _json_mapping(
        text=response.text,
        request=request,
        status_code=response.status_code,
    )
    if response.status_code >= _HTTP_ERROR_STATUS_MIN:
        failure = _status_failure(
            request=request,
            status_code=response.status_code,
            data=data,
        )
        log_provider_failure(request=request, failure=failure)
        raise ProviderError(
            failure,
            request.provider,
            request.model,
            message=failure.message,
        )
    file_obj = data.get("file")
    file_url = file_obj.get("url") if isinstance(file_obj, dict) else None
    if not isinstance(file_url, str) or not file_url:
        failure = ProviderFailure(
            provider=request.provider,
            model=request.model,
            message="QwenChat upload response did not include file.url.",
            retryable=False,
            status_code=response.status_code,
            retry_reason="invalid_upload_response",
        )
        log_provider_failure(request=request, failure=failure)
        raise ProviderError(
            failure,
            request.provider,
            request.model,
            message=failure.message,
        )
    logger.info(
        "Provider upload completed",
        event_type="llm_router.provider.upload.completed",
        **request.log_context(),
    )
    return file_url


def _json_mapping(
    *,
    text: str,
    request: ProviderRequest,
    status_code: int,
) -> dict[str, Any]:
    """Parse response text as a JSON mapping with safe failure wrapping."""
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        if status_code >= _HTTP_ERROR_STATUS_MIN:
            return {}
        failure = ProviderFailure(
            provider=request.provider,
            model=request.model,
            message="Provider response was not valid JSON.",
            retryable=False,
            status_code=status_code,
            retry_reason="invalid_json_response",
        )
        log_provider_failure(request=request, failure=failure)
        raise ProviderError(
            failure,
            request.provider,
            request.model,
            message=failure.message,
        ) from exc
    if isinstance(data, dict):
        return data
    if status_code >= _HTTP_ERROR_STATUS_MIN:
        return {}
    failure = ProviderFailure(
        provider=request.provider,
        model=request.model,
        message="Provider response JSON must be an object.",
        retryable=False,
        status_code=status_code,
        retry_reason="non_object_json_response",
    )
    log_provider_failure(request=request, failure=failure)
    raise ProviderError(
        failure,
        request.provider,
        request.model,
        message=failure.message,
    )


def _response_text(data: dict[str, Any]) -> str:
    """Extract assistant text from a QwenChat response body."""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content.strip() if isinstance(content, str) else ""


def _upload_url(*, base_url: str) -> str:
    """Build the QwenChat upload URL."""
    return f"{base_url.rstrip('/')}{_FILES_UPLOAD_PATH}"


def _status_failure(
    *,
    request: ProviderRequest,
    status_code: int,
    data: dict[str, Any],
) -> ProviderFailure:
    """Build a classified provider failure from a QwenChat error body."""
    decision = classify_status_code(status_code)
    return ProviderFailure(
        provider=request.provider,
        model=request.model,
        message=_error_message(data) or f"Provider returned HTTP {status_code}.",
        retryable=decision.retryable,
        status_code=status_code,
        retry_reason=decision.reason,
    )


def _error_message(data: dict[str, Any]) -> str | None:
    """Extract a QwenChat error message."""
    error = data.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    if isinstance(data.get("message"), str):
        return str(data["message"])
    return None


def _mime_type(name: str) -> str:
    """Guess a MIME type with a safe fallback."""
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def _video_mime_type(name: str) -> str:
    """Guess a video MIME type with MP4 as fallback."""
    return "video/quicktime" if name.lower().endswith(".mov") else "video/mp4"
