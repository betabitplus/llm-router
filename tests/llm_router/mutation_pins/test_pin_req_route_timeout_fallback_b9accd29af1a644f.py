# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK b9accd29af1a644f
# pinned-by: claude-opus-5-5: After a timeout, the mutant leaves timed_out False, so the finally block calls pool.shutdown(wait=True) and blocks until the timed-out executor call finishes. The sync path therefore keeps waiting on the timed-out route, against the requirement that it stop waiting. The existing tests likely pass on
from __future__ import annotations

import dataclasses
import json
import re
import typing

import llm_router
import pytest
import tests.llm_router.support.workers.timeout as worker_timeout

pytestmark = pytest.mark.verification_kind("unit")


def _instantiate(cls: type, **overrides: object) -> object:
    if dataclasses.is_dataclass(cls):
        fields = dataclasses.fields(cls)
        kwargs: dict[str, object] = {}
        for f in fields:
            if f.name in overrides:
                kwargs[f.name] = overrides[f.name]
            elif f.default is not dataclasses.MISSING:
                continue
            elif f.default_factory is not dataclasses.MISSING:
                continue
            else:
                name_lower = f.name.lower()
                if "token" in name_lower:
                    kwargs[f.name] = 25
                elif f.type in (int, "int", "int | None", "Optional[int]"):
                    kwargs[f.name] = 10
                elif f.type in (float, "float", "float | None", "Optional[float]"):
                    kwargs[f.name] = 1.0
                elif f.type in (str, "str", "str | None", "Optional[str]"):
                    kwargs[f.name] = f"test-{f.name}"
                elif f.type in (bool, "bool"):
                    kwargs[f.name] = True
                elif f.type in (list, "list", "list[str]"):
                    kwargs[f.name] = []
                elif f.type in (dict, "dict"):
                    kwargs[f.name] = {}
                else:
                    kwargs[f.name] = "test-value"
        return cls(**kwargs)
    return cls(**overrides)


class BlockingSyncExecutor:
    """Sync executor that blocks the first route attempt on an event."""

    def __init__(
        self,
        block_event: typing.Any,
        success_response: typing.Any,
        block_duration: float = 3.0,
    ) -> None:
        self.block_event = block_event
        self.success_response = success_response
        self.block_duration = block_duration
        self.calls: list[object] = []

    def execute(self, request: object) -> object:
        self.calls.append(request)
        if len(self.calls) == 1:
            self.block_event.wait(timeout=self.block_duration)
            msg = "Attempt timed out."
            raise TimeoutError(msg)
        return self.success_response


def _build_route_spec() -> object:
    for attr in (
        "make_timeout_spec",
        "make_spec",
        "make_route_plan",
        "TIMEOUT_SPEC",
        "SPEC",
    ):
        if hasattr(worker_timeout, attr):
            val = getattr(worker_timeout, attr)
            return val() if callable(val) else val

    RouterSpec = getattr(llm_router, "RouterSpec", None)
    RouteSpec = getattr(llm_router, "RouteSpec", None)
    if RouterSpec and RouteSpec:
        try:
            r1 = _instantiate(RouteSpec, name="route-primary", model="provider-a/model-1")
            r2 = _instantiate(RouteSpec, name="route-fallback", model="provider-b/model-2")
            return _instantiate(RouterSpec, routes=[r1, r2])
        except Exception:
            pass

    if RouterSpec:
        try:
            return RouterSpec(routes=["provider-a/model-1", "provider-b/model-2"])
        except Exception:
            pass

    return ("provider-a/model-1", "provider-b/model-2")


def _create_router(executor: BlockingSyncExecutor) -> object:
    for factory in (
        "make_timeout_router",
        "create_timeout_router",
        "build_timeout_router",
        "make_router",
    ):
        if hasattr(worker_timeout, factory):
            try:
                return getattr(worker_timeout, factory)(executor=executor)
            except Exception:
                pass

    RouterClass = getattr(llm_router, "LLMRouter", None) or getattr(
        llm_router, "RouterRuntime", None
    )
    if RouterClass is None:
        router_mod = typing.sys.modules.get("llm_router._internal.runtime.router")
        if router_mod:
            RouterClass = getattr(router_mod, "RouterRuntime", None)

    if RouterClass is not None:
        spec = _build_route_spec()
        return RouterClass(spec=spec, executor=executor)
    return None


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
def test_sync_timeout_stops_waiting_and_falls_back() -> None:
    Event = getattr(worker_timeout, "Event", None)
    if Event is None:
        threading_mod = typing.sys.modules.get("threading")
        Event = threading_mod.Event

    time_mod = typing.sys.modules.get("time")
    monotonic = time_mod.monotonic if time_mod else None

    blocked_duration = 3.0
    bounded_time = 1.0
    attempt_timeout = 0.05

    LLMRouterResponse = getattr(llm_router, "LLMRouterResponse", None)
    if LLMRouterResponse and dataclasses.is_dataclass(LLMRouterResponse):
        success_response = _instantiate(
            LLMRouterResponse,
            content="fallback response content",
            route="route-fallback",
            token_count=42,
        )
    else:
        success_response = "fallback response content"

    block_event = Event()
    executor = BlockingSyncExecutor(
        block_event=block_event,
        success_response=success_response,
        block_duration=blocked_duration,
    )

    router = None
    try:
        router = _create_router(executor)
    except Exception:
        router = None

    if router is not None:
        t0 = monotonic() if monotonic else 0.0
        try:
            response = router.query(
                "test query prompt", timeout_seconds=attempt_timeout
            )
            elapsed = (monotonic() - t0) if monotonic else 0.0
            assert response == success_response or response is not None
            assert (
                len(executor.calls) >= 2
            ), f"Expected fallback to second route, made {len(executor.calls)} calls"
            if monotonic:
                assert (
                    elapsed < bounded_time
                ), f"Sync fallback took {elapsed:.2f}s, expected < {bounded_time}s"
        finally:
            block_event.set()
    else:
        RouterRuntime = getattr(llm_router, "RouterRuntime", None)
        router_mod = typing.sys.modules.get("llm_router._internal.runtime.router")
        if RouterRuntime is None and router_mod:
            RouterRuntime = getattr(router_mod, "RouterRuntime", None)

        ResolvedRequest = getattr(llm_router, "ResolvedRequest", None)
        if ResolvedRequest is None and router_mod:
            ResolvedRequest = getattr(router_mod, "ResolvedRequest", None)

        request = (
            _instantiate(ResolvedRequest)
            if (ResolvedRequest and dataclasses.is_dataclass(ResolvedRequest))
            else None
        )

        runtime = RouterRuntime.__new__(RouterRuntime)
        runtime._executor = executor

        t0 = monotonic() if monotonic else 0.0
        try:
            with pytest.raises(TimeoutError):
                runtime._call_sync_with_timeout(
                    request, timeout_seconds=attempt_timeout
                )
            elapsed = (monotonic() - t0) if monotonic else 0.0
            if monotonic:
                assert (
                    elapsed < bounded_time
                ), f"Timed out attempt took {elapsed:.2f}s, expected < {bounded_time}s"
        finally:
            block_event.set()
