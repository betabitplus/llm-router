# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT e9e9444744bf3896
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
    VideoUrlSchema,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import aistudio_video_path
from tests.llm_router.support.workers.worker_patches import (
    install_worker_provider_base_url,
)

pytestmark = pytest.mark.verification_kind("unit")

_PATH = aistudio_video_path(model=Model.GEMINI_FLASH)

_SCHEMA = {
    "type": "object",
    "title": "BudgetReport",
    "$defs": {"budget": {"type": "integer", "minimum": 1}},
    "properties": {"max_tokens": {"$ref": "#/$defs/budget"}},
    "required": ["max_tokens"],
}


def _native_body(text: str) -> bytes:
    event = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    return ("data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n").encode("utf-8")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_provider_schema_transform_returns_spec_with_inlined_schema(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    monkeypatch.setenv("AISTUDIO_API_KEY_1", "local-aistudio-value")
    original = get_config()
    request.addfinalizer(lambda: install_config(original))
    routes = {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                body=_native_body(json.dumps({"max_tokens": 256})),
            )
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        install_worker_provider_base_url(
            provider="aistudio",
            base_url=f"{server.base_url}/v1",
        )
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
            temperature=0.0,
            seed=1,
        )
        response = router.query(
            [
                "Report the budget.",
                VideoUrlSchema(url="https://example.test/clip.mp4", fps=2),
            ],
            response_schema=_SCHEMA,
        )
        recorded = server.recorded_requests("POST", _PATH)

    assert response.data["parsed"] == {"max_tokens": 256}
    body = json.loads(recorded[0].body)
    sent = body["generationConfig"]["responseSchema"]
    assert "$defs" not in sent
    assert sent["properties"]["max_tokens"] == {"type": "INTEGER", "minimum": 1}
    assert sent["required"] == ["max_tokens"]
