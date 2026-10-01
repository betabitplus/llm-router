# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT FN-ED3039DC
# pinned-by: delegate, one pin for 2 pins of _pydantic_schema_spec
# kills: SM-008E10B9 SM-F375873A
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field, computed_field

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


class OrderPayload(BaseModel):
    item_count: int = Field(alias="itemCount")

    @computed_field
    def summary_text(self) -> str:
        return f"{self.item_count}"


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_pydantic_schema_validation_mode_and_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_name = "OPENROUTER_API_KEY_1"
    value = "inventory-assurance-value"
    monkeypatch.setenv(env_name, value)
    chat_path = openai_chat_path()
    response_body = openai_success_response(text=json.dumps({"itemCount": 42}))
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", chat_path): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=response_body,
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
            "Count the pallet jacks visible on the shelf.",
            response_schema=OrderPayload,
        )
        recorded = next(iter(server.recorded_requests("POST", chat_path)))

    body = json.loads(recorded.body)
    sent = body["response_format"]["json_schema"]["schema"]
    assert "summary_text" not in sent["properties"]
    assert "itemCount" in sent["properties"]
    assert sent == OrderPayload.model_json_schema()
    assert response.data["parsed"]["item_count"] == 42
