# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 8faa56db726fb19e
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from llm_router import LLMRouter, Model, Provider, RouterProfile
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

_UNCLOSED_BODY = '```json\n{"scene": "loading dock",\n"vehicle_count": 5}'


class DockObservation(BaseModel):
    scene: str = Field(description="Short scene label")
    vehicle_count: int = Field(description="Number of vehicles observed")


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_unclosed_fence_keeps_last_json_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reply opening a fence without closing it keeps its final line."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-assurance-value")
    response_body = openai_success_response(text=_UNCLOSED_BODY)
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
        response = router.query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=DockObservation,
        )

    assert response.data["parsed"] == _EXPECTED
    report = DockObservation.model_validate(response.data["parsed"])
    assert report.vehicle_count == 5
