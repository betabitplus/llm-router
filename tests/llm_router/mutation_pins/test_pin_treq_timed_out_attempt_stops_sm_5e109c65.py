# mutation-pin: TREQ_TIMED_OUT_ATTEMPT_STOPS SM-5E109C65
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Protocol

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider, ToolCall
from llm_router._internal.config import LLMRouterConfig, RetryPolicy, get_config
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderCredential,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.errors import AttemptLeftError
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.requests import ResolvedRequest

pytestmark = pytest.mark.verification_kind("unit")

PROVIDER_MODEL = "deepseek/deepseek-chat"
PROMPT = "What is the weather in Paris?"


class LeftFlag:
    """What the router sets once it leaves the attempt at its timeout."""

    def __init__(self) -> None:
        self.left = False

    def set(self) -> None:
        self.left = True

    def is_set(self) -> bool:
        return self.left


@dataclass(frozen=True)
class RouteStub:
    provider: Provider = Provider.OPENROUTER
    model: Model = Model.DEEPSEEK_V3
    provider_model: str = PROVIDER_MODEL
    route_index: int = 0


@dataclass(frozen=True)
class SettingsStub:
    tools: tuple[object, ...] | None = None
    max_tool_rounds: int | None = None
    response_schema: object | None = None
    tool_choice: str | None = None
    temperature: float | None = None
    seed: int | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)


class Step(Protocol):
    def __call__(self) -> ProviderResult: ...


def provider_result(
    *, output_text: str, tool_calls: tuple[ToolCall, ...] = ()
) -> ProviderResult:
    return ProviderResult(
        data={"id": "chatcmpl-1"},
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model=PROVIDER_MODEL,
        output_text=output_text,
        tool_calls=tool_calls,
    )


class RecordingAdapter:
    """Answer each provider request with the next scripted step."""

    def __init__(self, steps: list[Step]) -> None:
        self.capabilities = ProviderCapabilities(supports_tools=True)
        self.steps = steps
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        return self.steps[len(self.requests) - 1]()

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


def fast_retry_config() -> LLMRouterConfig:
    """The installed config, with same-route retries that do not wait."""
    base = get_config()
    policy = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=3)
    return replace(base, defaults=replace(base.defaults, retry_policy=policy))


def run_attempt(
    adapter: RecordingAdapter, left: LeftFlag, settings: SettingsStub
) -> None:
    def adapter_getter(provider: Provider, config: LLMRouterConfig) -> RecordingAdapter:
        assert provider is Provider.OPENROUTER
        assert config.retry_policy.max_attempts == 3
        return adapter

    executor = ProviderRouteExecutor(
        config=fast_retry_config(), adapter_getter=adapter_getter
    )
    resolved = ResolvedRequest(
        request_id="req-left-attempt",
        route=RouteStub(),  # type: ignore[arg-type]
        settings=settings,  # type: ignore[arg-type]
        key=ProviderCredential(  # type: ignore[arg-type]
            key_id=1,
            env_var="OPENROUTER_API_KEY_1",
            value="openrouter-test-value",
        ),
        messages=(PROMPT,),
        content=PROMPT,
    )
    executor.execute(resolved, left=left)  # type: ignore[arg-type]


@pytest.mark.verifies("TREQ_TIMED_OUT_ATTEMPT_STOPS[revision==1]")
def test_attempt_left_during_tool_call_sends_no_follow_up_request() -> None:
    left = LeftFlag()
    tool_runs: list[str] = []

    def look_up_weather(city: str) -> str:
        tool_runs.append(city)
        # The attempt timeout passes while the tool runs: the router leaves.
        left.set()
        return "sunny"

    weather_call = ToolCall(id="call-1", name="look_up_weather", args={"city": "Paris"})
    adapter = RecordingAdapter(
        [
            lambda: provider_result(output_text="", tool_calls=(weather_call,)),
            lambda: provider_result(output_text="late follow-up answer"),
        ]
    )

    with pytest.raises(ProviderError, match=r"AttemptLeftError") as info:
        run_attempt(
            adapter,
            left,
            SettingsStub(tools=(look_up_weather,), max_tool_rounds=3),
        )

    assert isinstance(info.value.cause, AttemptLeftError)
    assert tool_runs == ["Paris"]
    # The follow-up after the tool round never reaches the provider.
    assert len(adapter.requests) == 1


@pytest.mark.verifies("TREQ_TIMED_OUT_ATTEMPT_STOPS[revision==1]")
def test_attempt_left_during_request_starts_no_provider_retry() -> None:
    left = LeftFlag()

    def fails_after_router_left() -> ProviderResult:
        # The request was in flight when the router left; it fails retryably.
        left.set()
        failure = ProviderFailure(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            message="service unavailable",
            retryable=True,
            status_code=503,
        )
        raise ProviderError(failure, Provider.OPENROUTER, Model.DEEPSEEK_V3)

    adapter = RecordingAdapter(
        [
            fails_after_router_left,
            lambda: provider_result(output_text="late retry answer"),
            lambda: provider_result(output_text="late retry answer"),
        ]
    )

    with pytest.raises(ProviderError, match=r"AttemptLeftError") as info:
        run_attempt(adapter, left, SettingsStub())

    assert isinstance(info.value.cause, AttemptLeftError)
    # The retry the failure would earn never reaches the provider.
    assert len(adapter.requests) == 1
