# mutation-pin: REQ_PROVIDER_ERROR_BOUNDARY 62fc1baca32629b1
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router import Model
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    openai_chat_path,
    run_retry_worker,
)

pytestmark = pytest.mark.verification_kind("unit")

_OPENAI_PATH = openai_chat_path()
_GOOGLE_PATH = google_generate_path(model=Model.GEMINI_FLASH)
_PRIVATE_ARGUMENTS = '{"note": "provider-private-arguments-boundary"}'


def _openai_unnamed_tool_call_response() -> bytes:
    """Return a normalized 200 body whose tool call omits a required name."""
    return json.dumps(
        {
            "id": "chatcmpl-local",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"arguments": _PRIVATE_ARGUMENTS},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 5,
                "total_tokens": 17,
            },
        }
    ).encode("utf-8")


def _google_unnamed_function_call_response() -> bytes:
    """Return a normalized 200 body whose function call omits a required name."""
    return json.dumps(
        {
            "candidates": [
                {
                    "index": 0,
                    "content": {
                        "role": "model",
                        "parts": [{"functionCall": {"args": {}}}],
                    },
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


@pytest.mark.verifies("REQ_PROVIDER_ERROR_BOUNDARY[revision==1]")
def test_openai_unwrapped_response_failure_becomes_public_provider_error() -> None:
    routes = {
        ("POST", _OPENAI_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=_openai_unnamed_tool_call_response(),
            )
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        result = run_retry_worker(
            case="openai",
            scenario="non_retryable",
            server_base_url=server.base_url,
        )
        request_count = server.request_count("POST", _OPENAI_PATH)

    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert _PRIVATE_ARGUMENTS not in (result.error_message or "")
    assert request_count == 1


@pytest.mark.verifies("REQ_PROVIDER_ERROR_BOUNDARY[revision==1]")
def test_google_unwrapped_response_failure_becomes_public_provider_error() -> None:
    routes = {
        ("POST", _GOOGLE_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=_google_unnamed_function_call_response(),
            )
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        result = run_retry_worker(
            case="google",
            scenario="non_retryable",
            server_base_url=server.base_url,
        )
        request_count = server.request_count("POST", _GOOGLE_PATH)

    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert request_count == 1
