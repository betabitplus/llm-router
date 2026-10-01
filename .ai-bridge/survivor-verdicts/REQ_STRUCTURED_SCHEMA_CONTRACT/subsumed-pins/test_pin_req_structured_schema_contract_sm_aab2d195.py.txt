# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-AAB2D195
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
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

VIDEO_PATH = aistudio_video_path(model=Model.GEMINI_FLASH)

# "note" is required at the top level but only declared through allOf, so it
# is absent from the top-level "properties" mapping.
REPORT_SCHEMA = {
    "type": "object",
    "title": "LevelReport",
    "properties": {"level": {"type": "string", "enum": ["low", "high"]}},
    "allOf": [{"properties": {"note": {"type": "string", "minLength": 1}}}],
    "required": ["level", "note"],
}


def native_body(text: str) -> bytes:
    event = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    return ("data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n").encode("utf-8")


def scripted(payload: dict[str, str]) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "text/event-stream"},
        body=native_body(json.dumps(payload)),
    )


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_provider_schema_transform_keeps_required_declared_via_composition(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    monkeypatch.setenv("AISTUDIO_API_KEY_1", "local-aistudio-value")
    original = get_config()
    request.addfinalizer(lambda: install_config(original))
    routes = {
        ("POST", VIDEO_PATH): [
            scripted({"level": "high"}),
            scripted({"level": "high", "note": "stable signal"}),
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
                "Report the level with a short note.",
                VideoUrlSchema(url="https://example.test/clip.mp4", fps=2),
            ],
            response_schema=REPORT_SCHEMA,
        )
        recorded = server.recorded_requests("POST", VIDEO_PATH)

    # Router-side validation rejected the first output lacking "note" and
    # accepted only the repaired one.
    assert response.data["parsed"] == {"level": "high", "note": "stable signal"}
    assert len(recorded) == 2
    for entry in recorded:
        sent = json.loads(entry.body)["generationConfig"]["responseSchema"]
        assert sent["required"] == ["level", "note"]
        composed = next(iter(sent["allOf"]))
        assert composed["properties"]["note"] == {"type": "STRING", "min_length": 1}
