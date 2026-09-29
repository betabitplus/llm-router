# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 8a48c40fdfe50bce
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_fallback_trace_records_call_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_nvidia = "NVIDIA_API_KEY"
    value = "mock-provider-auth-12345"
    monkeypatch.setenv(env_nvidia, value)

    router = LLMRouter(
        [
            RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA),
            RouterProfile(model=Model.LLAMA_8B, provider=Provider.NVIDIA),
        ]
    )
    runtime = getattr(router, "_runtime", router)

    simulated_error = RuntimeError("simulated provider call failure")
    call_count = 0

    async def mock_call_async(request: Any, timeout_seconds: Any) -> Any:
        nonlocal call_count
        assert request is not None
        assert timeout_seconds is not None
        call_count += 1
        if call_count == 1:
            raise simulated_error
        return "second-route-ok"

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    captured: dict[str, Any] = {}

    def spy_complete_success(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "final-sentinel"

    monkeypatch.setattr(runtime, "_complete_success", spy_complete_success)

    result = asyncio.run(router.aquery("test content prompt"))

    assert result == "final-sentinel"
    traces = captured["traces"]
    assert len(traces) == 1
    failed_trace = next(iter(traces))
    assert failed_trace.error_type == type(simulated_error).__name__
    assert failed_trace.error_message == str(simulated_error)
