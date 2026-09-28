# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 4185d08c0ebf67fe
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_execution_defers_pacing_wait_under_one_second(
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

    routes = runtime._next_attempt_order(
        settings=runtime._settings_for_first_route(call_overrides={})
    )
    route = routes[0]

    def mock_attempt_order(*, settings: Any) -> tuple[Any, ...]:
        assert settings is not None
        return (route, route)

    monkeypatch.setattr(runtime, "_next_attempt_order", mock_attempt_order)

    prepared_requests: list[Any] = []
    original_prepare = runtime._prepare_request

    def mock_prepare(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        req, _ = original_prepare(*args, **kwargs)
        prepared_requests.append(req)
        wait_seconds = 0.5 if len(prepared_requests) == 1 else 0.0
        return req, wait_seconds

    monkeypatch.setattr(runtime, "_prepare_request", mock_prepare)

    called_requests: list[Any] = []

    async def mock_call_async(request: Any, timeout_seconds: Any) -> Any:
        assert timeout_seconds is not None
        called_requests.append(request)
        return "mock-response-data"

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    complete_calls: list[dict[str, Any]] = []

    def mock_complete_success(*args: Any, **kwargs: Any) -> Any:
        assert not args
        complete_calls.append(kwargs)
        return "mock-success-response"

    monkeypatch.setattr(runtime, "_complete_success", mock_complete_success)

    result = asyncio.run(router.aquery("test content prompt"))

    assert result == "mock-success-response"
    assert len(prepared_requests) == 2
    assert called_requests == [prepared_requests[1]]
    assert len(complete_calls) == 1
    assert len(complete_calls[0]["traces"]) == 1
