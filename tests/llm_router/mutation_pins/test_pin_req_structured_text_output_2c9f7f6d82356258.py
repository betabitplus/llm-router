# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 2c9f7f6d82356258
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

_EXPECTED = {"zone": "north aisle", "crate_count": 7}

_PLAIN_BODY = json.dumps(_EXPECTED)

_FENCED_BODY = f"```json\n{_PLAIN_BODY}\n```"

_SCHEMA = {
    "type": "object",
    "properties": {
        "zone": {"type": "string"},
        "crate_count": {"type": "integer"},
    },
    "required": ["zone", "crate_count"],
    "additionalProperties": False,
}


def _route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "route-formatting-check")
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
        return _route().query(
            "Report the warehouse zone and crate count using the schema.",
            response_schema=_SCHEMA,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_json_string_reply_validates_against_caller_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plain and fenced JSON string replies parse under a mapping schema."""
    plain_response = _query_with_body(monkeypatch, _PLAIN_BODY)
    fenced_response = _query_with_body(monkeypatch, _FENCED_BODY)

    assert parse_json_object(plain_response.output_text) == _EXPECTED
    assert parse_json_object(fenced_response.output_text) == _EXPECTED
    assert plain_response.data is not None
    assert fenced_response.data is not None
