# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-2093BBD0
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
def test_provider_schema_transform_keeps_legacy_definitions_targets() -> None:
    path = openai_chat_path()
    schema = {
        "title": "order_summary",
        "type": "object",
        "properties": {"item": {"$ref": "#/definitions/Item"}},
        "required": ["item"],
        "definitions": {
            "Item": {
                "type": "object",
                "properties": {"qty": {"type": "integer", "minimum": 1}},
                "required": ["qty"],
            }
        },
    }
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text='{"item": {"qty": 3}}'),
                )
            ]
        },
    ) as server:
        prepare_fault_case(case="aistudio_video", server_base_url=server.base_url)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO)
        )

        response = router.query("Summarize the order.", response_schema=schema)

        body = json.loads(server.recorded_requests("POST", path)[0].body)

    sent = body["response_format"]["json_schema"]["schema"]
    assert sent["properties"]["item"] == {"$ref": "#/definitions/Item"}
    assert sent["definitions"]["Item"]["properties"]["qty"]["minimum"] == 1
    assert json.loads(response.output_text) == {"item": {"qty": 3}}
