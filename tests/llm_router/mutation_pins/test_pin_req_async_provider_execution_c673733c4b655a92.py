# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION c673733c4b655a92
# pinned-by: claude-opus-5-5
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


@dataclasses.dataclass
class _DummyResponse:
    text: str = "ok"
    content: Any = "ok"


@dataclasses.dataclass
class _DummyResult:
    traces: list[Any]
    failed_traces: list[Any]
    final_trace: Any = None
    response: Any = None


def _build_two_route_router(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[LLMRouter, Any, Any]:
    value = "test-value"
    monkeypatch.setenv("NVIDIA_API_KEY", value)
    p1 = RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    router = LLMRouter([p1, p1])
    runtime = getattr(router, "_runtime", router)
    plan = getattr(runtime, "route_plan", None)
    routes = getattr(plan, "routes", plan)
    return router, routes[0], routes[1]


def _instrument_runtime(
    runtime: Any,
    route_0: Any,
    route_1: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[Any], list[tuple[list[Any], Any]]]:
    _ = route_1
    attempted_routes: list[Any] = []
    completed_traces: list[tuple[list[Any], Any]] = []

    def mock_prepare_request(
        request_id: Any, route: Any, settings: Any, content: Any
    ) -> tuple[Any, int]:
        _ = (request_id, settings, content)
        return _DummyRequest(route=route), 0

    def mock_call_sync(request: Any, timeout_seconds: Any = None) -> Any:
        _ = timeout_seconds
        route = getattr(request, "route", None)
        attempted_routes.append(route)
        if route is route_0 or (route == route_0 and route is not route_1):
            msg = "Route 0 simulated sync error"
            raise RuntimeError(msg)
        return _DummyResponse()

    async def mock_call_async(request: Any, timeout_seconds: Any = None) -> Any:
        _ = timeout_seconds
        route = getattr(request, "route", None)
        attempted_routes.append(route)
        if route is route_0 or (route == route_0 and route is not route_1):
            msg = "Route 0 simulated async error"
            raise RuntimeError(msg)
        return _DummyResponse()

    def mock_complete_success(*args: Any, **kwargs: Any) -> Any:
        _ = args
        traces = list(kwargs.get("traces", []))
        final_trace = kwargs.get("final_trace")
        completed_traces.append((traces, final_trace))
        all_traces = [*traces, final_trace] if final_trace else list(traces)
        return _DummyResult(
            traces=all_traces,
            failed_traces=traces,
            final_trace=final_trace,
            response=kwargs.get("response"),
        )

    def mock_noop(*args: Any, **kwargs: Any) -> None:
        _ = (args, kwargs)

    monkeypatch.setattr(runtime, "_prepare_request", mock_prepare_request)
    monkeypatch.setattr(runtime, "_record_failure", mock_noop)
    monkeypatch.setattr(runtime, "_record_success", mock_noop)
    monkeypatch.setattr(runtime, "_complete_success", mock_complete_success)
    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    for method_name in (
        "_call_sync_with_timeout",
        "_call_sync",
        "_call_with_timeout",
    ):
        if hasattr(runtime, method_name):
            monkeypatch.setattr(runtime, method_name, mock_call_sync)

    return attempted_routes, completed_traces


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_fallback_success_is_remembered_for_subsequent_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 1. Establish baseline behavior on sync router
    sync_router, s_route_0, s_route_1 = _build_two_route_router(monkeypatch)
    sync_runtime = getattr(sync_router, "_runtime", sync_router)
    sync_attempts, sync_traces = _instrument_runtime(
        sync_runtime, s_route_0, s_route_1, monkeypatch
    )

    sync_router.query("initial test request")
    assert sync_runtime._sticky_start_route_index is not None
    assert sync_attempts == [s_route_0, s_route_1]

    sync_attempts.clear()
    sync_res_2 = sync_router.query("subsequent test request")
    assert sync_attempts == [s_route_1]
    sync_req2_failed_traces = sync_traces[1][0]
    assert len(sync_req2_failed_traces) == 0

    # 2. Run corresponding requests on async router
    async_router, a_route_0, a_route_1 = _build_two_route_router(monkeypatch)
    async_runtime = getattr(async_router, "_runtime", async_router)
    async_attempts, async_traces = _instrument_runtime(
        async_runtime, a_route_0, a_route_1, monkeypatch
    )

    asyncio.run(async_router.aquery("initial test request"))
    assert async_attempts == [a_route_0, a_route_1]

    # Under the defect, fallback_occurred evaluates to False because
    # blocked_requests is empty, so _sticky_start_route_index stays None.
    assert async_runtime._sticky_start_route_index is not None, (
        "Async fallback success was not remembered: _sticky_start_route_index is None"
    )
    assert (
        async_runtime._sticky_start_route_index
        == sync_runtime._sticky_start_route_index
    )

    # 3. Assert next async request starts on the remembered route
    async_attempts.clear()
    async_res_2 = asyncio.run(async_router.aquery("subsequent test request"))

    assert async_attempts == [a_route_1], (
        "Next async request did not start on the fallback route; "
        f"attempts: {async_attempts}"
    )

    async_req2_failed_traces = async_traces[1][0]
    assert len(async_req2_failed_traces) == len(sync_req2_failed_traces) == 0
    assert len(async_attempts) == len(sync_attempts) == 1

    if hasattr(async_res_2, "traces") and hasattr(sync_res_2, "traces"):
        assert len(async_res_2.traces) == len(sync_res_2.traces)
