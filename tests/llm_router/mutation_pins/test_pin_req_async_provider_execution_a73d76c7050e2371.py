# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION a73d76c7050e2371
# pinned-by: claude-opus-5-5: The mutant removes `_record_success` from the async success path. The response to the current request stays the same, but the success of the route and key is never recorded. That affects health state, cooldown recovery and quota accounting, so later async requests are routed differently than sync on
from __future__ import annotations

import asyncio
import dataclasses
from typing import Any

import pytest
from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@dataclasses.dataclass
class _DummyKey:
    key_id: int = 1
    provider: Provider = Provider.NVIDIA


@dataclasses.dataclass
class _DummyRequest:
    key: _DummyKey = dataclasses.field(default_factory=_DummyKey)
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
def test_async_execution_records_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-12345")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")

    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    runtime = getattr(router, "_runtime", router)

    record_success_calls: list[dict[str, Any]] = []
    original_record_success = runtime._record_success

    def spy_record_success(*args: Any, **kwargs: Any) -> Any:
        route = kwargs.get("route") if "route" in kwargs else (args[0] if len(args) > 0 else None)
        settings = kwargs.get("settings") if "settings" in kwargs else (args[1] if len(args) > 1 else None)
        request = kwargs.get("request") if "request" in kwargs else (args[2] if len(args) > 2 else None)
        record_success_calls.append({
            "route": route,
            "settings": settings,
            "request": request,
        })
        try:
            return original_record_success(*args, **kwargs)
        except Exception:
            return None

    monkeypatch.setattr(runtime, "_record_success", spy_record_success)

    orig_prepare_request = runtime._prepare_request

    def safe_prepare_request(
        request_id: Any, route: Any, settings: Any, content: Any
    ) -> Any:
        try:
            req, _ = orig_prepare_request(
                request_id=request_id,
                route=route,
                settings=settings,
                content=content,
            )
            return (req, 0)
        except Exception:
            key = getattr(route, "key", None)
            key_id = 1
            if key is not None and isinstance(getattr(key, "key_id", None), int):
                key_id = key.key_id
            dummy_key = _DummyKey(key_id=key_id)
            return (_DummyRequest(key=dummy_key, route=route), 0)

    monkeypatch.setattr(runtime, "_prepare_request", safe_prepare_request)

    async def mock_call_async(request: Any, timeout_seconds: Any) -> Any:
        return _DummyResponse()

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    orig_complete_success = runtime._complete_success

    def safe_complete_success(*args: Any, **kwargs: Any) -> Any:
        try:
            return orig_complete_success(*args, **kwargs)
        except Exception:
            return kwargs.get("response")

    monkeypatch.setattr(runtime, "_complete_success", safe_complete_success)

    asyncio.run(router.aquery("ping"))

    assert len(record_success_calls) == 1, (
        "Expected _record_success to be called after successful async execution to clear "
        "failure streaks and cooldowns, but it was omitted."
    )
    call_info = record_success_calls[0]
    assert call_info["route"] is not None
    assert call_info["request"] is not None
