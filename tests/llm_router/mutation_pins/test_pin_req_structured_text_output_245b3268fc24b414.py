# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 245b3268fc24b414
# pinned-by: claude-opus-5-5
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

_CHAT_PATH = openai_chat_path()

_EXPECTED = {"item": "pallet jack", "quantity": 3}

_SCHEMA = {
    "type": "object",
    "properties": {
        "item": {"type": "string"},
        "quantity": {"type": "integer"},
    },
    "required": ["item", "quantity"],
    "additionalProperties": False,
}

_PLAIN_BODY = json.dumps(_EXPECTED)

_FENCED_BODY = f"Here you go:\n```json\n{_PLAIN_BODY}\n```"


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "inventory-assurance-value")
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
            "Count the pallet jacks visible on the shelf.",
            response_schema=_SCHEMA,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_string_json_reply_validates_against_dict_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plain and fenced string replies yield the same dict under a dict schema."""
    plain_response = _query_with_body(monkeypatch, _PLAIN_BODY)
    fenced_response = _query_with_body(monkeypatch, _FENCED_BODY)

    assert plain_response.data["parsed"] == _EXPECTED
    assert fenced_response.data["parsed"] == _EXPECTED
