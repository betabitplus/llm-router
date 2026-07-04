from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import pytest
from pydantic import BaseModel, Field

from llm_router import (
    LLMRouterResponse,
    Model,
    Provider,
    ProviderError,
    ProviderLimits,
    RouterProfile,
    ToolCall,
    ToolExecutionError,
)
from llm_router._internal.config import get_config
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.requests import ResolvedRequest
from llm_router._internal.runtime.router import RouterRuntime


class Reply(BaseModel):
    answer: str = Field(min_length=2)


class ScriptedAdapter:
    capabilities = ProviderCapabilities(supports_json_schema=True, supports_tools=True)

    def __init__(self, outcomes: Sequence[ProviderResult | Exception]) -> None:
        self.outcomes = list(outcomes)

    def execute(self, _request: ProviderRequest) -> ProviderResult:
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


class ScriptedRouteExecutor:
    def __init__(self, outcomes: Sequence[LLMRouterResponse | Exception] = ()) -> None:
        self.outcomes = list(outcomes)

    def execute(self, request: ResolvedRequest) -> LLMRouterResponse:
        return self._next_response(request)

    async def aexecute(self, request: ResolvedRequest) -> LLMRouterResponse:
        return self._next_response(request)

    def _next_response(self, request: ResolvedRequest) -> LLMRouterResponse:
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return LLMRouterResponse(
            data={"route_index": request.route.route_index},
            provider=request.route.provider.value,
            model=request.route.model.value,
            output_text=f"route-{request.route.route_index}",
        )


def explode(*, value: int) -> dict[str, int]:
    msg = f"boom {value}"
    raise RuntimeError(msg)


def ping(*, value: int) -> dict[str, int]:
    return {"value": value}


def _result(
    text: str,
    *,
    tool_calls: tuple[ToolCall, ...] = (),
) -> ProviderResult:
    return ProviderResult(
        data={"text": text},
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="deepseek/deepseek-chat-v3-0324:free",
        output_text=text,
        tool_calls=tool_calls,
    )


def _retryable_error() -> ProviderError:
    failure = ProviderFailure(
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        message="retry once",
        retryable=True,
        status_code=503,
        retry_reason="retryable_status",
    )
    return ProviderError(
        failure,
        Provider.OPENROUTER,
        Model.DEEPSEEK_V3,
        message=failure.message,
    )


def _fast_config():
    config = get_config()
    return replace(
        config,
        defaults=replace(
            config.defaults,
            retry_policy=RetryPolicy(
                min_wait_seconds=0.001,
                max_wait_seconds=0.001,
                max_attempts=2,
            ),
        ),
    )


def _runtime(adapter: ScriptedAdapter) -> RouterRuntime:
    executor = ProviderRouteExecutor(
        config=_fast_config(),
        adapter_getter=lambda _provider, _config: adapter,
    )
    return RouterRuntime(
        spec=RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        _executor=executor,
        round_robin_start=False,
        shuffle_fallbacks=False,
    )


