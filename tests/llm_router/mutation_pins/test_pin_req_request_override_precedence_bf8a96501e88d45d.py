# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE bf8a96501e88d45d
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_request_provider_kwargs_override_route_and_router_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "LOCAL_TEST_VALUE")
    path = openai_chat_path()
    ok = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="ok"),
    )
    router = LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=Provider.OPENROUTER,
            kwargs={"max_tokens": 50, "presence_penalty": 0.25},
        ),
        user="router-user",
        metadata={"tier": "router"},
    )
    with (
        ScriptedHTTPServer(port=0, routes={("POST", path): [ok]}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router.query(
            "hello",
            max_tokens=120,
            user="call-user",
            frequency_penalty=0.5,
        )
        payload = json.loads(server.recorded_requests("POST", path)[0].body)

    # Call values win over route (max_tokens) and router (user) kwargs.
    assert payload["max_tokens"] == 120
    assert payload["user"] == "call-user"
    # A request-only provider kwarg reaches the request.
    assert payload["frequency_penalty"] == 0.5
    # Unrelated route and router kwargs survive.
    assert payload["presence_penalty"] == 0.25
    assert payload["metadata"] == {"tier": "router"}
