# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION 0d1ec285e912ae10
# pinned-by: claude-opus-5-5
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
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text=marker),
                    )
                    for marker in ("A", "B", "C", "D")
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
def test_all_auto_keys_blocked_selects_shortest_wait_without_error(
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
        wait_for_cooldown_if_all_blocked=False,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.2,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    router.query("first")
    router.query("second")
    with pytest.raises(TimeoutError, match=r"All routes are blocked"):
        router.query("third")
