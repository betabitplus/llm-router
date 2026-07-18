from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from llm_router import LLMRouterResponse, Model, Provider, ProviderLimits, RouterProfile
from llm_router._internal.runtime.requests import ResolvedRequest
from llm_router._internal.runtime.router import RouterRuntime

Outcome = Callable[[ResolvedRequest], LLMRouterResponse] | BaseException


class ScriptedExecutor:
    def __init__(self, outcomes: list[Outcome] | None = None) -> None:
        self.outcomes = list(outcomes or [])
        self.requests: list[ResolvedRequest] = []

    def execute(self, request: ResolvedRequest) -> LLMRouterResponse:
        self.requests.append(request)
        return self._next_response(request)

    async def aexecute(self, request: ResolvedRequest) -> LLMRouterResponse:
        self.requests.append(request)
        return self._next_response(request)

    def _next_response(self, request: ResolvedRequest) -> LLMRouterResponse:
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome(request)
        return _response(request, text=f"route-{request.route.route_index}")


class SlowFirstExecutor(ScriptedExecutor):
    def execute(self, request: ResolvedRequest) -> LLMRouterResponse:
        self.requests.append(request)
        if request.route.route_index == 0:
            time.sleep(0.25)
            return _response(request, text="slow")
        return _response(request, text="fast")


def _response(request: ResolvedRequest, *, text: str) -> LLMRouterResponse:
    return LLMRouterResponse(
        data={"request_id": request.request_id},
        provider=request.route.provider.value,
        model=request.route.model.value,
        output_text=text,
    )


def _set_provider_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY_1", "nvidia-key-1")
    monkeypatch.setenv("NVIDIA_API_KEY_2", "nvidia-key-2")
    monkeypatch.setenv("GROQ_API_KEY_1", "groq-key-1")


def test_sync_fallback_records_invalid_provider_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider_keys(monkeypatch)
    executor = ScriptedExecutor()
    runtime = RouterRuntime(
        spec=[
            RouterProfile(provider="not-a-provider", model=Model.DEEPSEEK_V4_FLASH),
            RouterProfile(provider=Provider.NVIDIA, model=Model.DEEPSEEK_V4_FLASH),
        ],
        _executor=executor,
        shuffle_fallbacks=False,
    )

    response = runtime.query("hello", temperature=0.0)

    assert response.output_text == "route-1"
    assert [attempt.provider for attempt in response.routing_trace] == [
        "not-a-provider",
        Provider.NVIDIA.value,
    ]
    assert response.routing_trace[0].error_type == "ValueError"
    assert response.routing_trace[1].temperature == 0.0
    assert [request.route.route_index for request in executor.requests] == [1]


@pytest.mark.asyncio
async def test_async_fallback_records_failed_attempt_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider_keys(monkeypatch)
    executor = ScriptedExecutor([RuntimeError("first failed")])
    runtime = RouterRuntime(
        spec=[
            RouterProfile(provider=Provider.GROQ, model=Model.LLAMA_SCOUT),
            RouterProfile(provider=Provider.NVIDIA, model=Model.DEEPSEEK_V4_FLASH),
        ],
        _executor=executor,
        shuffle_fallbacks=False,
    )

    response = await runtime.aquery("hello")

    assert response.output_text == "route-1"
    assert [attempt.route_index for attempt in response.routing_trace] == [0, 1]
    assert response.routing_trace[0].error_type == "RuntimeError"
    assert response.routing_trace[0].key_id == 1
    assert response.routing_trace[1].error_type is None


def test_sync_attempt_timeout_falls_back_without_waiting_for_slow_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider_keys(monkeypatch)
    executor = SlowFirstExecutor()
    runtime = RouterRuntime(
        spec=[
            RouterProfile(provider=Provider.GROQ, model=Model.LLAMA_SCOUT),
            RouterProfile(provider=Provider.NVIDIA, model=Model.DEEPSEEK_V4_FLASH),
        ],
        _executor=executor,
        attempt_timeout_seconds=0.02,
        shuffle_fallbacks=False,
    )

    started_at = time.monotonic()
    response = runtime.query("hello")
    elapsed = time.monotonic() - started_at

    assert response.output_text == "fast"
    assert elapsed < 0.20
    assert [attempt.error_type for attempt in response.routing_trace] == [
        "TimeoutError",
        None,
    ]


def test_blocked_route_is_skipped_when_later_route_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider_keys(monkeypatch)
    executor = ScriptedExecutor()
    runtime = RouterRuntime(
        spec=[
            RouterProfile(
                provider=Provider.NVIDIA,
                model=Model.DEEPSEEK_V4_FLASH,
                key_id=1,
            ),
            RouterProfile(
                provider=Provider.NVIDIA,
                model=Model.DEEPSEEK_V4_FLASH,
                key_id=2,
            ),
        ],
        _executor=executor,
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=20.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )

    runtime.query("first")
    second = runtime.query("second")

    assert [request.key.key_id for request in executor.requests] == [1, 2]
    assert [attempt.key_id for attempt in second.routing_trace] == [1, 2]
    assert second.routing_trace[0].error_type == "RouteBlockedError"
    assert second.routing_trace[1].error_type is None


def test_all_blocked_routes_fail_fast_when_waiting_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider_keys(monkeypatch)
    executor = ScriptedExecutor()
    runtime = RouterRuntime(
        spec=RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.DEEPSEEK_V4_FLASH,
            key_id=1,
        ),
        _executor=executor,
        wait_for_cooldown_if_all_blocked=False,
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=1.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )

    runtime.query("first")
    started_at = time.monotonic()
    with pytest.raises(TimeoutError, match="All routes are blocked"):
        runtime.query("second")

    assert time.monotonic() - started_at < 0.2
    assert len(executor.requests) == 1


def test_all_blocked_routes_wait_then_execute_when_waiting_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider_keys(monkeypatch)
    executor = ScriptedExecutor()
    runtime = RouterRuntime(
        spec=RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.DEEPSEEK_V4_FLASH,
            key_id=1,
        ),
        _executor=executor,
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=20.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )

    runtime.query("first")
    started_at = time.monotonic()
    second = runtime.query("second")
    elapsed = time.monotonic() - started_at

    assert len(second.routing_trace) == 1
    assert second.routing_trace[0].key_id == 1
    assert second.routing_trace[0].wait_seconds > 0.0
    assert elapsed >= max(0.0, second.routing_trace[0].wait_seconds - 0.01)
    assert len(executor.requests) == 2


@pytest.mark.asyncio
async def test_async_all_blocked_route_waits_then_executes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider_keys(monkeypatch)
    executor = ScriptedExecutor()
    runtime = RouterRuntime(
        spec=RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.DEEPSEEK_V4_FLASH,
            key_id=1,
        ),
        _executor=executor,
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=20.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )

    await runtime.aquery("first")
    second = await runtime.aquery("second")

    assert len(second.routing_trace) == 1
    assert second.routing_trace[0].key_id == 1
    assert second.routing_trace[0].wait_seconds > 0.0
    assert len(executor.requests) == 2
