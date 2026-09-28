# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 0601f3c62c74bba8
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
import dataclasses
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@dataclasses.dataclass
class MockResponse:
    text: str = "normalized text response"
    traces: tuple[str, ...] = ("blocked_attempt_trace",)


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_execution_blocked_route_returns_response(
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

    real_prepare = runtime._prepare_request

    def mock_prepare_request(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        request, _ = real_prepare(*args, **kwargs)
        return request, 0.5

    monkeypatch.setattr(runtime, "_prepare_request", mock_prepare_request)

    expected = MockResponse()
    called = False

    async def mock_run_blocked_async(*_args: Any, **kwargs: Any) -> Any:
        nonlocal called
        called = True
        assert len(kwargs.get("blocked_requests", [])) == 1
        return expected

    monkeypatch.setattr(runtime, "_run_blocked_async", mock_run_blocked_async)

    result = asyncio.run(router.aquery("test content prompt"))

    assert called is True
    assert result is not None
    assert result == expected
    assert result.text == "normalized text response"
    assert len(result.traces) == 1
