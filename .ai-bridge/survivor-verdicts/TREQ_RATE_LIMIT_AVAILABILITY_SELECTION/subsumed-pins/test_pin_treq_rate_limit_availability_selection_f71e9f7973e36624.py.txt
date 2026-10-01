# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION f71e9f7973e36624
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

from collections.abc import Iterator

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
)
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

# Key 2 is spaced by 0.25 s after a success; key 1 (the lowest id) cools down
# for 2 s after one failure, so on the third request both keys are blocked,
# rotation points back at key 1, and key 2 has the shortest remaining wait.
LIMITS = ProviderLimits(
    rps=4.0,
    rpm=1_000_000.0,
    cooldown_seconds=2.0,
    cooldown_after_failures=1,
)


@pytest.fixture
def local_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[ScriptedHTTPServer]:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-value-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-value-2")
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", openai_chat_path()): [
                    ScriptedResponse(
                        status_code=400,
                        headers={"Content-Type": "application/json"},
                        body=b'{"error":{"message":"cool down key one"}}',
                    ),
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text="served by key 2"),
                    ),
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text="after shortest wait"),
                    ),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        yield server


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_all_blocked_auto_keys_run_shortest_wait_key_not_lowest_id(
    local_server: ScriptedHTTPServer,
) -> None:
    assert local_server is not None
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id="auto",
        ),
        round_robin_start=False,
        shuffle_fallbacks=False,
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={Provider.OPENROUTER: LIMITS},
    )
    with pytest.raises(Exception, match=r"failed for model"):
        router.query("open cooldown on key 1")
    second = router.query("space out key 2")
    third = router.query("both keys blocked")

    assert second.routing_trace[-1].key_id == 2
    assert second.routing_trace[-1].wait_seconds == 0.0
    final = third.routing_trace[-1]
    assert final.key_id == 2
    assert 0.0 < final.wait_seconds <= 0.25
    assert third.output_text == "after shortest wait"
