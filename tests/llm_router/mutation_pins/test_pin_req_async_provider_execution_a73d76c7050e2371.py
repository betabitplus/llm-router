# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION a73d76c7050e2371
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
import dataclasses
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@dataclasses.dataclass
class _DummyAuth:
    key_id: int = 1
    provider: Provider = Provider.NVIDIA


@dataclasses.dataclass
class _DummyRequest:
    key: _DummyAuth = dataclasses.field(default_factory=_DummyAuth)
    route: Any = None
    model: Model = Model.DEEPSEEK_V4_FLASH
    provider: Provider = Provider.NVIDIA


@dataclasses.dataclass
class _DummyResponse:
    output_text: str = "pong"
    data: dict[str, Any] = dataclasses.field(default_factory=dict)
    usage: Any = None
    model: Model = Model.DEEPSEEK_V4_FLASH
    provider: Provider = Provider.NVIDIA


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_execution_records_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_name = "NVIDIA_API_KEY"
    value = "test-auth-value"
    monkeypatch.setenv(env_name, value)

    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    runtime = getattr(router, "_runtime", router)

    record_success_calls: list[dict[str, Any]] = []

    def spy_record_success(
        route: Any = None,
        settings: Any = None,
        request: Any = None,
        **extra: Any,
    ) -> None:
        record_success_calls.append(
            {
                "route": route,
                "settings": settings,
                "request": request,
                "extra": extra,
            }
        )

    monkeypatch.setattr(runtime, "_record_success", spy_record_success)

    def mock_prepare_request(
        request_id: Any,
        route: Any,
        settings: Any,
        content: Any,
    ) -> tuple[_DummyRequest, int]:
        _ = (request_id, settings, content)
        key_obj = _DummyAuth(key_id=1)
        return _DummyRequest(key=key_obj, route=route), 0

    monkeypatch.setattr(runtime, "_prepare_request", mock_prepare_request)

    async def mock_call_async(request: Any, timeout_seconds: Any) -> Any:
        return _DummyResponse(data={"request": request, "timeout": timeout_seconds})

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    def mock_complete_success(
        content: Any = None,
        request_id: Any = None,
        response: Any = None,
        traces: Any = None,
        final_trace: Any = None,
        **extra: Any,
    ) -> Any:
        _ = (content, request_id, traces, final_trace, extra)
        return response

    monkeypatch.setattr(runtime, "_complete_success", mock_complete_success)

    asyncio.run(router.aquery("ping"))

    assert len(record_success_calls) == 1, (
        "Expected _record_success to be called after async execution."
    )
    call_info = record_success_calls[0]
    assert call_info["route"] is not None
    assert call_info["request"] is not None
