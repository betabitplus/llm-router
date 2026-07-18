from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import pytest
from pydantic import BaseModel, Field

from llm_router import (
    LLMRouterResponse,
    Model,
    Provider,
    ProviderError,
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
from llm_router._internal.runtime.router import RouterRuntime


class Reply(BaseModel):
    answer: str = Field(min_length=2)


class ScriptedAdapter:
    capabilities = ProviderCapabilities(supports_json_schema=True, supports_tools=True)

    def __init__(self, outcomes: Sequence[ProviderResult | Exception]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


def ping(*, value: int) -> dict[str, int]:
    return {"echo": value}


def explode(*, value: int) -> dict[str, int]:
    msg = f"tool exploded with value={value}"
    raise RuntimeError(msg)


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


def _executor(adapter: ScriptedAdapter) -> ProviderRouteExecutor:
    return ProviderRouteExecutor(
        config=_fast_config(),
        adapter_getter=lambda _provider, _config: adapter,
    )


def _runtime(
    adapter: ScriptedAdapter,
    *,
    spec: object | None = None,
    **kwargs: object,
) -> RouterRuntime:
    return RouterRuntime(
        spec=spec
        or RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        _executor=_executor(adapter),
        shuffle_fallbacks=False,
        round_robin_start=False,
        **kwargs,
    )


def _result(
    text: str,
    *,
    provider: Provider = Provider.OPENROUTER,
    model: Model = Model.DEEPSEEK_V3,
    tool_calls: tuple[ToolCall, ...] = (),
) -> ProviderResult:
    return ProviderResult(
        data={"text": text},
        provider=provider,
        model=model,
        provider_model=model.value,
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


def _permanent_error(provider: Provider, model: Model) -> ProviderError:
    failure = ProviderFailure(
        provider=provider,
        model=model,
        message="bad request",
        retryable=False,
        status_code=400,
        retry_reason="caller_or_auth_status",
    )
    return ProviderError(failure, provider, model, message=failure.message)


def test_retry_repair_and_response_normalization_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    adapter = ScriptedAdapter(
        [
            _retryable_error(),
            _result('{"answer": "x"}'),
            _result('{"answer": "ok"}'),
        ]
    )
    runtime = _runtime(adapter)

    response = runtime.query("reply", response_schema=Reply)

    assert isinstance(response, LLMRouterResponse)
    assert response.output_text == '{"answer": "ok"}'
    assert response.provider == "openrouter"
    assert response.model == "deepseek-chat-v3"
    assert response.data["parsed"] == {"answer": "ok"}
    assert len(adapter.requests) == 3
    assert len(response.routing_trace) == 1
    assert response.routing_trace[0].error_type is None


def test_text_sequence_content_preserves_separate_provider_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    adapter = ScriptedAdapter([_result("ok")])
    runtime = _runtime(adapter)

    response = runtime.query(["Follow instructions exactly.", "Reply ONLY with OK."])

    assert response.output_text == "ok"
    assert len(adapter.requests) == 1
    assert [message.parts[0].text for message in adapter.requests[0].messages] == [
        "Follow instructions exactly.",
        "Reply ONLY with OK.",
    ]


def test_route_fallback_remains_separate_from_same_provider_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY_1", "groq-key")
    monkeypatch.setenv("NVIDIA_API_KEY_1", "nvidia-key")
    first = ScriptedAdapter([_permanent_error(Provider.GROQ, Model.LLAMA_SCOUT)])
    second = ScriptedAdapter(
        [
            _result(
                "fallback-ok",
                provider=Provider.NVIDIA,
                model=Model.DEEPSEEK_V4_FLASH,
            )
        ]
    )

    def adapter_getter(provider: Provider, _config: object) -> ScriptedAdapter:
        return first if provider is Provider.GROQ else second

    executor = ProviderRouteExecutor(
        config=_fast_config(),
        adapter_getter=adapter_getter,
    )
    runtime = RouterRuntime(
        spec=[
            RouterProfile(provider=Provider.GROQ, model=Model.LLAMA_SCOUT),
            RouterProfile(provider=Provider.NVIDIA, model=Model.DEEPSEEK_V4_FLASH),
        ],
        _executor=executor,
        shuffle_fallbacks=False,
        round_robin_start=False,
    )

    response = runtime.query("hello")

    assert response.output_text == "fallback-ok"
    assert [attempt.provider for attempt in response.routing_trace] == [
        "groq",
        "nvidia",
    ]
    assert response.routing_trace[0].error_type == "ProviderError"
    assert response.routing_trace[1].error_type is None
    assert len(first.requests) == 1
    assert len(second.requests) == 1


def test_tool_failure_stops_before_another_provider_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    adapter = ScriptedAdapter(
        [_result("", tool_calls=(ToolCall(name="explode", args={"value": 7}),))]
    )
    runtime = _runtime(adapter)

    with pytest.raises(ToolExecutionError):
        runtime.query(
            "use tool",
            tools=[explode],
            tool_choice="required",
            max_tool_rounds=2,
        )

    assert len(adapter.requests) == 1


def test_tool_round_limit_returns_last_tool_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    adapter = ScriptedAdapter(
        [
            _result("", tool_calls=(ToolCall(name="ping", args={"value": 7}),)),
            _result("", tool_calls=(ToolCall(name="ping", args={"value": 7}),)),
        ]
    )
    runtime = _runtime(adapter)

    response = runtime.query(
        "use tool",
        tools=[ping],
        tool_choice="required",
        max_tool_rounds=2,
    )

    assert response.output_text == ""
    assert len(response.tool_trace) == 2
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "ping"
    assert response.tool_calls[0].args == {"value": 7}
    assert len(adapter.requests) == 2
