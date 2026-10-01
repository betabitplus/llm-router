# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 594d55ab4bfdf987
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

_EXPECTED_JSON = json.dumps(_EXPECTED)

_UNRECOGNISED_FENCED_BODY = f"```text\n{_EXPECTED_JSON}\n```"


class DockObservation(BaseModel):
    scene: str = Field(description="Short scene label")
    vehicle_count: int = Field(description="Number of vehicles observed")


def _fenced_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_unrecognised_language_fence_still_parses_to_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ```text-fenced reply reaches the parser unchanged and validates."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-assurance-value")
    response_body = openai_success_response(text=_UNRECOGNISED_FENCED_BODY)

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
        response = _fenced_route().query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=DockObservation,
        )

    report = DockObservation.model_validate(parse_json_object(response.output_text))

    assert response.data["parsed"] == _EXPECTED
    assert report.scene == _EXPECTED["scene"]
    assert report.vehicle_count == _EXPECTED["vehicle_count"]
