# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE FN-435B2A95
# pinned-by: delegate, one pin for 4 pins of resolve_effective_settings
# kills: 39cd06b3a9c8bc51 SM-4D75202A bf8a96501e88d45d e238ff65d72c6c1f
from __future__ import annotations

import json

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterError,
    Model,
    Provider,
    RouterProfile,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


@pytest.fixture(autouse=True)
def setup_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for route_id in (1, 2):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{route_id}", f"value-{route_id}")


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_route_policy_defaults_and_router_overrides() -> None:
    path = openai_chat_path()
    headers = {"Content-Type": "application/json"}
    responses = [
        ScriptedResponse(
            status_code=400,
            headers=headers,
            body=openai_error_response(status_code=400, message="first-failed"),
        ),
        ScriptedResponse(
            status_code=200,
            headers=headers,
            body=openai_success_response(text="second-route"),
        ),
    ]
    profiles = [
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id=route_id,
            max_attempts=1,
        )
        for route_id in (1, 2)
    ]
    limited = LLMRouter(
        profiles,
        shuffle_fallbacks=False,
        round_robin_start=False,
    )
    with (
        ScriptedHTTPServer(port=0, routes={("POST", path): responses}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
        pytest.raises(LLMRouterError, match=r"(?s).*"),
    ):
        limited.query("hello")

    widened = LLMRouter(
        profiles,
        max_attempts=2,
        shuffle_fallbacks=False,
        round_robin_start=False,
    )
    with (
        ScriptedHTTPServer(port=0, routes={("POST", path): responses}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
    ):
        response = widened.query("hello")
    assert response.output_text == "second-route"


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_kwargs_precedence_route_router_call() -> None:
    profile = RouterProfile(
        model=Model.DEEPSEEK_V3,
        provider=Provider.OPENROUTER,
        key_id=1,
        max_attempts=1,
        kwargs={
            "user": "route-user",
            "stop": ["route-stop"],
            "logprobs": True,
        },
    )
    router = LLMRouter(
        profile,
        max_attempts=1,
        user="router-user",
        stop=["router-stop"],
        presence_penalty=1.0,
        frequency_penalty=1.0,
        metadata={"tier": "router"},
        shuffle_fallbacks=False,
        round_robin_start=False,
    )
    path = openai_chat_path()
    ok_response = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="done"),
    )
    with (
        ScriptedHTTPServer(port=0, routes={("POST", path): [ok_response]}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router.query(
            "hello",
            user="call-user",
            top_p=0.5,
            logprobs=False,
            frequency_penalty=None,
            metadata={},
        )
        record = next(iter(server.recorded_requests("POST", path)))
        recorded = json.loads(record.body)

    assert recorded.get("presence_penalty") == 1.0
    assert recorded.get("stop") == ["router-stop"]
    assert recorded.get("user") == "call-user"
    assert recorded.get("top_p") == 0.5
    assert recorded.get("logprobs") is False
    assert recorded.get("frequency_penalty") is None
    assert recorded.get("metadata") == {}
