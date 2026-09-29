# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT d3d06f3ed1c4b9af
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

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
from tests.llm_router.support.workers.worker_patches import (
    install_worker_provider_base_url,
)

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = qwen_chat_path()
_EXPECTED = {"scene": "loading dock", "vehicle_count": 5}


_SCHEMA = {
    "type": "object",
    "title": "DockObservation",
    "properties": {
        "scene": {"type": "string"},
        "vehicle_count": {"type": "integer"},
    },
    "required": ["scene", "vehicle_count"],
}


def _reply(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=qwen_success_response(text=text),
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_non_json_reply_is_reported_as_invalid_json_in_repair_turn(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """A non-JSON reply is rejected as 'not valid JSON' and repaired."""
    monkeypatch.setenv("QWENCHAT_API_KEY_1", "local-qwen-value")
    original = get_config()
    request.addfinalizer(lambda: install_config(original))
    routes = {
        ("POST", _CHAT_PATH): [
            _reply("the dock has five vehicles"),
            _reply(json.dumps(_EXPECTED)),
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        install_worker_provider_base_url(
            provider="qwenchat",
            base_url=f"{server.base_url}/api",
        )
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
            seed=1,
        )
        response = router.query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=_SCHEMA,
        )
        requests = server.recorded_requests("POST", _CHAT_PATH)

    assert response.data["parsed"] == _EXPECTED
    assert len(requests) == 2
    repair_text = requests[1].body.decode("utf-8")
    assert "Structured output is not valid JSON" in repair_text
