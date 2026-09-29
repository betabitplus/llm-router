# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT SM-C1639EC8
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

_EXPECTED = {"UserName": "ada", " Key ": 2, "itemCount": 3}

_SCHEMA = {
    "type": "object",
    "properties": {
        "UserName": {"type": "string"},
        " Key ": {"type": "integer"},
        "itemCount": {"type": "integer"},
    },
    "required": ["UserName", " Key ", "itemCount"],
    "additionalProperties": False,
}


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
            "Describe the record.",
            response_schema=_SCHEMA,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_mixed_case_and_spaced_keys_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keys keep exact case and whitespace so the caller schema validates."""
    response = _query_with_body(monkeypatch, json.dumps(_EXPECTED))

    assert response.data["parsed"] == _EXPECTED
    assert list(response.data["parsed"]) == list(_EXPECTED)
