# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT dd75771132cecdc4
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_EXPECTED = {"scene": "loading dock", "vehicle_count": 5}

_SCHEMA = {
    "type": "object",
    "properties": {
        "scene": {"type": "string"},
        "vehicle_count": {"type": "integer"},
    },
    "required": ["scene", "vehicle_count"],
}


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_json_object_reply_validates_against_mapping_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A JSON object reply is parsed via a JSON Schema mapping into a dict."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "object-assurance-value")
    body = openai_success_response(text=json.dumps(_EXPECTED))
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
                        body=body,
                    )
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=_SCHEMA,
        )

    assert response.data["parsed"] == _EXPECTED
    assert parse_json_object(response.output_text) == _EXPECTED
