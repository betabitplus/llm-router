# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION e92263fea0939fa2
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

from collections.abc import Iterator

import pytest

from llm_router import (
    KeyId,
    LLMRouter,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
)
from llm_router._internal.runtime.limiter import KeyResolver
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
                    for marker in ("A", "B")
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
def test_explicit_blocked_key_is_kept_without_availability_scan(
    local_server: ScriptedHTTPServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert local_server is not None
    scanned: list[KeyId] = []
    scan = KeyResolver.candidates

    def recording_scan(
        self: KeyResolver,
        *,
        provider: Provider,
        key_id: KeyId,
    ) -> object:
        scanned.append(key_id)
        return scan(self, provider=provider, key_id=key_id)

    monkeypatch.setattr(KeyResolver, "candidates", recording_scan)
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id=1,
        ),
        round_robin_start=False,
        shuffle_fallbacks=False,
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=5.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    first = router.query("first")
    # Key 1 is now blocked for about 0.2 s while key 2 was never used.
    second = router.query("second")
    assert first.routing_trace[-1].key_id == 1
    assert first.routing_trace[-1].wait_seconds == 0.0
    assert second.routing_trace[-1].key_id == 1
    assert second.routing_trace[-1].wait_seconds > 0.0
    assert second.output_text == "B"
    # An explicit key is not subject to the automatic availability scan.
    assert scanned == []
