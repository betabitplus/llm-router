# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 24bb2ffb3a209650
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


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_provider_schema_transform_keeps_schema_name_and_validation() -> None:
    path = openai_chat_path()
    schema = {
        "title": "ticket_summary",
        "type": "object",
        "properties": {"count": {"type": "integer", "minimum": 0}},
        "required": ["count"],
    }
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text='{"count": 2}'),
                )
            ]
        },
    ) as server:
        prepare_fault_case(case="aistudio_video", server_base_url=server.base_url)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO)
        )

        response = router.query("Count the tickets.", response_schema=schema)

        body = json.loads(server.recorded_requests("POST", path)[0].body)

    json_schema = body["response_format"]["json_schema"]
    assert json_schema["name"] == "ticket_summary"
    assert json_schema["schema"]["required"] == ["count"]
    assert json.loads(response.output_text) == {"count": 2}
