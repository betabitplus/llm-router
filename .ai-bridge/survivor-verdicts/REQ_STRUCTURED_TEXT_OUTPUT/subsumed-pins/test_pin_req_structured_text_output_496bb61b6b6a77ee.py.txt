# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 496bb61b6b6a77ee
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import RootModel

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

_ENDPOINT = openai_chat_path()
_FENCED_SCALAR = "```json\n42\n```"


class ScalarMetric(RootModel[int]):
    root: int


def _scripted_scalar_response() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=_FENCED_SCALAR),
    )


def _router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=Provider.OPENROUTER,
        ),
        temperature=0.0,
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_structured_text_scalar_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    env_name = "OPENROUTER_API_KEY_1"
    env_val = "test-scalar-route-auth"
    monkeypatch.setenv(env_name, env_val)

    routes = {("POST", _ENDPOINT): [_scripted_scalar_response()]}
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = _router().query(
                "Return the scalar count.",
                response_schema=ScalarMetric,
            )

        recorded = server.recorded_requests("POST", _ENDPOINT)
        assert len(recorded) == 1

    assert response.output_text == _FENCED_SCALAR
    assert isinstance(response.data, dict)
    if "payload" in response.data:
        assert response.data["payload"] == "42"

    parsed = response.data["parsed"]
    assert parsed == 42 or getattr(parsed, "root", None) == 42
