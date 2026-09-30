# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE SM-4D75202A
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
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
def test_falsy_call_provider_kwarg_overrides_route_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "LOCAL_TEST_VALUE")
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="ok"),
                )
            ]
            * 2
        },
    ) as server:
        router = LLMRouter(
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
                kwargs={"logprobs": True, "max_tokens": 50},
            ),
        )
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            router.query("hello")
            router.query("hello", logprobs=False)

        recorded = server.recorded_requests("POST", path)
        omitted = json.loads(recorded[0].body)
        explicit = json.loads(recorded[1].body)
        assert omitted["logprobs"] is True
        assert explicit["logprobs"] is False
        assert explicit["max_tokens"] == 50
