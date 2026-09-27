# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 3dc1348c54023b59
# pinned-by: claude-opus-5-5: The mutant drops `_record_failure` from the async attempt path, so a provider or key failure is never recorded in the health, cooldown and circuit state. Async requests would then route differently from sync ones: later calls keep hitting a failed key or route, and the routing traces change. That br
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


@dataclasses.dataclass
class _DummyRequest:
    key: _DummyKey = dataclasses.field(default_factory=_DummyKey)
    route: Any = None


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_execution_records_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-12345")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")

    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    runtime = getattr(router, "_runtime", router)

    record_failure_calls: list[dict[str, Any]] = []
    original_record_failure = getattr(runtime, "_record_failure", None)

    def spy_record_failure(*args: Any, **kwargs: Any) -> Any:
        request = kwargs.get("request") if "request" in kwargs else (args[0] if len(args) > 0 else None)
        exc = kwargs.get("exc") if "exc" in kwargs else (args[1] if len(args) > 1 else None)
        record_failure_calls.append({
            "request": request,
            "exc": exc,
        })
        if original_record_failure is not None:
            try:
                return original_record_failure(*args, **kwargs)
            except Exception:
                return None
        return None

    monkeypatch.setattr(runtime, "_record_failure", spy_record_failure)

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

    simulated_error = RuntimeError("simulated provider failure")

    async def mock_call_async(request: Any, timeout_seconds: Any) -> Any:
        raise simulated_error

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    with pytest.raises(RuntimeError, match="simulated provider failure"):
        asyncio.run(router.aquery("test content prompt"))

    assert len(record_failure_calls) == 1
    assert record_failure_calls[0]["exc"] is simulated_error
    assert record_failure_calls[0]["request"] is not None
