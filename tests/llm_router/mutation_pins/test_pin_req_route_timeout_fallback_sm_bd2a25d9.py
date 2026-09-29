# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK SM-BD2A25D9
# pinned-by: claude-opus-5-5
from __future__ import annotations

import typing

import pytest

import llm_router

pytestmark = pytest.mark.verification_kind("unit")


class _SlowExecutor:
    """Executor double whose call finishes after 1.5 timeouts."""

    def __init__(self, response: object, delay: float) -> None:
        self.response = response
        self.delay = delay
        self.gate = typing.sys.modules["threading"].Event()

    def execute(self, request: object) -> object:
        assert request is not None
        self.gate.wait(self.delay)
        return self.response


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
def test_sync_attempt_times_out_after_one_timeout_without_grace() -> None:
    """A call finishing after 1.5 timeouts must still raise TimeoutError."""
    router_mod = typing.sys.modules["llm_router._internal.runtime.router"]
    router_runtime_cls = router_mod.RouterRuntime
    response_cls = router_mod.LLMRouterResponse
    request_cls = router_mod.ResolvedRequest

    request = request_cls.__new__(request_cls)
    slow_response = response_cls.__new__(response_cls)
    executor = _SlowExecutor(slow_response, 0.3)

    runtime = router_runtime_cls.__new__(router_runtime_cls)
    runtime._executor = executor

    assert llm_router is not None
    with pytest.raises(TimeoutError, match=r"Attempt timed out"):
        runtime._call_sync_with_timeout(request, timeout_seconds=0.2)
