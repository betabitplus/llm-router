# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION SM-592318D7
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
@pytest.mark.asyncio
async def test_async_fallback_trace_uses_fallback_route_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("NVIDIA_API_KEY", value)
    monkeypatch.setenv("OPENROUTER_API_KEY", value)

    router = LLMRouter(
        [
            RouterProfile(
                model=Model.DEEPSEEK_V4_FLASH,
                provider=Provider.NVIDIA,
                temperature=0.1,
                seed=11,
            ),
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
                temperature=0.7,
                seed=23,
            ),
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
    )
    runtime = getattr(router, "_runtime", router)
    timeouts: list[Any] = []
    completed: list[Any] = []

    async def fake_call(_request: Any, *, timeout_seconds: Any) -> Any:
        timeouts.append(timeout_seconds)
        if len(timeouts) == 1:
            msg = "first route boom"
            raise RuntimeError(msg)
        return "provider-response"

    def fake_complete(**kwargs: Any) -> Any:
        completed.append(kwargs["final_trace"])
        return "normalized"

    monkeypatch.setattr(runtime, "_call_async_with_timeout", fake_call)
    monkeypatch.setattr(runtime, "_complete_success", fake_complete)

    result = await router.aquery("test content prompt")

    assert result == "normalized"
    assert len(timeouts) == 2
    trace = next(iter(completed))
    assert trace.provider == Provider.OPENROUTER.value
    assert trace.temperature == 0.7
    assert trace.seed == 23
