# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 6e9116a1b83a69f4
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

ModelMetaclass = type(BaseModel)


class TextInstanceMeta(ModelMetaclass):
    """Model metaclass that already counts provider text as a model instance."""

    def __instancecheck__(self, instance: object) -> bool:
        return isinstance(instance, str) or super().__instancecheck__(instance)


class Verdict(BaseModel, metaclass=TextInstanceMeta):
    summary: str
    score: int


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_output_already_an_instance_of_requested_model_is_returned_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "schema-contract-value")
    output_text = json.dumps({"summary": "all good", "score": 42})
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", openai_chat_path()): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text=output_text),
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
        response = router.query("Summarise the review.", response_schema=Verdict)

    assert isinstance(output_text, Verdict)
    assert response.output_text == output_text
    assert response.data.get("parsed") == output_text
