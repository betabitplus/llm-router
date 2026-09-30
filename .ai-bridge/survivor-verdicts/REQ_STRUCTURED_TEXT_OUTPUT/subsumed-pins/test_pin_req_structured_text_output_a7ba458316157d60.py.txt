# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT a7ba458316157d60
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest
from pydantic import RootModel

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_EXPECTED = 5

_BARE_FENCED_BODY = f"```\n{_EXPECTED}\n```"


class VehicleCount(RootModel[int]):
    """Bare integer vehicle count."""


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-assurance-value")
    response_body = openai_success_response(text=body_text)
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )
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
        return router.query(
            "How many vehicles are at the loading dock?",
            response_schema=VehicleCount,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_bare_fence_reply_is_unwrapped_and_validates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A plain ``` fence (no language tag) is stripped from bare JSON."""
    response = _query_with_body(monkeypatch, _BARE_FENCED_BODY)

    parsed = response.data["parsed"]

    assert parsed == _EXPECTED
    assert VehicleCount.model_validate(parsed).root == _EXPECTED
