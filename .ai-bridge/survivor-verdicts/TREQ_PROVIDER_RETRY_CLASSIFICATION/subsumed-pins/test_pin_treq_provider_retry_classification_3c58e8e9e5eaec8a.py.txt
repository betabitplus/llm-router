# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 3c58e8e9e5eaec8a
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider, ProviderLimits
from llm_router._internal.config import (
    BehaviorDefaults,
    LLMRouterConfig,
    ProviderCatalog,
    RetryPolicy,
    RouterPolicyDefaults,
)
from llm_router._internal.providers.base import ProviderRequest, ProviderResult
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.requests import ResolvedRequest

pytestmark = pytest.mark.verification_kind("unit")

EVENT = "llm_router.provider.retry.exhausted"


class TransientCauseError(Exception):
    retryable = True


class PermanentCauseError(Exception):
    retryable = False


class FailingAdapter:
    def __init__(self, error: Exception) -> None:
        self.calls = 0
        self._error = error

    def execute(self, request: ProviderRequest) -> ProviderResult:
        assert request.request_id == "req-1"
        self.calls += 1
        raise self._error


@dataclass
class StubRoute:
    route_index: int
    model: Model
    provider: Provider
    provider_model: str


@dataclass
class StubSettings:
    response_schema: object | None = None
    tools: object | None = None
    tool_choice: object | None = None
    max_tool_rounds: int | None = None
    kwargs: dict[str, object] | None = None
    temperature: float | None = None
    seed: int | None = None


@dataclass
class StubKey:
    key_id: int
    env_var: str
    value: str


def _limits() -> ProviderLimits:
    return ProviderLimits(
        rps=10.0, rpm=100.0, cooldown_seconds=1.0, cooldown_after_failures=3
    )


def _config() -> LLMRouterConfig:
    defaults = BehaviorDefaults(
        retry_policy=RetryPolicy(
            min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=2
        ),
        policy=RouterPolicyDefaults(
            max_attempts=1,
            attempt_timeout_seconds=None,
            wait_for_cooldown_if_all_blocked=False,
            round_robin_start=False,
            shuffle_fallbacks=False,
            min_routes_for_fallback_shuffle=2,
            default_limits=_limits(),
        ),
        default_max_tool_rounds=1,
        structured_output_max_attempts=1,
        provider_limits=_limits(),
    )
    return LLMRouterConfig(
        default_provider=Provider.GROQ,
        default_model=Model.LLAMA_8B,
        default_key_id=1,
        defaults=defaults,
        catalog=ProviderCatalog(),
    )


def _request() -> ResolvedRequest:
    route: Any = StubRoute(
        route_index=0,
        model=Model.LLAMA_8B,
        provider=Provider.GROQ,
        provider_model="llama-3.1-8b-instant",
    )
    settings: Any = StubSettings(kwargs={})
    key: Any = StubKey(key_id=1, env_var="LLM_ROUTER_VALUE", value="v")
    return ResolvedRequest(
        request_id="req-1",
        route=route,
        settings=settings,
        key=key,
        messages=("hello",),
        content="hello",
    )


def _run(error: Exception, caplog: pytest.LogCaptureFixture) -> tuple[int, str]:
    caplog.clear()
    adapter = FailingAdapter(error)

    def getter(provider: Provider, config: LLMRouterConfig) -> FailingAdapter:
        assert provider is Provider.GROQ
        assert config is not None
        return adapter

    executor = ProviderRouteExecutor(config=_config(), adapter_getter=getter)
    with pytest.raises(ProviderError):
        executor.execute(_request())
    logged = " ".join(
        record.getMessage() + " " + str(record.msg) + " " + str(record.__dict__)
        for record in caplog.records
    )
    return adapter.calls, logged


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_retry_exhausted_event_only_for_retryable_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(0)
    provider = Provider.GROQ
    model = Model.LLAMA_8B
    permanent = ProviderError(PermanentCauseError("bad request"), provider, model)
    transient = ProviderError(TransientCauseError("busy"), provider, model)

    permanent_calls, permanent_log = _run(permanent, caplog)
    transient_calls, transient_log = _run(transient, caplog)

    assert permanent_calls == 1
    assert EVENT not in permanent_log
    assert transient_calls == 2
    assert EVENT in transient_log
