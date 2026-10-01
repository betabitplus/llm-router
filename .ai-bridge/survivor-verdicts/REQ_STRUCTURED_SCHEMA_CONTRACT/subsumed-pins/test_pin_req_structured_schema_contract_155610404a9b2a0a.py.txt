# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 155610404a9b2a0a
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()


class AnswerSchema:
    """Holder whose class namespace is a read-only mapping proxy."""

    __slots__ = ()
    type = "object"
    title = "Answer"
    properties = {"answer": {"type": "string", "minLength": 2}}  # noqa: RUF012
    required = ["answer"]  # noqa: RUF012


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_read_only_mapping_schema_is_accepted_and_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = AnswerSchema.__dict__
    value = "read-only-schema-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    body = openai_success_response(text=json.dumps({"answer": "ok"}))
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
        response = router.query("Answer briefly.", response_schema=schema)

    assert response.data["parsed"] == {"answer": "ok"}
