# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT FN-EA3F2437
# pinned-by: delegate, one pin for 6 pins of with_schema_transform
# kills: 24bb2ffb3a209650 SM-2093BBD0 SM-AAB2D195 SM-DD714EDA c8e877b2ede451a3
# kills: e9e9444744bf3896
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
from tests.llm_router.support.workers.retry import (
    aistudio_video_path,
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import (
    install_worker_provider_base_url,
    prepare_fault_case,
)

pytestmark = pytest.mark.verification_kind("unit")


def native_body(text: str) -> bytes:
    event = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    return ("data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n").encode("utf-8")


def scripted(payload: dict[str, object]) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "text/event-stream"},
        body=native_body(json.dumps(payload)),
    )


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_provider_schema_transform_keeps_name_and_definitions() -> None:
    path = openai_chat_path()
    schema = {
        "title": "order_summary",
        "type": "object",
        "properties": {"item": {"$ref": "#/definitions/Item"}},
        "required": ["item"],
        "definitions": {
            "Item": {
                "type": "object",
                "properties": {"qty": {"type": "integer", "minimum": 1}},
                "required": ["qty"],
            }
        },
    }
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text='{"item": {"qty": 3}}'),
                )
            ]
        },
    ) as server:
        prepare_fault_case(case="aistudio_video", server_base_url=server.base_url)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO)
        )

        response = router.query("Summarize the order.", response_schema=schema)

        request_record = next(iter(server.recorded_requests("POST", path)))
        body = json.loads(request_record.body)

    json_schema = body["response_format"]["json_schema"]
    sent = json_schema["schema"]
    assert json_schema["name"] == "order_summary"
    assert sent["properties"]["item"] == {"$ref": "#/definitions/Item"}
    assert sent["definitions"]["Item"]["properties"]["qty"]["minimum"] == 1
    assert json.loads(response.output_text) == {"item": {"qty": 3}}


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_provider_transformed_schema_is_what_the_provider_receives() -> None:
    path = openai_chat_path()
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ticket_summary",
        "type": "object",
        "$defs": {
            "Ticket": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "exclusiveMinimum": 0},
                    "kind": {"const": "bug"},
                },
                "required": ["count", "kind"],
            }
        },
        "properties": {
            "ticket": {"$ref": "#/$defs/Ticket"},
            "note": {
                "anyOf": [
                    {"type": "string", "maxLength": 40},
                    {"type": "null"},
                ]
            },
        },
        "required": ["ticket"],
    }
    text = '{"ticket": {"count": 2, "kind": "bug"}, "note": null}'
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text=text),
                )
            ]
        },
    ) as server:
        prepare_fault_case(case="aistudio_video", server_base_url=server.base_url)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO)
        )

        response = router.query("Summarise the ticket.", response_schema=schema)

        request_record = next(iter(server.recorded_requests("POST", path)))
        body = json.loads(request_record.body)

    json_schema = body["response_format"]["json_schema"]
    assert json_schema["name"] == "ticket_summary"
    assert "ticket" in json_schema["schema"]["required"]
    assert json_schema["schema"] != schema
    assert json.loads(response.output_text) == json.loads(text)


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_provider_schema_transform_keeps_composition_and_nested_constraints(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    env_name = "AISTUDIO_API_KEY_1"
    env_value = "local-aistudio-value"
    monkeypatch.setenv(env_name, env_value)
    original = get_config()
    request.addfinalizer(lambda: install_config(original))
    video_path = aistudio_video_path(model=Model.GEMINI_FLASH)
    schema = {
        "type": "object",
        "title": "LevelReport",
        "$defs": {"level": {"type": "string", "enum": ["low", "high"]}},
        "properties": {"level": {"$ref": "#/$defs/level"}},
        "allOf": [{"properties": {"note": {"type": "string", "minLength": 1}}}],
        "required": ["level", "note"],
        "minProperties": 1,
    }
    routes = {
        ("POST", video_path): [
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
            response_schema=schema,
        )
        recorded = server.recorded_requests("POST", video_path)

    assert response.data["parsed"] == {"level": "high", "note": "stable signal"}
    assert len(recorded) == 2
    for entry in recorded:
        sent = json.loads(entry.body)["generationConfig"]["responseSchema"]
        assert sent["required"] == ["level", "note"]
        assert sent["minProperties"] == 1
        assert sent["properties"]["level"]["enum"] == ["low", "high"]
        composed = next(iter(sent["allOf"]))
        assert composed["properties"]["note"] == {
            "type": "STRING",
            "min_length": 1,
        }
