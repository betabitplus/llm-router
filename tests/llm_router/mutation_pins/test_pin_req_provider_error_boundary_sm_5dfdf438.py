# mutation-pin: REQ_PROVIDER_ERROR_BOUNDARY SM-5DFDF438
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import Model
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    google_success_response,
    run_retry_worker,
)

pytestmark = pytest.mark.verification_kind("unit")

_GOOGLE_PATH = google_generate_path(model=Model.GEMINI_FLASH)

_SdkFailure = type(
    "APIError",
    (Exception,),
    {"__module__": "google.genai.errors"},
)


def _raise_sdk_failure(_response: object) -> str:
    raise _SdkFailure("sdk-private-detail-boundary")


@pytest.mark.verifies("REQ_PROVIDER_ERROR_BOUNDARY[revision==1]")
def test_google_sdk_shaped_failure_becomes_public_provider_error_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "google.genai.types.GenerateContentResponse.text",
        property(_raise_sdk_failure),
    )
    routes = {
        ("POST", _GOOGLE_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_success_response(text="ok"),
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
