# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 3346a8edbcf6b98d
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object
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

_EXPECTED = {"scene": "loading dock", "vehicle_count": 5}

_INDENTED_JSON = json.dumps(_EXPECTED, indent=2)

_TRUNCATED_FENCE_BODY = f"```json\n{_INDENTED_JSON}"


class DockObservation(BaseModel):
    scene: str = Field(description="Short scene label")
    vehicle_count: int = Field(description="Number of vehicles observed")


def _truncated_fence_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


def _query_with_truncated_fence(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-assurance-value")
    response_body = openai_success_response(text=_TRUNCATED_FENCE_BODY)
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
        return _truncated_fence_route().query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=DockObservation,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_unclosed_json_fence_keeps_closing_brace_in_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ```json fence with no closing marker keeps its closing brace."""
    response = _query_with_truncated_fence(monkeypatch)

    report = DockObservation.model_validate(parse_json_object(response.output_text))

    assert response.data["parsed"] == _EXPECTED
    assert report.model_dump() == _EXPECTED
    assert response.output_text.rstrip().endswith("}")
