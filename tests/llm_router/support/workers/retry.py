"""Project-specific helpers for retry-focused llm_router tests.

Why:
    Keeps retry e2e scenarios focused on public outcomes instead of repeating
    subprocess orchestration and provider-shaped payload builders in every file.

When to use:
    Use from llm_router retry e2e tests that drive real HTTP clients through a
    local scripted fault server.

How:
    Start a `ScriptedHTTPServer`, then call `run_retry_worker(...)` with the
    case/scenario identifier and assert on the returned `RetryWorkerResult`.
"""

from __future__ import annotations

import json
import os
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from typing import NoReturn

from llm_router import Model
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
    install_worker_provider_base_url,
    patched_gemini_webapi_sdk,
    patched_google_genai_sdk,
    patched_openai_sdk,
)


@dataclass(frozen=True, slots=True)
class RetryWorkerResult:
    """Structured result returned by the retry worker."""

    ok: bool
    output_text: str
    error_type: str | None
    error_message: str | None
    returncode: int
    stdout: str
    stderr: str


def _raise_unknown_retry_case(case: str) -> NoReturn:
    raise ValueError(f"Unknown retry worker case: {case}")


def _required_env_keys_for_case(case: str) -> dict[str, str]:
    env_by_case: dict[str, dict[str, str]] = {
        "openai": {"OPENROUTER_API_KEY_1": "LOCAL_RETRY_KEY"},
        "google": {"GOOGLE_API_KEY_1": "LOCAL_RETRY_KEY"},
        "qwenchat": {"QWENCHAT_API_KEY_1": "LOCAL_RETRY_KEY"},
        "aistudio_nonvideo": {"AISTUDIO_API_KEY_1": "LOCAL_RETRY_KEY"},
        "aistudio_video": {"AISTUDIO_API_KEY_1": "LOCAL_RETRY_KEY"},
        "gemini_webapi": {},
    }
    required = env_by_case.get(case)
    if required is None:
        _raise_unknown_retry_case(case)
    return required


def _patch_context_for_case(
    *, case: str, server_base_url: str
) -> AbstractContextManager[None]:
    if case == "openai":
        return patched_openai_sdk(
            forced_base_url=f"{server_base_url}/v1",
            disable_sdk_retries=True,
        )
    if case == "google":
        return patched_google_genai_sdk(server_base_url=server_base_url)
    if case == "gemini_webapi":
        return patched_gemini_webapi_sdk(server_base_url=server_base_url)
    return nullcontext()


def _install_provider_base_url_overrides(*, case: str, server_base_url: str) -> None:
    overrides: dict[str, tuple[str, str]] = {
        "qwenchat": ("qwenchat", f"{server_base_url}/api"),
        "aistudio_nonvideo": ("aistudio", f"{server_base_url}/v1"),
        "aistudio_video": ("aistudio", f"{server_base_url}/v1"),
    }
    override = overrides.get(case)
    if override is None:
        return
    provider, base_url = override
    install_worker_provider_base_url(provider=provider, base_url=base_url)


def run_retry_worker(
    *,
    case: str,
    scenario: str,
    server_base_url: str,
) -> RetryWorkerResult:
    """Run one retry scenario.

    For speed, retry scenarios run in-process (no subprocess overhead) with
    temporary SDK/config patching that is restored before returning.
    """

    return run_retry_inprocess(
        case=case, scenario=scenario, server_base_url=server_base_url
    )


def run_retry_inprocess(
    *,
    case: str,
    scenario: str,
    server_base_url: str,
) -> RetryWorkerResult:
    """Run one retry scenario in-process (no subprocess overhead)."""
    import tests.llm_router.support.workers.retry_worker as worker
    from llm_router import get_config, install_config
    from tests.llm_router.support.runtime import clear_test_caches

    original_config = get_config()

    required_env_keys = _required_env_keys_for_case(case)

    previous_env: dict[str, str | None] = {
        key: os.environ.get(key) for key in required_env_keys
    }
    for key, value in required_env_keys.items():
        os.environ.setdefault(key, value)

    try:
        clear_test_caches()

        _install_provider_base_url_overrides(case=case, server_base_url=server_base_url)

        if scenario in {"retryable", "retryable_upload", "retryable_api_error"}:
            install_fast_worker_runtime_config()

        with _patch_context_for_case(case=case, server_base_url=server_base_url):
            payload = worker._run_case(case=case, scenario=scenario)
    except Exception as exc:
        payload = {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    finally:
        clear_test_caches()
        install_config(original_config)
        for key, prev_value in previous_env.items():
            if prev_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev_value

    return RetryWorkerResult(
        ok=bool(payload.get("ok")),
        output_text=str(payload.get("output_text", "")),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        returncode=0,
        stdout="",
        stderr="",
    )


def openai_chat_path() -> str:
    """Return the OpenAI-compatible chat completions path."""
    return "/v1/chat/completions"


def qwen_chat_path() -> str:
    """Return the Qwen chat completions path."""
    return "/api/chat/completions"


def qwen_upload_path() -> str:
    """Return the Qwen single-file upload path."""
    return "/api/files/upload"


def google_generate_path(*, model: Model) -> str:
    """Return the native Google GenerateContent path for a public model."""
    model_map = {
        Model.GEMINI_FLASH: "gemini-2.5-flash",
        Model.GEMINI_3_FLASH: "gemini-3-flash-preview",
    }
    api_model = model_map[model]
    return f"/v1beta/models/{api_model}:generateContent"


def aistudio_video_path(*, model: Model) -> str:
    """Return the AI Studio native video path for a public model."""
    model_map = {
        Model.GEMINI_FLASH: "gemini-2.5-flash",
        Model.GEMINI_3_FLASH: "gemini-3-flash-preview",
    }
    api_model = model_map[model]
    return f"/v1beta/models/{api_model}:streamGenerateContent"


def gemini_webapi_google_path() -> str:
    """Return the fake google.com bootstrap path used by gemini_webapi."""
    return "/google"


def gemini_webapi_init_path() -> str:
    """Return the fake init path used by gemini_webapi."""
    return "/app"


def gemini_webapi_generate_path() -> str:
    """Return the fake stream-generate path used by gemini_webapi."""
    return "/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"


def gemini_webapi_batch_path() -> str:
    """Return the fake batch-execute path used by gemini_webapi."""
    return "/_/BardChatUi/data/batchexecute"


def openai_success_response(*, text: str) -> bytes:
    """Return a minimal OpenAI-compatible chat-completion success payload."""
    return json.dumps(
        {
            "id": "chatcmpl-local",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 5,
                "total_tokens": 17,
            },
        }
    ).encode("utf-8")


