# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE e238ff65d72c6c1f
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import prepare_fault_case

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_router_level_provider_kwargs_reach_request_and_call_wins() -> None:
    path = openai_chat_path()
    ok = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="done"),
    )
    with ScriptedHTTPServer(port=0, routes={("POST", path): [ok, ok]}) as server:
        prepare_fault_case(case="aistudio_video", server_base_url=server.base_url)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
            user="router-user",
            metadata={"tier": "router"},
        )

        router.query("Hello.")
        router.query("Hello again.", user="call-user")

        recorded = server.recorded_requests("POST", path)
        inherited = json.loads(recorded[0].body)
        overridden = json.loads(recorded[1].body)

    assert inherited["user"] == "router-user"
    assert inherited["metadata"] == {"tier": "router"}
    assert overridden["user"] == "call-user"
    assert overridden["metadata"] == {"tier": "router"}
