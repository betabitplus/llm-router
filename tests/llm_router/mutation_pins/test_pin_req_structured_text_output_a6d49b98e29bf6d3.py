# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT a6d49b98e29bf6d3
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

# Opening fence line carries a trailing space after the json tag. The body
# has no braces or brackets, so only fence stripping exposes the payload.
_FENCED_TRAILING_SPACE_BODY = "```json \n5\n```"


class VehicleCount(RootModel[int]):
    """Bare integer result."""


def _fenced_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-assurance-value")
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
        return _fenced_route().query(
            "How many vehicles are at the dock? Use the requested schema.",
            response_schema=VehicleCount,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_fence_with_trailing_space_unwraps_to_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ```json fence with trailing space validates like plain JSON."""
    response = _query_with_body(monkeypatch, _FENCED_TRAILING_SPACE_BODY)

    assert response.data["parsed"] == _EXPECTED
