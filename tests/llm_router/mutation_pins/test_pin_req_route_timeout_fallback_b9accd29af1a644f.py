# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK b9accd29af1a644f
# pinned-by: claude-opus-5-5
from __future__ import annotations

import typing

import pytest

import llm_router
import tests.llm_router.support.workers.timeout as worker_timeout

pytestmark = pytest.mark.verification_kind("unit")

_BLOCK_DURATION = 3.0
_ATTEMPT_TIMEOUT = 0.05
_BOUNDED_TIME = 0.5


class _BlockingExecutor:
    """Executor that blocks every call until block_event is set."""

    def __init__(
        self,
        block_event: typing.Any,
        block_duration: float,
    ) -> None:
        self.block_event = block_event
        self.block_duration = block_duration
        self.calls: list[object] = []

    def execute(self, request: object) -> object:
        self.calls.append(request)
        self.block_event.wait(timeout=self.block_duration)
        return object()


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
def test_sync_timeout_returns_promptly_without_blocking_on_shutdown() -> None:
    """pool.shutdown must use wait=False after a timeout.

    The defect flips timed_out to False inside the except block, so
    pool.shutdown(wait=not False) == pool.shutdown(wait=True), which
    blocks the caller until the stuck background thread finishes
    (_BLOCK_DURATION seconds).  The correct code uses wait=False and
    returns in well under _BOUNDED_TIME.
    """
    event_cls = getattr(worker_timeout, "Event", None)
    if event_cls is None:
        sys_mod = typing.sys  # typing imports sys internally
        threading_mod = sys_mod.modules.get("threading")
        event_cls = threading_mod.Event  # type: ignore[union-attr]

    time_mod = typing.sys.modules["time"]

    router_runtime_cls = getattr(llm_router, "RouterRuntime", None)
    if router_runtime_cls is None:
        router_mod = typing.sys.modules["llm_router._internal.runtime.router"]
        router_runtime_cls = router_mod.RouterRuntime

    block_event = event_cls()
    executor = _BlockingExecutor(
        block_event=block_event,
        block_duration=_BLOCK_DURATION,
    )

    runtime = router_runtime_cls.__new__(router_runtime_cls)
    runtime._executor = executor

    t0 = time_mod.monotonic()
    with pytest.raises(TimeoutError):
        runtime._call_sync_with_timeout(
            None,
            timeout_seconds=_ATTEMPT_TIMEOUT,
        )
    elapsed = time_mod.monotonic() - t0

    block_event.set()  # release the stuck background thread

    assert elapsed < _BOUNDED_TIME, (
        f"_call_sync_with_timeout blocked for {elapsed:.3f}s after raising "
        f"TimeoutError (expected < {_BOUNDED_TIME}s). "
        "Defect: timed_out=False causes pool.shutdown(wait=True), "
        "which hangs until the background thread finishes."
    )
