# mutation-pin: REQ_PROVIDER_ERROR_BOUNDARY SM-0C2C0162
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router import Model
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    run_retry_worker,
)

pytestmark = pytest.mark.verification_kind("unit")

_GOOGLE_PATH = google_generate_path(model=Model.GEMINI_FLASH)


def _google_unnamed_function_call_response() -> bytes:
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
def test_provider_error_message_names_provider_before_model() -> None:
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

    assert result.error_type == "ProviderError"
    message = (result.error_message or "").lower()
    model_text = str(Model.GEMINI_FLASH.value).lower()
    assert "google" in message
    assert model_text in message
    assert message.index("google") < message.index(model_text)
