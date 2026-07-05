"""Gemini WebAPI provider adapter.

Why:
    Owns browser-cookie-backed Gemini WebAPI request translation and preflight
    behavior.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import inspect
import json
import os
import re
import tempfile
import threading
from collections.abc import Callable, Mapping
from io import BytesIO
from pathlib import Path
from typing import Any

from llm_router._api.errors import ProviderError
from llm_router._api.types import Provider
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
from llm_router._internal.capabilities.usage import normalize_usage
from llm_router._internal.config.models import LLMRouterConfig
from llm_router._internal.providers._prompted import (
    build_json_instruction,
    build_tool_instruction,
    json_safe_value,
    parse_prompted_structured_data,
    textual_tool_call_from_text,
)
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.providers.retry import (
    RetryClassification,
    RetryDecision,
    classify_exception,
    classify_status_code,
)
from py_lib_runtime import preview_exception_message
from py_lib_runtime import get_logger

logger = get_logger(__name__)

_DEFAULT_OPERA_COOKIE_FILE = (
    Path.home() / "Library/Application Support/com.operasoftware.Opera/Default/Cookies"
)
_COOKIE_DOMAIN = "google.com"
_COOKIE_CACHE_DIR = (
    Path(tempfile.gettempdir()) / "llm_router_gemini_webapi_cookie_cache"
)
_HTTP_STATUS_MIN = 100
_HTTP_STATUS_MAX = 599
_NON_RETRYABLE_GEMINI_WEBAPI_CODES = frozenset({1060})
_STATUS_TEXT_RE = re.compile(r"\bstatus(?:\s+code)?\s*:\s*(\d{3})\b", re.IGNORECASE)


class GeminiWebAPIAdapter:
    """Adapter for browser-cookie-backed Gemini WebAPI requests."""

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
        runtime_status_func: Callable[[], Mapping[str, object]] | None = None,
        client_builder: Callable[[], object] | None = None,
        init_client_func: Callable[[object, float], object] | None = None,
        init_timeout_seconds: float = 30.0,
    ) -> None:
        """Create a Gemini WebAPI adapter with optional test fakes."""
        self._client = client
        self._runtime_status_func = runtime_status_func or runtime_status
        self._client_builder = client_builder or build_client
        self._init_client_func = init_client_func or _init_client_with_timeout
        self.init_timeout_seconds = init_timeout_seconds
        self._client_lock = threading.RLock()

    def build_prompt_and_files(
        self,
        request: ProviderRequest,
        *,
        temp_dir: Path,
    ) -> tuple[str, list[Path]]:
        """Build Gemini WebAPI prompt text plus local upload file paths."""
        if _uses_textual_tool_prompt(request):
            return _tool_prompt_and_files(request=request, temp_dir=temp_dir)

        prompt_parts: list[str] = []
        if request.schema is not None:
            prompt_parts.append(build_json_instruction(request.schema))

        files: list[Path] = []
        for message in request.messages:
            rendered_text, message_files = _message_prompt_and_files(
                message,
                temp_dir=temp_dir,
            )
            files.extend(message_files)
            if rendered_text:
                prompt_parts.append(rendered_text)
        return "\n\n".join(prompt_parts), files

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one synchronous Gemini WebAPI request."""
        return _run_coro_sync(self.aexecute(request))

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one asynchronous Gemini WebAPI request."""
        _log_provider_start(request)
        try:
            client = await self._client_for(request)
            with tempfile.TemporaryDirectory(
                prefix="llm_router_gemini_webapi_",
            ) as td:
                prompt, files = self.build_prompt_and_files(
                    request,
                    temp_dir=Path(td),
                )
                kwargs: dict[str, object] = {
                    "model": request.provider_model,
                    **dict(request.kwargs),
                }
                if files:
                    kwargs["files"] = files
                response = await _maybe_await(client.generate_content(prompt, **kwargs))
        except ProviderError:
            raise
        except Exception as exc:
            failure = _failure_from_exception(request=request, exc=exc)
            _log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            ) from exc
        return parse_gemini_webapi_response(request=request, response=response)

    async def _client_for(self, request: ProviderRequest) -> Any:  # noqa: ANN401
        """Return a ready client or raise a safe runtime preflight error."""
        with self._client_lock:
            if self._client is not None:
                return self._client
        status = dict(self._runtime_status_func())
        if not status.get("ready"):
            message = str(status.get("reason") or "Gemini WebAPI runtime is not ready.")
            failure = ProviderFailure(
                provider=request.provider,
                model=request.model,
                message=message,
                retryable=False,
                retry_reason="runtime_preflight_failed",
            )
            _log_provider_failure(request=request, failure=failure)
            raise ProviderError(
                failure,
                request.provider,
                request.model,
                message=failure.message,
            )
        logger.info(
            "Provider runtime preflight completed",
            event_type="llm_router.provider.runtime.preflight.completed",
            **request.log_context(),
            has_secure_1psidts=bool(status.get("has_secure_1psidts")),
            has_nid=bool(status.get("has_nid")),
        )
        client = self._client_builder()
        initialized = await _maybe_await(
            self._init_client_func(client, self.init_timeout_seconds)
        )
        _disable_sdk_generate_retry(initialized)
        with self._client_lock:
            if self._client is None:
                self._client = initialized
            return self._client


def adapter_from_config(
    config: LLMRouterConfig,
    provider: Provider,
) -> GeminiWebAPIAdapter:
    """Build a Gemini WebAPI adapter from one config snapshot."""
    if provider is not Provider.GEMINI_WEBAPI:
        msg = f"Provider '{provider.value}' is not Gemini WebAPI."
        raise KeyError(msg)
    timeout_seconds = config.policy.attempt_timeout_seconds or 600.0
    init_timeout_seconds = min(120.0, timeout_seconds)
    return GeminiWebAPIAdapter(init_timeout_seconds=init_timeout_seconds)


def parse_gemini_webapi_response(
    *,
    request: ProviderRequest,
    response: object,
) -> ProviderResult:
    """Parse Gemini WebAPI SDK output into the provider-neutral result port."""
    output_text = str(getattr(response, "text", "") or "").strip()
    parsed = (
        parse_prompted_structured_data(spec=request.schema, text=output_text)
        if request.schema is not None
        else None
    )
    data: dict[str, Any] = {"text": output_text}
    normalized_output_text = output_text
    if parsed is not None:
        parsed_value = json_safe_value(parsed)
        data["parsed"] = parsed_value
        normalized_output_text = json.dumps(parsed_value, ensure_ascii=False)
    usage = normalize_usage(_response_usage(response))
    if usage is not None:
        data["usage"] = usage.model_dump()
    tool_call = textual_tool_call_from_text(
        text=output_text,
        registry=request.tool_registry,
    )
    result = ProviderResult(
        data=data,
        provider=request.provider,
        model=request.model,
        provider_model=request.provider_model,
        output_text=normalized_output_text,
        usage=usage,
        tool_calls=() if tool_call is None else (tool_call,),
    )
    logger.info(
        "Provider request completed",
        event_type="llm_router.provider.request.completed",
        **request.log_context(),
    )
    return result


def opera_cookie_file_path() -> Path:
    """Return the configured Opera cookie database path."""
    override = os.getenv("WORKBENCH_OPERA_COOKIE_FILE") or os.getenv(
        "LLM_ROUTER_OPERA_COOKIE_FILE"
    )
    return (Path(override) if override else _DEFAULT_OPERA_COOKIE_FILE).expanduser()


def cookie_cache_dir() -> Path:
    """Return the SDK cookie-cache directory."""
    return _COOKIE_CACHE_DIR


def cookie_lookup() -> dict[str, str]:
    """Return decrypted google.com cookies for Gemini WebAPI."""
    import browser_cookie3

    cookie_file = opera_cookie_file_path()
    with tempfile.TemporaryDirectory(prefix="llm_router_opera_cookies_") as td:
        copied_cookie_file = Path(td) / "Cookies"
        copied_cookie_file.write_bytes(cookie_file.read_bytes())
        jar = browser_cookie3.opera(
            cookie_file=str(copied_cookie_file),
            domain_name=_COOKIE_DOMAIN,
        )
        return {cookie.name: cookie.value for cookie in jar}


def runtime_status() -> dict[str, object]:
    """Return safe readiness evidence for the local browser-cookie setup."""
    cookie_file = opera_cookie_file_path()
    if not cookie_file.exists():
        return {
            "ready": False,
            "reason": f"Opera Cookies DB not found: {cookie_file}",
        }
    try:
        lookup = cookie_lookup()
    except Exception as exc:
        return {
            "ready": False,
            "reason": f"Opera cookie decryption not available: {exc}",
        }
    if "__Secure-1PSID" not in lookup:
        return {
            "ready": False,
            "reason": "Missing __Secure-1PSID in Opera cookies for google.com",
        }
    return {
        "ready": True,
        "cookie_file": str(cookie_file),
        "cookie_cache_dir": str(_ensure_cookie_cache_dir()),
        "has_secure_1psid": True,
        "has_secure_1psidts": "__Secure-1PSIDTS" in lookup,
        "has_nid": "NID" in lookup,
    }


def build_client() -> object:
    """Build a live Gemini WebAPI client from local browser cookies."""
    from gemini_webapi import GeminiClient

    _ensure_cookie_cache_dir()
    lookup = cookie_lookup()
    client = GeminiClient(
        lookup["__Secure-1PSID"],
        lookup.get("__Secure-1PSIDTS"),
        proxy=None,
    )
    nid = lookup.get("NID")
    if nid:
        with contextlib.suppress(Exception):
            client.cookies.set("NID", nid, domain=".google.com")
    return client


async def init_client(
    client: object,
    *,
    init_timeout_seconds: float = 30.0,
) -> object:
    """Initialize one Gemini WebAPI client with stable runtime settings."""
    await client.init(
        timeout=float(init_timeout_seconds),
        auto_close=False,
        close_delay=300,
        auto_refresh=True,
        verbose=False,
    )
    return client


def _init_client_with_timeout(client: object, init_timeout_seconds: float) -> object:
    """Call the public async initializer through a simple two-argument seam."""
    return init_client(client, init_timeout_seconds=init_timeout_seconds)


def _disable_sdk_generate_retry(client: object) -> None:
    """Keep same-provider retry ownership in the router runtime."""
    generate = getattr(client, "_generate", None)
    wrapped = getattr(generate, "__wrapped__", None)
    if wrapped is None:
        return
    with contextlib.suppress(Exception):
        client._generate = wrapped.__get__(client, type(client))


def _ensure_cookie_cache_dir() -> Path:
    """Ensure the gemini_webapi cookie cache path exists and is configured."""
    configured = os.getenv("GEMINI_COOKIE_PATH")
    if configured:
        return Path(configured).expanduser()
    _COOKIE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["GEMINI_COOKIE_PATH"] = str(_COOKIE_CACHE_DIR)
    return _COOKIE_CACHE_DIR


def _media_prompt_and_files(
    media: ImageMedia | FileMedia | VideoFileMedia | VideoUrlMedia,
    *,
    temp_dir: Path,
) -> tuple[str | None, list[Path]]:
    """Translate media to prompt text and SDK upload file paths."""
    if isinstance(media, ImageMedia):
        buffer = BytesIO()
        media.image.save(buffer, format="PNG")
        content = buffer.getvalue()
        digest = hashlib.sha256(content).hexdigest()[:16]
        path = temp_dir / f"image_{digest}.png"
        path.write_bytes(content)
        return None, [path]
    if isinstance(media, FileMedia | VideoFileMedia):
        return None, [Path(media.path)]
    return media.url, []


def _uses_textual_tool_prompt(request: ProviderRequest) -> bool:
    """Return whether this request uses Gemini WebAPI textual tools."""
    return bool(request.tool_registry is not None and request.tool_registry.tools)


def _tool_prompt_and_files(
    *,
    request: ProviderRequest,
    temp_dir: Path,
) -> tuple[str, list[Path]]:
    """Build the prompt-led tool payload for Gemini WebAPI."""
    if _is_tool_follow_up(request):
        latest_user = _latest_user_message(request)
        if latest_user is None:
            return "", []
        rendered_text, files = _message_prompt_and_files(
            latest_user,
            temp_dir=temp_dir,
        )
        return rendered_text or "", files

    prompt_parts = [
        build_tool_instruction(
            registry=request.tool_registry,
            choice=request.tool_choice,
        )
    ]
    if request.schema is not None:
        prompt_parts.append(build_json_instruction(request.schema))

    task_parts: list[str] = []
    files: list[Path] = []
    for message in request.messages:
        rendered_text, message_files = _message_prompt_and_files(
            message,
            temp_dir=temp_dir,
        )
        files.extend(message_files)
        if rendered_text:
            task_parts.append(rendered_text)
    if task_parts:
        task_text = "\n\n".join(task_parts)
        prompt_parts.append(f"Original task:\n{task_text}")
    return "\n\n".join(prompt_parts), files


def _is_tool_follow_up(request: ProviderRequest) -> bool:
    """Return whether the prompt already carries tool-result context."""
    return any(message.role == "assistant" for message in request.messages)


def _latest_user_message(request: ProviderRequest) -> NormalizedMessage | None:
    """Return the latest user message in a provider request."""
    for message in reversed(request.messages):
        if message.role == "user":
            return message
    return None


def _message_prompt_and_files(
    message: NormalizedMessage,
    *,
    temp_dir: Path,
) -> tuple[str | None, list[Path]]:
    """Render one provider-neutral message into Gemini prompt parts."""
    text_chunks: list[str] = []
    files: list[Path] = []
    for part in message.parts:
        if isinstance(part, TextPart):
            text_chunks.append(part.text)
            continue
        media_text, media_files = _media_prompt_and_files(
            part.media,
            temp_dir=temp_dir,
        )
        if media_text:
            text_chunks.append(media_text)
        files.extend(media_files)
    if not text_chunks:
        return None, files
    rendered_text = "\n\n".join(text_chunks)
    if message.role == "assistant":
        rendered_text = f"Assistant: {rendered_text}"
    return rendered_text, files


def _response_usage(response: object) -> object | None:
    """Return usage metadata from SDK-like objects when available."""
    usage = getattr(response, "usage_metadata", None)
    if usage is not None:
        return usage
    return getattr(response, "usage", None)


def _failure_from_exception(
    *,
    request: ProviderRequest,
    exc: Exception,
) -> ProviderFailure:
    """Build a classified Gemini WebAPI failure from SDK exceptions."""
    provider_code = _provider_error_code(exc)
    if provider_code is not None and provider_code > _HTTP_STATUS_MAX:
        decision = _classify_provider_code(provider_code)
        return ProviderFailure(
            provider=request.provider,
            model=request.model,
            message=preview_exception_message(exc),
            retryable=decision.retryable,
            status_code=provider_code,
            retry_reason=decision.reason,
        )
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


def _provider_error_code(exc: Exception) -> int | None:
    """Extract Gemini WebAPI provider-specific error codes."""
    for attr in ("error_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _exception_status_code(exc: Exception) -> int | None:
    """Extract common HTTP status codes from SDK exceptions."""
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int) and _HTTP_STATUS_MIN <= value <= _HTTP_STATUS_MAX:
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int):
        return value
    match = _STATUS_TEXT_RE.search(str(exc))
    if match is None:
        return None
    status_code = int(match.group(1))
    if _HTTP_STATUS_MIN <= status_code <= _HTTP_STATUS_MAX:
        return status_code
    return None


def _classify_provider_code(error_code: int) -> RetryDecision:
    """Classify Gemini WebAPI stream error codes."""
    if error_code in _NON_RETRYABLE_GEMINI_WEBAPI_CODES:
        return RetryDecision(
            classification=RetryClassification.NON_RETRYABLE,
            reason="gemini_webapi_error_code",
        )
    return RetryDecision(
        classification=RetryClassification.NON_RETRYABLE,
        reason="provider_error_code",
    )


async def _maybe_await(value: object) -> object:
    """Await a value only when it is awaitable."""
    if inspect.isawaitable(value):
        return await value
    return value


def _run_coro_sync(coro: object) -> object:
    """Run one coroutine from sync code, including inside an active event loop."""
    if not inspect.isawaitable(coro):
        return coro
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, object] = {}
    error: dict[str, BaseException] = {}

    def runner() -> None:
        """Run the coroutine in a helper thread and capture its outcome."""
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - passthrough guard
            error["value"] = exc

    thread = threading.Thread(target=runner, name="gemini-webapi-sync", daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error["value"]
    return result.get("value")


def _log_provider_start(request: ProviderRequest) -> None:
    """Log one Gemini WebAPI request start with safe fields."""
    logger.info(
        "Provider request started",
        event_type="llm_router.provider.request.started",
        **request.log_context(),
    )


def _log_provider_failure(
    *,
    request: ProviderRequest,
    failure: ProviderFailure,
) -> None:
    """Log one Gemini WebAPI failure with safe fields."""
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
