# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 5b5f64ae9f619fd8
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest
from pydantic import RootModel

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

_OPENAI_PATH = openai_chat_path()
_EXPECTED = ["marker_status: closed}", "{marker_scope: internal"]
_EXPECTED_JSON = json.dumps(_EXPECTED)


class TagList(RootModel[list[str]]):
    pass


def _openai_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=Provider.OPENROUTER,
        ),
        temperature=0.0,
    )


def _openai_success() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=_EXPECTED_JSON),
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_structured_text_array_with_inverted_braces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_name = "OPENROUTER_API_KEY_1"
    env_val = "assurance-test-value"
    monkeypatch.setenv(env_name, env_val)

    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", _OPENAI_PATH): [_openai_success()]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = _openai_router().query(
            "Extract audit markers matching the schema.",
            response_schema=TagList,
        )

    assert response.data["parsed"] == _EXPECTED
    assert json.loads(response.output_text) == _EXPECTED
