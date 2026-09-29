# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT a1ecc6333d1910f4
# pinned-by: claude-opus-5-5
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

_EXPECTED = {"name": "Ada", "age": 3}

_BODY = json.dumps(_EXPECTED)

_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
}


def _profile_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_dict_schema_result_preserves_multi_character_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A JSON-schema mapping route returns the exact parsed object."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "route-assurance-value")
    response_body = openai_success_response(text=_BODY)
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
        response = _profile_route().query(
            "Describe the person using the requested schema.",
            response_schema=_SCHEMA,
        )

    assert response.data["parsed"] == _EXPECTED
