# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 1045c8ab17c9edbd
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderError,
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

_ARRAY_BODY = json.dumps([3, 5])

_SCHEMA = {
    "type": "object",
    "properties": {
        "scene": {"type": "string"},
        "vehicle_count": {"type": "integer"},
    },
    "required": ["scene", "vehicle_count"],
}


@pytest.fixture
def restored_config():
    original = get_config()
    yield None
    install_config(original)


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_json_array_reply_reports_non_object_error_in_repair_prompt(
    monkeypatch: pytest.MonkeyPatch,
    restored_config: None,
) -> None:
    """A JSON-array reply is rejected with 'must be a JSON object' guidance."""
    assert restored_config is None
    monkeypatch.setenv("QWENCHAT_API_KEY_1", "array-reply-value")
    replies = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=qwen_success_response(text=_ARRAY_BODY),
        )
        for _ in range(3)
    ]
    with ScriptedHTTPServer(
        port=0,
        routes={("POST", _CHAT_PATH): replies},
    ) as server:
        install_worker_provider_base_url(
            provider="qwenchat",
            base_url=f"{server.base_url}/api",
        )
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
        )
        with pytest.raises(ProviderError, match=r"validation failed"):
            router.query(
                "Describe the loading dock scene using the requested schema.",
                response_schema=_SCHEMA,
            )
        recorded = server.recorded_requests("POST", _CHAT_PATH)

    assert len(recorded) >= 2
    repair_body = recorded[1].body.decode("utf-8")
    assert "Structured output must be a JSON object." in repair_body
