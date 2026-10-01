# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT da7a8951ef012c23
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
@pytest.mark.parametrize("schema", [int, dict, str], ids=["int", "dict", "str"])
def test_non_pydantic_class_schema_is_rejected_with_type_error(
    monkeypatch: pytest.MonkeyPatch, schema: type
) -> None:
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
        with pytest.raises(
            TypeError,
            match=r"response_schema must be a Pydantic model type or JSON schema",
        ):
            router.query("Summarize the incident.", response_schema=schema)
