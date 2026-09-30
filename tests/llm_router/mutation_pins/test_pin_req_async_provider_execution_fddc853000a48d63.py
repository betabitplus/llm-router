# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION fddc853000a48d63
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


class ZeroAttempts:
    """Non-int attempt cap that slices to zero routes."""

    def __index__(self) -> int:
        return 0


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_query_with_no_attempt_routes_raises_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("NVIDIA_API_KEY", value)
    cap: Any = ZeroAttempts()
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA),
        max_attempts=cap,
    )

    with pytest.raises(TimeoutError, match=r"No route attempts were available\."):
        asyncio.run(router.aquery("test content prompt"))
