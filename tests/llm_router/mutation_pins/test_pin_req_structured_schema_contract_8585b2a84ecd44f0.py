# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 8585b2a84ecd44f0
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


def _sent_schema_name(schema: dict[str, object]) -> str:
    path = openai_chat_path()
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
        router.query("Count the tickets.", response_schema=schema)
        body = json.loads(server.recorded_requests("POST", path)[0].body)
    return str(body["response_format"]["json_schema"]["name"])


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_untitled_mapping_schema_is_named_from_id_or_default() -> None:
    properties = {"count": {"type": "integer", "minimum": 0}}
    with_id = {
        "$id": "https://example.com/ticket_summary",
        "type": "object",
        "properties": properties,
    }
    neither = {"type": "object", "properties": properties}

    assert _sent_schema_name(with_id) == "https://example.com/ticket_summary"
    assert _sent_schema_name(neither) == "structured_response"
