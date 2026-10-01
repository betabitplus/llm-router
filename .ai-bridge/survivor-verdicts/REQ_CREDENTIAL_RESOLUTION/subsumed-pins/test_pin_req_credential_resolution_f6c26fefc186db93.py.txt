# mutation-pin: REQ_CREDENTIAL_RESOLUTION f6c26fefc186db93
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_key_rotation_is_ascending_round_robin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for number in (1, 2, 3):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{number}", f"value-{number}")
    path = openai_chat_path()
    responses = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=openai_success_response(text=marker),
        )
        for marker in ("A", "B", "C", "D")
    ]
    with (
        ScriptedHTTPServer(port=0, routes={("POST", path): responses}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router = LLMRouter(
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id="auto",
            ),
            limits_by_provider={
                Provider.OPENROUTER: ProviderLimits(
                    rps=0.0,
                    rpm=0.0,
                    cooldown_seconds=0.0,
                    cooldown_after_failures=0,
                )
            },
        )
        used = [router.query("hello").routing_trace[-1].key_id for _ in range(4)]

    assert used == [1, 2, 3, 1]
