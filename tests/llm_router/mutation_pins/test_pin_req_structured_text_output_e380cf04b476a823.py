# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT e380cf04b476a823
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
"""Pin: a non-object JSON reply is reported with the object-type message."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    qwen_chat_path,
    qwen_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = qwen_chat_path()

_EXPECTED = {"scene": "loading dock", "vehicle_count": 5}

_EXPECTED_MESSAGE = "Structured output must be a JSON object."

_SCHEMA = {
    "title": "DockObservation",
    "type": "object",
    "properties": {
        "scene": {"type": "string"},
        "vehicle_count": {"type": "integer"},
    },
    "required": ["scene", "vehicle_count"],
}


def _scripted(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=qwen_success_response(text=text),
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_non_object_json_reply_gets_object_type_repair_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A JSON array reply is flagged as 'must be a JSON object' in the repair."""
    monkeypatch.setenv("QWENCHAT_API_KEY_1", "fence-assurance-value")
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _CHAT_PATH): [
                _scripted("[1, 2, 3]"),
                _scripted(json.dumps(_EXPECTED)),
            ]
        },
    ) as server:
        config = get_config()
        base_urls = dict(config.provider_base_urls)
        base_urls[Provider.QWENCHAT] = f"{server.base_url}/api"
        install_config(
            replace(
                config,
                catalog=replace(config.catalog, provider_base_urls=base_urls),
            )
        )
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
        )
        response = router.query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=_SCHEMA,
        )
        recorded = server.recorded_requests("POST", _CHAT_PATH)

    assert response.data["parsed"] == _EXPECTED
    assert len(recorded) == 2
    repair_body = json.loads(recorded[1].body)
    assert _EXPECTED_MESSAGE in json.dumps(repair_body["messages"])
