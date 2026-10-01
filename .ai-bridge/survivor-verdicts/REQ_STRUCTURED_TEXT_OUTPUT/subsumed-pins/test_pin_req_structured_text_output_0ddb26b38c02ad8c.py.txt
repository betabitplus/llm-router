# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 0ddb26b38c02ad8c
# pinned-by: claude-opus-5-5
from __future__ import annotations

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
from tests.llm_router.support.workers.worker_patches import (
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")

_OPENAI_PATH = openai_chat_path()
_EXPECTED_ITEMS = ["service-api", "worker-queue"]
_CHATTER_RESPONSE = '["service-api", "worker-queue"] finished :}'


class TaskList(RootModel[list[str]]):
    root: list[str]


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
        body=openai_success_response(text=_CHATTER_RESPONSE),
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_structured_text_array_payload_with_trailing_brace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_var = "OPENROUTER_API_KEY_1"
    value = "test-provider-credential"
    monkeypatch.setenv(env_var, value)
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
            "Return the service list.",
            response_schema=TaskList,
        )

    assert response.data["parsed"] == _EXPECTED_ITEMS
