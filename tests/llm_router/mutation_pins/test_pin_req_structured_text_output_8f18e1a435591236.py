# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 8f18e1a435591236
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

_OPENAI_PATH = openai_chat_path()
_EXPECTED = {
    "service_name": "payments-api",
    "status": "degraded",
    "error_count": 7,
}


class IncidentSummary(BaseModel):
    service_name: str = Field(description="Service identifier, e.g. payments-api")
    status: str = Field(description="One of: healthy, degraded, down")
    error_count: int


def _fenced_json_body() -> str:
    payload = json.dumps(_EXPECTED)
    return f"```json\n{payload}\n```"


def _fenced_success_response() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=_fenced_json_body()),
    )


def _openai_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_markdown_fenced_json_reply_validates_against_caller_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ```json fenced reply must still parse into the requested schema."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "value")
    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", _OPENAI_PATH): [_fenced_success_response()]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = _openai_route().query(
            "Summarize the incident using the requested schema.",
            response_schema=IncidentSummary,
        )

    parsed = IncidentSummary.model_validate(parse_json_object(response.output_text))
    assert parsed.service_name == _EXPECTED["service_name"]
    assert parsed.status == _EXPECTED["status"]
    assert parsed.error_count == _EXPECTED["error_count"]
    assert response.data["parsed"] == _EXPECTED
