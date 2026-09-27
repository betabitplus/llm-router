# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION c673733c4b655a92
# pinned-by: claude-opus-5-5: Changing `or` to `and` means an async request whose primary route failed and whose fallback then succeeded is only remembered as a fallback success when a blocked route also exists. As a result, the attempt order and routing traces of later async requests differ from the sync path. That is a visible
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
    key: Any = dataclasses.field(default_factory=_DummyKey)
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
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-12345")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test-key-12345")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-test-key-12345")

    p1 = RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    spec: Any = None
    for prov in Provider:
        for mod in Model:
            if prov == Provider.NVIDIA and mod == Model.DEEPSEEK_V4_FLASH:
                continue
            try:
                candidate = RouterProfile(model=mod, provider=prov)
                r = LLMRouter([p1, candidate])
                rt = getattr(r, "_runtime", r)
                plan = getattr(rt, "route_plan", None)
                routes = getattr(plan, "routes", plan)
                if len(routes) >= 2:
                    spec = [p1, candidate]
                    break
            except Exception:
                continue
        if spec is not None:
            break

    if spec is None:
        spec = [p1, p1]

    router = LLMRouter(spec)
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
    attempted_routes: list[Any] = []
    completed_traces: list[tuple[list[Any], Any]] = []
    active_route: list[Any] = [None]

    orig_log_route_selected = getattr(runtime, "_log_route_selected", None)

    def spy_log_route_selected(*args: Any, **kwargs: Any) -> Any:
        route = kwargs.get("route") if "route" in kwargs else (args[1] if len(args) > 1 else None)
        active_route[0] = route
        if orig_log_route_selected is not None:
            return orig_log_route_selected(*args, **kwargs)

    monkeypatch.setattr(runtime, "_log_route_selected", spy_log_route_selected)

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
            if not hasattr(req, "route"):
                try:
                    req.route = route
                except Exception:
                    pass
            return (req, 0)
        except Exception:
            key = getattr(route, "key", None)
            key_id = 1
            if key is not None and isinstance(getattr(key, "key_id", None), int):
                key_id = key.key_id
            return (_DummyRequest(key=_DummyKey(key_id=key_id), route=route), 0)

    monkeypatch.setattr(runtime, "_prepare_request", safe_prepare_request)

    orig_record_success = runtime._record_success

    def safe_record_success(*args: Any, **kwargs: Any) -> Any:
        try:
            return orig_record_success(*args, **kwargs)
        except Exception:
            return None

    monkeypatch.setattr(runtime, "_record_success", safe_record_success)

    orig_record_failure = runtime._record_failure

    def safe_record_failure(*args: Any, **kwargs: Any) -> Any:
        try:
            return orig_record_failure(*args, **kwargs)
        except Exception:
            return None

    monkeypatch.setattr(runtime, "_record_failure", safe_record_failure)

    orig_complete_success = runtime._complete_success

    def safe_complete_success(*args: Any, **kwargs: Any) -> Any:
        traces = list(kwargs.get("traces", []))
        final_trace = kwargs.get("final_trace")
        completed_traces.append((traces, final_trace))
        try:
            res = orig_complete_success(*args, **kwargs)
            if not hasattr(res, "traces"):
                all_traces = list(traces)
                if final_trace is not None:
                    all_traces.append(final_trace)
                try:
                    res.traces = all_traces
                except Exception:
                    pass
            return res
        except Exception:
            all_traces = list(traces)
            if final_trace is not None:
                all_traces.append(final_trace)
            return _DummyResult(
                traces=all_traces,
                failed_traces=traces,
                final_trace=final_trace,
                response=kwargs.get("response"),
            )

    monkeypatch.setattr(runtime, "_complete_success", safe_complete_success)

    async def mock_call_async(request: Any, timeout_seconds: Any = None) -> Any:
        route = active_route[0] or getattr(request, "route", None)
        attempted_routes.append(route)
        if route == route_0:
            msg = "Route 0 simulated async error"
            raise RuntimeError(msg)
        return _DummyResponse()

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    def mock_call_sync(request: Any, timeout_seconds: Any = None) -> Any:
        route = active_route[0] or getattr(request, "route", None)
        attempted_routes.append(route)
        if route == route_0:
            msg = "Route 0 simulated sync error"
            raise RuntimeError(msg)
        return _DummyResponse()

    for method_name in ["_call_sync_with_timeout", "_call_sync", "_call_with_timeout"]:
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

    # Under the defect, fallback_occurred evaluates to False because blocked_requests is empty,
    # leaving _sticky_start_route_index as None instead of remembering the successful fallback.
    assert async_runtime._sticky_start_route_index is not None, (
        "Async fallback success was not remembered: _sticky_start_route_index is None"
    )
    assert (
        async_runtime._sticky_start_route_index
        == sync_runtime._sticky_start_route_index
    )

    # 3. Assert next async request starts on the remembered route and traces match sync
    async_attempts.clear()
    async_res_2 = asyncio.run(async_router.aquery("subsequent test request"))

    assert async_attempts == [a_route_1], (
        f"Next async request did not start on the fallback route; attempts: {async_attempts}"
    )

    async_req2_failed_traces = async_traces[1][0]
    assert len(async_req2_failed_traces) == len(sync_req2_failed_traces) == 0
    assert len(async_attempts) == len(sync_attempts) == 1

    if hasattr(async_res_2, "traces") and hasattr(sync_res_2, "traces"):
        assert len(async_res_2.traces) == len(sync_res_2.traces)
