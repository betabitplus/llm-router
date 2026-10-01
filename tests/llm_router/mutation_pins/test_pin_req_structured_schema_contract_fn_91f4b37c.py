# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT FN-91F4B37C
# pinned-by: delegate, one pin for 2 pins of _parse_pydantic_model
# kills: 6e9116a1b83a69f4 SM-D49276DB
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
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

ModelMetaclass = type(BaseModel)


class TextInstanceMeta(ModelMetaclass):
    """Model metaclass that already counts provider text as a model instance."""

    def __instancecheck__(self, instance: object) -> bool:
        return isinstance(instance, str) or super().__instancecheck__(instance)


class Verdict(BaseModel, metaclass=TextInstanceMeta):
    summary: str
    score: int


class Requested(BaseModel):
    count: int
    label: str


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_parse_pydantic_model_handles_instances_and_fenced_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "schema-contract-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    output_text = json.dumps({"summary": "all good", "score": 42})
    expected = {"count": 42, "label": "success"}
    reply = (
        "Here is the structured result:\n"
        "```json\n"
        f"{json.dumps(expected)}\n"
        "```\n"
        "End of response."
    )
    routes = {
        ("POST", openai_chat_path()): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=output_text),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=reply),
            ),
        ]
    }
    limits = ProviderLimits(
        rps=1000.0,
        rpm=100000.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=1000,
    )
    with (
        ScriptedHTTPServer(port=0, routes=routes) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
            default_limits=limits,
        )
        response_instance = router.query(
            "Summarise the review.", response_schema=Verdict
        )
        response_fenced = router.query("Report the result.", response_schema=Requested)

    assert response_instance.data.get("parsed") == output_text
    parsed = Requested.model_validate(response_fenced.data["parsed"])
    assert (parsed.count, parsed.label) == (42, "success")
