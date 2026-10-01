# mutation-pin: REQ_TOOL_CHOICE SM-B25D86B3
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    google_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_google_genai_sdk

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]")
def test_required_choice_without_tools_asks_google_for_any_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY_1", "local-google-key")
    path = google_generate_path(model=Model.GEMINI_FLASH)
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=google_success_response(text="ok"),
                ),
            ]
        },
    ) as server:
        with patched_google_genai_sdk(server_base_url=server.base_url):
            LLMRouter(
                RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
                temperature=0.0,
                seed=42,
            ).query("Say ok.", tool_choice="required")
        requests = server.recorded_requests("POST", path)

    assert len(requests) == 1
    payload = json.loads(requests[0].body.decode("utf-8"))
    calling = payload["toolConfig"]["functionCallingConfig"]
    assert calling["mode"] == "ANY"
