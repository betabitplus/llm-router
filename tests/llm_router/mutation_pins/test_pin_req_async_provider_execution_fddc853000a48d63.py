# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION fddc853000a48d63
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_execution_no_routes_raises_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_nvidia = "NVIDIA_API_KEY"
    env_openai = "OPENAI_API_KEY"
    value = "mock-provider-auth-12345"
    monkeypatch.setenv(env_nvidia, value)
    monkeypatch.setenv(env_openai, value)

    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    runtime = getattr(router, "_runtime", router)

    def mock_next_attempt_order(*_args: Any, **_kwargs: Any) -> tuple[Any, ...]:
        return ()

    monkeypatch.setattr(runtime, "_next_attempt_order", mock_next_attempt_order)

    with pytest.raises(TimeoutError, match="No route attempts were available"):
        asyncio.run(router.aquery("test content prompt"))
