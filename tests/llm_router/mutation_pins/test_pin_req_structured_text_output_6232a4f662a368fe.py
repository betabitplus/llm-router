# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 6232a4f662a368fe
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()
_EXPECTED = {"scene": "loading dock", "vehicle_count": 5}
_EXPECTED_JSON = json.dumps(_EXPECTED)
_FENCED_BODY = f"```json\n{_EXPECTED_JSON}\n```"
_PLAIN_BODY = _EXPECTED_JSON


class DockObservation(BaseModel):
    scene: str = Field(description="Short scene label")
    vehicle_count: int = Field(description="Number of vehicles observed")


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
            "Describe the loading dock scene using the requested schema.",
            response_schema=DockObservation,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_fenced_json_reply_matches_unfenced_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ```json-fenced reply validates against the schema like plain JSON."""
    fenced_response = _query_with_body(monkeypatch, _FENCED_BODY)
    plain_response = _query_with_body(monkeypatch, _PLAIN_BODY)

    fenced_report = DockObservation.model_validate(
        parse_json_object(fenced_response.output_text)
    )
    plain_report = DockObservation.model_validate(
        parse_json_object(plain_response.output_text)
    )

    assert fenced_response.data["parsed"] == _EXPECTED
    assert plain_response.data["parsed"] == _EXPECTED
    assert fenced_report.model_dump() == plain_report.model_dump()
    assert fenced_report.scene == _EXPECTED["scene"]
    assert fenced_report.vehicle_count == _EXPECTED["vehicle_count"]
