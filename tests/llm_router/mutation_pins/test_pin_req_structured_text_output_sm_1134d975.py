# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT SM-1134D975
# pinned-by: claude-opus-5-5
from __future__ import annotations

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

_EXPECTED: dict[str, object] = {}

_SCHEMA = {
    "type": "object",
}


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    value = "inventory-assurance-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    response_body = openai_success_response(text=body_text)
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
        return router.query(
            "Describe the record.",
            response_schema=_SCHEMA,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_valid_json_wrapped_object_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate wrapped in valid JSON string syntax parses to an object."""
    response = _query_with_body(monkeypatch, '"{}"')

    assert response.data["parsed"] == _EXPECTED
