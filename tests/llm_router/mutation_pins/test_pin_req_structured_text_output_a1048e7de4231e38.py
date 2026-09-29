# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT a1048e7de4231e38
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


class DockObservation(RootModel[int]):
    """Vehicle count reported as a bare JSON integer."""


def _route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


def _query_with_body(monkeypatch: pytest.MonkeyPatch, body_text: str):
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-uppercase-assurance-value")
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
        return _route().query(
            "Describe the loading dock scene using the requested schema.",
            response_schema=DockObservation,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_uppercase_json_fence_matches_lowercase_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ```JSON-fenced reply validates like a ```json-fenced one."""
    lower_response = _query_with_body(monkeypatch, "```json\n7\n```")
    upper_response = _query_with_body(monkeypatch, "```JSON\n7\n```")

    assert lower_response.data["parsed"] == 7
    assert upper_response.data["parsed"] == 7
