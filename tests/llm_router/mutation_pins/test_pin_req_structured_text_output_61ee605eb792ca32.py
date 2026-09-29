# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 61ee605eb792ca32
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

import llm_router
from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_EXECUTOR = "llm_router._internal.runtime.executor"

_EXPECTED = {"scene": "loading dock", "vehicle_count": 5}

_SCHEMA = {
    "type": "object",
    "properties": {
        "scene": {"type": "string"},
        "vehicle_count": {"type": "integer"},
    },
    "required": ["scene", "vehicle_count"],
}


def _public_response_with_text_output(original: Any) -> Any:
    """Serialize a decoded candidate only where the public DTO requires text."""

    def build(result: Any, **kwargs: Any) -> Any:
        text_result = dataclasses.replace(
            result, output_text=json.dumps(result.output_text)
        )
        return original(text_result, **kwargs)

    return build


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_mapping_candidate_is_returned_as_same_mapping_under_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An already-decoded object candidate validates and is returned unchanged."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "mapping-candidate-value")
    monkeypatch.setattr(
        "llm_router._internal.providers.openai_compatible._message_text",
        lambda _message: dict(_EXPECTED),
    )
    original = llm_router._internal.runtime.executor.build_public_response
    monkeypatch.setattr(
        f"{_EXECUTOR}.build_public_response",
        _public_response_with_text_output(original),
    )
    body = openai_success_response(text=json.dumps(_EXPECTED))
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
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
        )
        response = router.query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=_SCHEMA,
        )

    assert response.data["parsed"] == _EXPECTED
    assert isinstance(response.data["parsed"]["scene"], str)
    assert isinstance(response.data["parsed"]["vehicle_count"], int)
