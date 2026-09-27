# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 3dc1348c54023b59
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_execution_records_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    env_nvidia = "NVIDIA_API_KEY"
    env_openai = "OPENAI_API_KEY"
    value = "mock-provider-auth-12345"
    monkeypatch.setenv(env_nvidia, value)
    monkeypatch.setenv(env_openai, value)

    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    runtime = getattr(router, "_runtime", router)

    record_failure_calls: list[tuple[Any, Exception]] = []

    def spy_record_failure(request: Any, exc: Exception) -> None:
        record_failure_calls.append((request, exc))

    monkeypatch.setattr(runtime, "_record_failure", spy_record_failure)

    simulated_error = RuntimeError("simulated provider failure")

    async def mock_call_async(request: Any, timeout_seconds: Any) -> Any:
        assert request is not None
        assert timeout_seconds is not None
        raise simulated_error

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    with pytest.raises(RuntimeError, match="simulated provider failure"):
        asyncio.run(router.aquery("test content prompt"))

    assert len(record_failure_calls) == 1
    assert record_failure_calls[0][1] is simulated_error
    assert record_failure_calls[0][0] is not None
