# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT c8e877b2ede451a3
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import prepare_fault_case

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_provider_transformed_schema_is_what_the_provider_receives() -> None:
    path = openai_chat_path()
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ticket_summary",
        "type": "object",
        "$defs": {
            "Ticket": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "exclusiveMinimum": 0},
                    "kind": {"const": "bug"},
                },
                "required": ["count", "kind"],
            }
        },
        "properties": {
            "ticket": {"$ref": "#/$defs/Ticket"},
            "note": {
                "anyOf": [
                    {"type": "string", "maxLength": 40},
                    {"type": "null"},
                ]
            },
        },
        "required": ["ticket"],
    }
    text = '{"ticket": {"count": 2, "kind": "bug"}, "note": null}'
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text=text),
                )
            ]
        },
    ) as server:
        prepare_fault_case(case="aistudio_video", server_base_url=server.base_url)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO)
        )

        response = router.query("Summarise the ticket.", response_schema=schema)

        body = json.loads(server.recorded_requests("POST", path)[0].body)

    json_schema = body["response_format"]["json_schema"]
    assert json_schema["name"] == "ticket_summary"
    assert "ticket" in json_schema["schema"]["required"]
    assert json_schema["schema"] != schema
    assert json.loads(response.output_text) == json.loads(text)
