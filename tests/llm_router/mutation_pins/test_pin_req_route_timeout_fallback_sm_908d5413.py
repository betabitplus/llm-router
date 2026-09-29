# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK SM-908D5413
# pinned-by: claude-opus-5-5
from __future__ import annotations

import typing

import pytest

import llm_router

pytestmark = pytest.mark.verification_kind("unit")


class _SlowWorkerExecutor:
    """Blocks when run on a worker thread; returns at once on the caller."""

    def __init__(self, response: object, release: object, caller: int) -> None:
        self.response = response
        self.release = release
        self.caller = caller
        self.received_request: object = None

    def execute(self, request: object) -> object:
        threading = typing.sys.modules["threading"]
        self.received_request = request
        if threading.get_ident() != self.caller:
            self.release.wait(5)
        return self.response


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
def test_sync_zero_timeout_raises_timeout_error() -> None:
    """A zero attempt timeout must time out, not run without a timeout."""
    threading = typing.sys.modules["threading"]
    router_mod = typing.sys.modules["llm_router._internal.runtime.router"]
    router_runtime_cls = router_mod.RouterRuntime
    response_cls = router_mod.LLMRouterResponse
    request_cls = router_mod.ResolvedRequest

    request = request_cls.__new__(request_cls)
    response = response_cls.__new__(response_cls)
    release = threading.Event()
    executor = _SlowWorkerExecutor(response, release, threading.get_ident())

    runtime = router_runtime_cls.__new__(router_runtime_cls)
    runtime._executor = executor

    with pytest.raises(TimeoutError, match=r"Attempt timed out"):
        runtime._call_sync_with_timeout(request, timeout_seconds=0)
    release.set()
    assert llm_router is not None
