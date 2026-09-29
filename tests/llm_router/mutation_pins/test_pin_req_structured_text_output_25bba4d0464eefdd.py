# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 25bba4d0464eefdd
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

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


class RichObservation(BaseModel):
    scene: str
    vehicle_count: int


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_structured_text_reconstructs_single_line_fenced_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "assurance-credential-value")

    expected_payload = {"scene": "urban traffic", "vehicle_count": 3}
    fenced_content = f"```{json.dumps(expected_payload)}```"

    chat_path = openai_chat_path()
    server_response = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=fenced_content),
    )

    router = LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=Provider.OPENROUTER,
        ),
        temperature=0.0,
    )

    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", chat_path): [server_response]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query(
            "Describe the scene using the requested schema.",
            response_schema=RichObservation,
        )

    assert response.data["parsed"] == expected_payload
    assert response.output_text == fenced_content
