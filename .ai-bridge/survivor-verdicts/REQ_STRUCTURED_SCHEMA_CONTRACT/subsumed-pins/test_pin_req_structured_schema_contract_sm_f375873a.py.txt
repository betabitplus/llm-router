# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-F375873A
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

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


class AliasedPayload(BaseModel):
    item_count: int = Field(alias="itemCount")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_pydantic_schema_keeps_alias_and_rebuilds_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sent schema is the model's own, and alias JSON rebuilds the model."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "inventory-assurance-value")
    response_body = openai_success_response(text=json.dumps({"itemCount": 42}))
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _CHAT_PATH): [
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
            response_schema=AliasedPayload,
        )
        recorded = server.recorded_requests("POST", _CHAT_PATH)[0]

    body = json.loads(recorded.body)
    sent = body["response_format"]["json_schema"]["schema"]
    assert sent == AliasedPayload.model_json_schema()
    assert "itemCount" in sent["properties"]
    assert response.data["parsed"] == {"item_count": 42}
