# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 2f06445af49144cc
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio

import pytest

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_blocked_only_route_waits_instead_of_no_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("NVIDIA_API_KEY", value)
    limits = ProviderLimits(
        rps=10.0, rpm=1000.0, cooldown_seconds=0.05, cooldown_after_failures=1
    )
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA),
        default_limits=limits,
        attempt_timeout_seconds=1.0,
    )

    async def run() -> list[object]:
        first = await asyncio.gather(router.aquery("first"), return_exceptions=True)
        second = await asyncio.gather(router.aquery("second"), return_exceptions=True)
        return [*first, *second]

    results = asyncio.run(run())
    second_result = results[-1]
    assert not (
        isinstance(second_result, TimeoutError)
        and "No route attempts were available" in str(second_result)
    )
