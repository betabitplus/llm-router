from __future__ import annotations

import json
from pathlib import Path

from llm_router import FileSchema, Model, Provider, VideoSchema, VideoUrlSchema
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.providers.aistudio import AIStudioAdapter
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
    ProviderResult,
)


class FakeOpenAIAdapter:
    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        return ProviderResult(
            data={"branch": "openai"},
            provider=request.provider,
            model=request.model,
            provider_model=request.provider_model,
            output_text="openai",
        )

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


def _request(**overrides: object) -> ProviderRequest:
    values = {
        "request_id": "req-1",
        "provider": Provider.AISTUDIO,
        "model": Model.GEMINI_FLASH,
        "provider_model": "gemini-2.5-flash",
        "credential": ProviderCredential(
            key_id=1,
            env_var="AISTUDIO_API_KEY_1",
            value="secret",
        ),
        "messages": [normalize_content("hello")],
    }
    values.update(overrides)
    return ProviderRequest(**values)


def _adapter(fake: FakeOpenAIAdapter | None = None) -> AIStudioAdapter:
    return AIStudioAdapter(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        openai_adapter=fake or FakeOpenAIAdapter(),
    )


def test_text_requests_use_openai_compatible_branch() -> None:
    fake = FakeOpenAIAdapter()

    result = _adapter(fake).execute(_request())

    assert result.output_text == "openai"
    assert fake.requests[0].messages[0].parts[0].text == "hello"


def test_file_request_uses_native_payload(tmp_path: Path) -> None:
    path = tmp_path / "input.pdf"
    path.write_bytes(b"%PDF local")
    request = _request(
        messages=[
            normalize_content([FileSchema(path=str(path), mime_type="application/pdf")])
        ]
    )
    adapter = _adapter()

    payload = adapter.build_native_payload(request)

    part = payload["contents"][0]["parts"][0]
    assert adapter.uses_native_media(request) is True
    assert part["inlineData"]["mimeType"] == "application/pdf"
    assert part["inlineData"]["data"]


def test_video_url_request_uses_native_payload() -> None:
    request = _request(
        messages=[
            normalize_content(
                [
                    "watch",
                    VideoUrlSchema(
                        url="https://example.test/clip.mp4",
                        fps=2,
                        start_offset=1,
                        end_offset=3,
                    ),
                ]
            )
        ]
    )

    payload = _adapter().build_native_payload(request)

    parts = payload["contents"][0]["parts"]
    assert parts[0] == {"text": "watch"}
    assert parts[1]["fileData"]["fileUri"] == "https://example.test/clip.mp4"
    assert parts[1]["videoMetadata"] == {
        "fps": 2,
        "startOffset": "1s",
        "endOffset": "3s",
    }


def test_default_video_metadata_is_omitted(tmp_path: Path) -> None:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"video")
    request = _request(
        seed=42, messages=[normalize_content(["watch", VideoSchema(path=str(path))])]
    )

    payload = _adapter().build_native_payload(request)

    video_part = payload["contents"][0]["parts"][1]
    assert "videoMetadata" not in video_part
    assert "seed" not in payload.get("generationConfig", {})


def test_native_payload_inlines_schema_refs() -> None:
    schema = normalize_schema(
        {
            "title": "Reply",
            "type": "object",
            "$defs": {"Answer": {"type": "string", "minLength": 2}},
            "properties": {"answer": {"$ref": "#/$defs/Answer"}},
        }
    )
    request = _request(schema=schema)

    payload = _adapter().build_native_payload(request)

    schema_payload = payload["generationConfig"]["responseSchema"]
    assert "$defs" not in json.dumps(schema_payload)
    assert "$ref" not in json.dumps(schema_payload)
    assert schema_payload["properties"]["answer"]["type"] == "STRING"
