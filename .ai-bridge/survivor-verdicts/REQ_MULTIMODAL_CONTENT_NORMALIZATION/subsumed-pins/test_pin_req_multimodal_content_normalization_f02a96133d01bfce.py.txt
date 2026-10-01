# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION f02a96133d01bfce
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_plain_string_turns_each_reach_provider_as_one_ordered_text_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "neutral-auth-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    path = openai_chat_path()
    reply = "Two sentences about the quarterly report."
    turns = [
        "Read the quarterly report.",
        "Summarize it in two sentences.",
    ]
    routes = {
        ("POST", path): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=reply),
            ),
        ]
    }
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = router.query(turns)
        recorded_requests = server.recorded_requests("POST", path)
        request_count = server.request_count("POST", path)
        server.retain_current_boundary_evidence()

    assert request_count == 1
    assert response.output_text == reply
    body = json.loads(next(iter(recorded_requests)).body)
    assert body["messages"] == [
        {"role": "user", "content": "Read the quarterly report."},
        {"role": "user", "content": "Summarize it in two sentences."},
    ]
