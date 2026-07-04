from __future__ import annotations

import json
from dataclasses import replace

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.providers.aistudio import (
    AIStudioAdapter,
    inline_schema_refs,
)
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
    ProviderResult,
)


class CapturingOpenAIAdapter:
    def __init__(self) -> None:
        self.request: ProviderRequest | None = None

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.request = request
        return ProviderResult(
            data={},
            provider=request.provider,
            model=request.model,
            provider_model=request.provider_model,
            output_text="ok",
        )

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.AISTUDIO,
        model=Model.GEMINI_FLASH,
        provider_model="gemini-2.5-flash",
        credential=ProviderCredential(
            key_id=1,
            env_var="AISTUDIO_API_KEY_1",
            value="secret",
        ),
        messages=[normalize_content("hello")],
    )


def test_inline_schema_refs_removes_defs_and_refs() -> None:
    schema = {
        "title": "Reply",
        "$defs": {
            "Answer": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
            }
        },
        "properties": {"answer": {"$ref": "#/$defs/Answer"}},
    }

    resolved = inline_schema_refs(schema)

    encoded = json.dumps(resolved)
    assert "$defs" not in encoded
    assert "$ref" not in encoded
    assert resolved["properties"]["answer"]["properties"]["text"]["type"] == "string"


def test_openai_branch_receives_schema_with_inlined_refs() -> None:
    original = normalize_schema(
        {
            "title": "Reply",
            "$defs": {"Answer": {"type": "string"}},
            "properties": {"answer": {"$ref": "#/$defs/Answer"}},
        }
    )
    fake = CapturingOpenAIAdapter()
    adapter = AIStudioAdapter(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        openai_adapter=fake,
    )

    adapter.execute(replace(_request(), schema=original))

    assert fake.request is not None
    encoded = json.dumps(dict(fake.request.schema.json_schema))
    assert "$defs" not in encoded
    assert "$ref" not in encoded
    assert original.parse({"answer": "ok"}) == {"answer": "ok"}
