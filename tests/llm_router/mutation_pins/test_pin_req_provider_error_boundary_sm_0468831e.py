# mutation-pin: REQ_PROVIDER_ERROR_BOUNDARY SM-0468831E
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

_BAD_REQUEST = 400


class _StatusCarryingSdkError(Exception):
    """Provider-shaped exception exposing an HTTP status code."""

    status_code = _BAD_REQUEST


def _raise_status_error(_self: object) -> str:
    raise _StatusCarryingSdkError("provider-private-detail-boundary")


@pytest.mark.verifies("REQ_PROVIDER_ERROR_BOUNDARY[revision==1]")
def test_status_carrying_failure_after_sdk_call_becomes_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "google.genai.types.GenerateContentResponse.text",
        property(_raise_status_error),
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
