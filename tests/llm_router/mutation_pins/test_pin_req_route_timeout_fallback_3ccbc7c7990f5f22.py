# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK 3ccbc7c7990f5f22
# pinned-by: claude-opus-5-5
from __future__ import annotations

import typing

import pytest

import llm_router

pytestmark = pytest.mark.verification_kind("unit")


class _RecordingExecutor:
    """Executor test double that records calls and returns a response."""

    def __init__(self, response: object) -> None:
        self.response = response
        self.called = False
        self.received_request: object = None

    def execute(self, request: object) -> object:
        self.called = True
        self.received_request = request
        return self.response


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
def test_sync_call_without_timeout_returns_executor_response() -> None:
    """_call_sync_with_timeout must return executor response when timeout is None."""
    router_runtime_cls = getattr(llm_router, "RouterRuntime", None)
    if router_runtime_cls is None:
        router_mod = typing.sys.modules["llm_router._internal.runtime.router"]
        router_runtime_cls = router_mod.RouterRuntime

    response_cls = getattr(llm_router, "LLMRouterResponse", None)
    if response_cls is None:
        router_mod = typing.sys.modules["llm_router._internal.runtime.router"]
        response_cls = router_mod.LLMRouterResponse

    request_cls = getattr(llm_router, "ResolvedRequest", None)
    if request_cls is None:
        router_mod = typing.sys.modules["llm_router._internal.runtime.router"]
        request_cls = router_mod.ResolvedRequest

    request = request_cls.__new__(request_cls)
    expected_response = response_cls.__new__(response_cls)
    executor = _RecordingExecutor(expected_response)

    runtime = router_runtime_cls.__new__(router_runtime_cls)
    runtime._executor = executor

    result = runtime._call_sync_with_timeout(
        request,
        timeout_seconds=None,
    )

    assert executor.called is True, "Executor must be called when timeout is None."
    assert executor.received_request is request, "Request must be passed to executor."
    assert result is expected_response, (
        f"Expected executor response {expected_response!r}, got {result!r}. "
        "Defect: _call_sync_with_timeout returns None instead of response."
    )
