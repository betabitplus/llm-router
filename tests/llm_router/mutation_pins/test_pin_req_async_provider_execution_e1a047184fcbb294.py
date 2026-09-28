# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION e1a047184fcbb294
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
    UsageStats,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_execution_first_route_prepare_failure_records_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_nvidia = "NVIDIA_API_KEY"
    env_openai = "OPENAI_API_KEY"
    value = "mock-provider-auth-12345"
    monkeypatch.setenv(env_nvidia, value)
    monkeypatch.setenv(env_openai, value)

    router = LLMRouter(
        [
            RouterProfile(
                model=Model.DEEPSEEK_V4_FLASH,
                provider=Provider.NVIDIA,
            ),
            RouterProfile(
                model=Model.DEEPSEEK_V4_FLASH,
                provider=Provider.NVIDIA,
            ),
        ]
    )
    runtime = getattr(router, "_runtime", router)

    real_prepare = runtime._prepare_request
    failed_once = False

    def mock_prepare_request(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise RuntimeError("Unsupported route capability")
        return real_prepare(*args, **kwargs)

    monkeypatch.setattr(runtime, "_prepare_request", mock_prepare_request)

    async def mock_call_async_with_timeout(
        *_args: Any, **_kwargs: Any
    ) -> LLMRouterResponse:
        return LLMRouterResponse(
            data="normalized text response",
            usage=UsageStats(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
            ),
            provider="nvidia",
            model="deepseek-v4-flash",
            output_text="normalized text response",
        )

    monkeypatch.setattr(
        runtime, "_call_async_with_timeout", mock_call_async_with_timeout
    )

    result = asyncio.run(router.aquery("test content prompt"))

    assert isinstance(result, LLMRouterResponse)
    traces = result.routing_trace
    assert len(traces) == 2
    failed_trace = next(iter(traces))
    final_trace = next(iter(reversed(traces)))
    assert failed_trace.error_type == "RuntimeError"
    assert failed_trace.error_message == "Unsupported route capability"
    assert final_trace.error_type is None
    assert final_trace.error_message is None
