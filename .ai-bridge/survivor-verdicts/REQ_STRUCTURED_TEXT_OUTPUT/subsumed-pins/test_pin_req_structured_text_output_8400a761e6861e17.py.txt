# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 8400a761e6861e17
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

_PADDED_BODY = "\n\n  ```json\n5\n```  \n\n"


class VehicleCount(RootModel[int]):
    """Bare integer structured result."""


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_whitespace_padded_fenced_reply_validates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A padded fenced reply is unwrapped before validation."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-assurance-value")
    route = LLMRouter(
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
                        body=openai_success_response(text=_PADDED_BODY),
                    )
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = route.query(
            "How many vehicles are at the loading dock?",
            response_schema=VehicleCount,
        )

    assert response.data["parsed"] == 5
