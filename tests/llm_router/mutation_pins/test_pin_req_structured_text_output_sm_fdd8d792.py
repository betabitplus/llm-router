# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT SM-FDD8D792
# pinned-by: claude-opus-5-5
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

_SCHEMA = {
    "type": "object",
    "properties": {
        "note": {"type": ["string", "null"]},
        "quantity": {"type": "integer"},
    },
    "required": ["note", "quantity"],
    "additionalProperties": False,
}

_EXPECTED = {"note": None, "quantity": 3}


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_null_valued_required_field_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A required nullable field with a null value stays in the result."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "inventory-assurance-value")
    response_body = openai_success_response(text=json.dumps(_EXPECTED))
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
            response_schema=_SCHEMA,
        )

    assert response.data["parsed"] == _EXPECTED
    assert "note" in response.data["parsed"]