def openai_error_response(*, status_code: int, message: str) -> bytes:
    """Return a minimal OpenAI-compatible error payload."""
    status_names = {
        400: "bad_request",
        401: "invalid_api_key",
        403: "insufficient_permissions",
        429: "too_many_requests",
        500: "server_error",
        503: "service_unavailable",
    }
    error_types = {
        400: "invalid_request_error",
        401: "authentication_error",
        403: "permission_error",
        429: "rate_limit_error",
        500: "server_error",
        503: "server_error",
    }
    return json.dumps(
        {
            "error": {
                "message": message,
                "type": error_types.get(status_code, "invalid_request_error"),
                "param": None,
                "code": status_names.get(status_code, "unknown_error"),
            }
        }
    ).encode("utf-8")


def google_success_response(*, text: str) -> bytes:
    """Return a minimal Google GenerateContent success payload."""
    return json.dumps(
        {
            "candidates": [
                {
                    "index": 0,
                    "content": {"role": "model", "parts": [{"text": text}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 4,
                "totalTokenCount": 14,
            },
            "modelVersion": "local-model",
        }
    ).encode("utf-8")


def google_error_response(*, status_code: int, message: str) -> bytes:
    """Return a minimal Google API error payload."""
    statuses = {
        400: "INVALID_ARGUMENT",
        401: "UNAUTHENTICATED",
        403: "PERMISSION_DENIED",
        429: "RESOURCE_EXHAUSTED",
        500: "INTERNAL",
        503: "UNAVAILABLE",
        504: "DEADLINE_EXCEEDED",
    }
    return json.dumps(
        {
            "error": {
                "code": status_code,
                "message": message,
                "status": statuses.get(status_code, "UNKNOWN"),
            }
        }
    ).encode("utf-8")


def aistudio_stream_response(*, text: str) -> bytes:
    """Return a native Gemini stream body for AI Studio video retries."""
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                }
            }
        ]
    }
    return (f"data: {json.dumps(payload)}\n\ndata: [DONE]\n\n").encode()


def qwen_success_response(*, text: str) -> bytes:
    """Return a minimal Qwen/OpenAI-compatible success payload."""
    return json.dumps(
        {
            "id": "chatcmpl-qwen-local",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 4,
                "total_tokens": 15,
            },
        }
    ).encode("utf-8")


def qwen_error_response(*, status_code: int, message: str) -> bytes:
    """Return a minimal Qwen proxy error payload."""
    return json.dumps(
        {
            "error": {
                "message": message,
                "status_code": status_code,
            }
        }
    ).encode("utf-8")


def qwen_upload_success_response(*, url: str) -> bytes:
    """Return a minimal Qwen upload success payload."""
    return json.dumps({"file": {"url": url}}).encode("utf-8")


def gemini_webapi_init_response() -> bytes:
    """Return a minimal HTML response containing init tokens."""
    return (
        b'<html><body>"SNlM0e":"local-token","cfb2h":"local-build",'
        b'"FdrFJe":"local-session"</body></html>'
    )


def gemini_webapi_batch_response() -> bytes:
    """Return a minimal successful batch-execute payload."""
    return b"[]"


def gemini_webapi_stream_response(*, text: str) -> bytes:
    """Return a minimal framed stream payload for gemini_webapi."""
    candidate = [None] * 9
    candidate[0] = "rcid-local"
    candidate[1] = [text]
    candidate[8] = [2]

    part_json = [None] * 26
    part_json[1] = ["cid-local", "rid-local", "rcid-local"]
    part_json[4] = [candidate]

    part = [None, None, json.dumps(part_json, separators=(",", ":"))]
    payload = json.dumps([part], separators=(",", ":"))
    framed = f"\n{payload}\n"
    utf16_units = len(framed.encode("utf-16-le")) // 2
    return f"{utf16_units}{framed}".encode()


def gemini_webapi_error_stream_response(*, error_code: int) -> bytes:
    """Return a minimal framed stream payload with one Gemini server error code."""
    part = [
        None,
        None,
        None,
        None,
        None,
        [
            None,
            None,
            [
                [
                    None,
                    [error_code],
                ]
            ],
        ],
    ]
    payload = json.dumps([part], separators=(",", ":"))
    framed = f"\n{payload}\n"
    utf16_units = len(framed.encode("utf-16-le")) // 2
    return f"{utf16_units}{framed}".encode()
