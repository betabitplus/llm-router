# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 4185d08c0ebf67fe
# pinned-by: claude-opus-5-5: Changing the check to `wait_seconds > 1` means a route with a wait between 0 and 1 second is no longer treated as blocked. The async path then calls the provider right away, ignoring the pacing wait, and skips a ready fallback route. The resulting attempt traces also differ from the original's (and
from __future__ import annotations

import asyncio
from typing import Any

import pytest
from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_routing_defers_subsecond_pacing_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """A route with a pacing wait under one second must be deferred for a ready alternative."""
    profile_primary = RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE)
    profile_fallback = RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)

    for env_var in (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "NVIDIA_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.setenv(env_var, "test-api-key")

    router = LLMRouter(
        [profile_primary, profile_fallback],
        shuffle_fallbacks=False,
        round_robin_start=False,
    )
    runtime = getattr(router, "_runtime", getattr(router, "runtime", router))

    orig_prepare = runtime._prepare_request
    prepare_routes: list[Any] = []

    def fake_prepare(request_id: str, route: Any, settings: Any, content: Any) -> tuple[Any, float]:
        prepare_routes.append(route)
        try:
            req, _ = orig_prepare(
                request_id=request_id,
                route=route,
                settings=settings,
                content=content,
            )
        except Exception:
            class DummyKey:
                key_id: int = 1

                def __getattr__(self, name: str) -> Any:
                    return None

            class DummyRequest:
                def __init__(self, r: Any, s: Any, c: Any) -> None:
                    self.route = r
                    self.settings = s
                    self.content = c
                    self.key = DummyKey()

                def __getattr__(self, name: str) -> Any:
                    return None

            req = DummyRequest(route, settings, content)

        # Primary route has subsecond pacing wait (0.5s); fallback route is ready (0.0s)
        wait_seconds = 0.5 if len(prepare_routes) == 1 else 0.0
        return req, wait_seconds

    monkeypatch.setattr(runtime, "_prepare_request", fake_prepare)

    called_requests: list[Any] = []

    async def fake_call_async(request: Any, timeout_seconds: float | None = None) -> Any:
        called_requests.append(request)
        try:
            return LLMRouterResponse(
                output_text="pong",
                provider=getattr(getattr(request, "route", None), "provider", Provider.NVIDIA),
                model=getattr(getattr(request, "route", None), "model", Model.DEEPSEEK_V4_FLASH),
            )
        except Exception:
            class MockResponse:
                def __init__(self) -> None:
                    self.output_text = "pong"
                    self.data = {"reply": "pong"}
                    self.usage = None
                    self.traces = []
                    self.final_trace = None
                    self.provider = getattr(getattr(request, "route", None), "provider", None)
                    self.model = getattr(getattr(request, "route", None), "model", None)

                def __getattr__(self, name: str) -> Any:
                    return None

                def model_copy(self, *, update: dict[str, Any] | None = None, **kwargs: Any) -> Any:
                    obj = MockResponse()
                    obj.__dict__.update(self.__dict__)
                    if update:
                        obj.__dict__.update(update)
                    return obj

            return MockResponse()

    monkeypatch.setattr(runtime, "_call_async_with_timeout", fake_call_async)

    completed_calls: list[dict[str, Any]] = []
    orig_complete = runtime._complete_success

    def fake_complete(*, content: Any, request_id: str, response: Any, traces: list[Any], final_trace: Any) -> Any:
        completed_calls.append({
            "response": response,
            "traces": traces,
            "final_trace": final_trace,
        })
        try:
            return orig_complete(
                content=content,
                request_id=request_id,
                response=response,
                traces=traces,
                final_trace=final_trace,
            )
        except Exception:
            if hasattr(response, "__dict__"):
                response.__dict__["traces"] = traces
                response.__dict__["final_trace"] = final_trace
            return response

    monkeypatch.setattr(runtime, "_complete_success", fake_complete)

    response = asyncio.run(router.aquery("test query"))

    assert len(prepare_routes) == 2, (
        "Async routing must advance to prepare the fallback route when the first route is deferred"
    )
    assert len(called_requests) == 1
    assert called_requests[0].route == prepare_routes[1], (
        "Async routing must try the ready alternative route first when the primary route has a pacing wait"
    )
    assert len(completed_calls) == 1
    traces = completed_calls[0]["traces"]
    assert len(traces) == 1, (
        "The deferred route must be recorded as blocked in the attempt traces"
    )
    assert any(getattr(t, "wait_seconds", None) == 0.5 for t in traces), (
        "Attempt traces must report the subsecond wait duration for the blocked route"
    )
