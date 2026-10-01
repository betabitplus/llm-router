# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT a57b176468930694
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_EXPECTED = {"scene": "night market alley", "vehicle_count": 3}

_EXPECTED_JSON = json.dumps(_EXPECTED)

_INDENTED_JSON = json.dumps(_EXPECTED, indent=2)

_CLOSED_FENCE_BODY = f"```json\n{_EXPECTED_JSON}\n```"

_UNCLOSED_FENCE_BODY = f"```json\n{_INDENTED_JSON}"


class NightMarketObservation(BaseModel):
    scene: str = Field(description="Short scene label")
    vehicle_count: int = Field(description="Number of vehicles observed")


def _observation_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "brace-recovery-value")
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
        return _observation_route().query(
            "Describe the alley scene using the requested schema.",
            response_schema=NightMarketObservation,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_unterminated_json_fence_still_recovers_full_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ```json fence missing its closing marker keeps its final line.

    The brace-based extraction that runs after fence stripping can only
    recover the full JSON object if the opening ```json line was left
    untouched when no closing fence is present. This pins that the last
    line of the reply (the JSON object's closing brace) is preserved and
    that a properly closed fence still yields the identical structured
    result, so provider-specific fencing never leaks into the public
    structured output.
    """
    unclosed_response = _query_with_body(monkeypatch, _UNCLOSED_FENCE_BODY)
    closed_response = _query_with_body(monkeypatch, _CLOSED_FENCE_BODY)

    unclosed_report = NightMarketObservation.model_validate(
        unclosed_response.data["parsed"]
    )
    closed_report = NightMarketObservation.model_validate(
        closed_response.data["parsed"]
    )

    assert unclosed_response.data["parsed"] == _EXPECTED
    assert closed_response.data["parsed"] == _EXPECTED
    assert unclosed_report.model_dump() == closed_report.model_dump()
    assert unclosed_report.vehicle_count == _EXPECTED["vehicle_count"]
