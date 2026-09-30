# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT bfa1905a769a5c06
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
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_EXPECTED = {"vendor": "Acme Supply Co", "line_item_count": 7}

_EXPECTED_JSON = json.dumps(_EXPECTED)

_WRAPPED_BODY = f"Here is the summary:\n```json\n{_EXPECTED_JSON}\n```\nDone."

_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string"},
        "line_item_count": {"type": "integer"},
    },
    "required": ["vendor", "line_item_count"],
    "additionalProperties": False,
}


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "structured-output-check-value")
    response_body = openai_success_response(text=body_text)
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )
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
        return router.query(
            "Summarize the invoice using the requested schema.",
            response_schema=_SCHEMA,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_dict_schema_yields_parsed_object_for_plain_and_wrapped_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plain and wrapped JSON replies yield the real parsed object."""
    plain = _query_with_body(monkeypatch, _EXPECTED_JSON)
    wrapped = _query_with_body(monkeypatch, _WRAPPED_BODY)

    assert plain.data["parsed"] == _EXPECTED
    assert wrapped.data["parsed"] == _EXPECTED