def _payloads(records: list[logging.LogRecord]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for record in records:
        if isinstance(record.msg, dict):
            payloads.append(record.msg)
        elif isinstance(record.args, dict):
            payloads.append(record.args)
        else:
            event_type = getattr(record, "event_type", None)
            if isinstance(event_type, str):
                payloads.append(dict(record.__dict__))
    return payloads


def _event_types(records: list[logging.LogRecord]) -> set[str]:
    return {
        str(payload["event_type"])
        for payload in _payloads(records)
        if "event_type" in payload
    }


def test_retry_and_schema_repair_events_are_emitted(
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    caplog.set_level(logging.INFO, logger="llm_router")
    prompt_marker = "SECRET_PROMPT_SHOULD_NOT_APPEAR"
    adapter = ScriptedAdapter(
        [
            _retryable_error(),
            _result('{"answer": "x"}'),
            _result('{"answer": "ok"}'),
        ]
    )

    response = _runtime(adapter).query(prompt_marker, response_schema=Reply)

    event_types = _event_types(caplog.records)
    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert response.data["parsed"] == {"answer": "ok"}
    assert "llm_router.provider.retry.scheduled" in event_types
    assert "llm_router.capability.schema.validation.failed" in event_types
    assert "llm_router.capability.schema.repair.started" in event_types
    assert "llm_router.capability.schema.repair.succeeded" in event_types
    retry_events = [
        payload
        for payload in _payloads(caplog.records)
        if payload.get("event_type") == "llm_router.provider.retry.scheduled"
    ]
    assert retry_events
    assert retry_events[0]["route_index"] == 0
    assert prompt_marker not in rendered


def test_retry_and_schema_repair_exhaustion_events_are_emitted(
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    caplog.set_level(logging.INFO, logger="llm_router")

    with pytest.raises(ProviderError):
        _runtime(ScriptedAdapter([_retryable_error(), _retryable_error()])).query(
            "retry exhaustion"
        )

    adapter = ScriptedAdapter(
        [
            _result('{"answer": "x"}'),
            _result('{"answer": "y"}'),
            _result('{"answer": "z"}'),
        ]
    )
    with pytest.raises(ProviderError):
        _runtime(adapter).query("schema exhaustion", response_schema=Reply)

    payloads = _payloads(caplog.records)
    event_types = _event_types(caplog.records)
    exhausted_retry = [
        payload
        for payload in payloads
        if payload.get("event_type") == "llm_router.provider.retry.exhausted"
    ]
    assert "llm_router.provider.retry.exhausted" in event_types
    assert "llm_router.capability.schema.repair.exhausted" in event_types
    assert exhausted_retry
    assert exhausted_retry[0]["route_index"] == 0


def test_route_fallback_skip_and_wait_events_are_emitted(
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY_1", "nvidia-key-1")
    monkeypatch.setenv("NVIDIA_API_KEY_2", "nvidia-key-2")
    monkeypatch.setenv("GROQ_API_KEY_1", "groq-key-1")
    caplog.set_level(logging.INFO, logger="llm_router")

    RouterRuntime(
        spec=[
            RouterProfile(provider=Provider.GROQ, model=Model.LLAMA_SCOUT),
            RouterProfile(provider=Provider.NVIDIA, model=Model.LLAMA_MAVERICK),
        ],
        _executor=ScriptedRouteExecutor([RuntimeError("first failed")]),
        round_robin_start=False,
        shuffle_fallbacks=False,
    ).query("fallback")

    limited = RouterRuntime(
        spec=[
            RouterProfile(
                provider=Provider.NVIDIA,
                model=Model.LLAMA_MAVERICK,
                key_id=1,
            ),
            RouterProfile(
                provider=Provider.NVIDIA,
                model=Model.LLAMA_MAVERICK,
                key_id=2,
            ),
        ],
        _executor=ScriptedRouteExecutor(),
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=50.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    limited.query("first")
    limited.query("second")

    waiting = RouterRuntime(
        spec=RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.LLAMA_MAVERICK,
            key_id=1,
        ),
        _executor=ScriptedRouteExecutor(),
        round_robin_start=False,
        shuffle_fallbacks=False,
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=50.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    waiting.query("first")
    waiting.query("second")

    event_types = _event_types(caplog.records)
    assert "llm_router.routing.routes.expanded" in event_types
    assert "llm_router.routing.attempt.failed" in event_types
    assert "llm_router.routing.attempt.succeeded" in event_types
    assert "llm_router.routing.limit.blocked" in event_types
    assert "llm_router.routing.route.skipped" in event_types
    assert "llm_router.routing.limit.waiting" in event_types


def test_tool_failure_event_uses_safe_fields(
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    caplog.set_level(logging.INFO, logger="llm_router")
    adapter = ScriptedAdapter(
        [_result("", tool_calls=(ToolCall(name="explode", args={"value": 7}),))]
    )

    with pytest.raises(ToolExecutionError):
        _runtime(adapter).query(
            "SECRET_TOOL_PROMPT_SHOULD_NOT_APPEAR",
            tools=[explode],
            tool_choice="required",
        )

    event_types = _event_types(caplog.records)
    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert "llm_router.capability.tool.called" in event_types
    assert "llm_router.capability.tool.failed" in event_types
    assert "SECRET_TOOL_PROMPT_SHOULD_NOT_APPEAR" not in rendered
    assert '"value": 7' not in rendered


def test_tool_completed_event_is_emitted(
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    caplog.set_level(logging.INFO, logger="llm_router")
    adapter = ScriptedAdapter(
        [
            _result("", tool_calls=(ToolCall(name="ping", args={"value": 7}),)),
            _result("done"),
        ]
    )

    response = _runtime(adapter).query(
        "use tool",
        tools=[ping],
        tool_choice="required",
    )

    assert response.output_text == "done"
    assert "llm_router.capability.tool.completed" in _event_types(caplog.records)


def test_tool_round_limit_event_is_emitted(
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    caplog.set_level(logging.INFO, logger="llm_router")
    adapter = ScriptedAdapter(
        [_result("", tool_calls=(ToolCall(name="explode", args={"value": 7}),))]
    )

    response = _runtime(adapter).query(
        "use tool",
        tools=[explode],
        tool_choice="required",
        max_tool_rounds=0,
    )

    assert response.output_text == ""
    assert "llm_router.capability.tool.round_limit_reached" in _event_types(
        caplog.records
    )
