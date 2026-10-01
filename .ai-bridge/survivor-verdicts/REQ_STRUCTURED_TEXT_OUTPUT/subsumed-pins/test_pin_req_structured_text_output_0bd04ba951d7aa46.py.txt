# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 0bd04ba951d7aa46
# pinned-by: claude-opus-5-5
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

_EXPECTED = [101, 102]

_PROSE_ARRAY_BODY = "Note: [101, 102]"


class VehicleIds(RootModel[list[int]]):
    """List of vehicle identifiers."""


def _router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    value = "prose-array-assurance-value"
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
        return _router().query(
            "Which vehicles are at the dock? Use the requested schema.",
            response_schema=VehicleIds,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_prose_before_array_unwraps_to_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prose preceding a JSON array unwraps cleanly to the requested schema."""
    response = _query_with_body(monkeypatch, _PROSE_ARRAY_BODY)

    assert response.data["parsed"] == _EXPECTED
