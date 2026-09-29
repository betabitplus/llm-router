# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 745bcea4332c9c50
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_EXPECTED = {"location": "north dock", "sensor_count": 4}

_SCHEMA = {
    "type": "object",
    "properties": {
        "location": {"type": "string"},
        "sensor_count": {"type": "integer"},
    },
    "required": ["location", "sensor_count"],
    "additionalProperties": False,
}


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "route-assurance-value")
    response_body = openai_success_response(text=body_text)
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _CHAT_PATH): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=response_body,
                    )
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
        )
        return router.query(
            "Report the dock sensor reading using the requested schema.",
            response_schema=_SCHEMA,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_mapping_schema_route_returns_decoded_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A JSON-schema mapping route returns the decoded object, plain or fenced."""
    plain = _query_with_body(monkeypatch, json.dumps(_EXPECTED))
    fenced = _query_with_body(monkeypatch, f"```json\n{json.dumps(_EXPECTED)}\n```")

    assert plain.data["parsed"] == _EXPECTED
    assert fenced.data["parsed"] == _EXPECTED
    assert parse_json_object(plain.output_text) == _EXPECTED
    assert parse_json_object(fenced.output_text) == _EXPECTED
