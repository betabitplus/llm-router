# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 7bb039bcfc778dc9
# pinned-by: claude-opus-5-5
from __future__ import annotations

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

_JSON_HEAD_LINE = '{"scene": "loading dock",'

_JSON_TAIL_LINE = ' "vehicle_count": 5}'

_UNCLOSED_FENCED_BODY = f"```json\n{_JSON_HEAD_LINE}\n{_JSON_TAIL_LINE}"


class DockObservation(BaseModel):
    scene: str = Field(description="Short scene label")
    vehicle_count: int = Field(description="Number of vehicles observed")


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_unclosed_markdown_fence_keeps_trailing_json_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An opened-but-never-closed ```json fence must not lose its last line."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-boundary-value")
    response_body = openai_success_response(text=_UNCLOSED_FENCED_BODY)

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
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
        )
        response = router.query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=DockObservation,
        )

    report = DockObservation.model_validate(parse_json_object(response.output_text))

    assert response.data["parsed"] == _EXPECTED
    assert report.model_dump() == _EXPECTED
    assert report.scene == _EXPECTED["scene"]
    assert report.vehicle_count == _EXPECTED["vehicle_count"]
