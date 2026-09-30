# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-07EEEA4D
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
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


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
@pytest.mark.parametrize(
    "schema",
    [
        {"title": "Report", "type": "object", "required": "summary"},
        {"type": "object", "additionalProperties": "yes"},
        {"required": "summary"},
        {"type": "object", "minProperties": -1},
    ],
    ids=[
        "required-not-array",
        "additional-properties-not-schema",
        "required-without-type",
        "negative-min-properties",
    ],
)
def test_invalid_schema_without_properties_is_rejected_before_provider(
    monkeypatch: pytest.MonkeyPatch, schema: dict
) -> None:
    assert "properties" not in schema
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "schema-assurance-value")
    body = openai_success_response(text=json.dumps({"summary": "ok"}))
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
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER)
        )
        with pytest.raises(ValueError, match=r"valid Draft 2020-12 JSON Schema"):
            router.query("Summarize the incident.", response_schema=schema)
