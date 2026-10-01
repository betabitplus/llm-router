# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION SM-9B37A894
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


class Sum(BaseModel):
    total: int


def _ok(body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_repair_turn_keeps_assistant_role_for_prior_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "route-credential")
    routes = {
        ("POST", openai_chat_path()): [
            _ok(openai_success_response(text="not json at all")),
            _ok(openai_success_response(text='{"total": 13}')),
        ]
    }
    router = LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        temperature=0.0,
        seed=7,
    )
    original_config = get_config()
    install_fast_worker_runtime_config(structured_output_max_attempts=2)
    try:
        with (
            ScriptedHTTPServer(port=0, routes=routes) as server,
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
        ):
            response = router.query("Add 7 and 6.", response_schema=Sum)
            recorded = server.recorded_requests("POST", openai_chat_path())
            server.retain_current_boundary_evidence()
    finally:
        install_config(original_config)

    assert response.data["parsed"] == {"total": 13}
    assert len(recorded) == 2
    messages = json.loads(recorded[1].body)["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant", "user"]
    assert messages[1]["content"] == "not json at all"
