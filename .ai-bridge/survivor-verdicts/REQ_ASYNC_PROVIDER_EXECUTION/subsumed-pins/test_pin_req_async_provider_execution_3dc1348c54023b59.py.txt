# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 3dc1348c54023b59
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
async def test_async_failure_puts_route_into_cooldown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("NVIDIA_API_KEY", value)
    limits = ProviderLimits(
        rps=1000.0,
        rpm=100000.0,
        cooldown_seconds=3600.0,
        cooldown_after_failures=1,
    )
    router = LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V4_FLASH,
            provider=Provider.NVIDIA,
            attempt_timeout_seconds=1e-6,
            wait_for_cooldown_if_all_blocked=False,
            limits_by_provider={Provider.NVIDIA: limits},
        )
    )

    with pytest.raises(Exception, match=r".*") as first:
        await router.aquery("test content prompt")
    with pytest.raises(Exception, match=r".*") as second:
        await router.aquery("test content prompt")

    assert str(first.value) != str(second.value)
