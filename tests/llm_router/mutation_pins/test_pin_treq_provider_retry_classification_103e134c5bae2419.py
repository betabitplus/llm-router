# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 103e134c5bae2419
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import dataclass

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
from llm_router._internal.providers.base import (
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.requests import (
    EffectiveSettings,
    ExpandedRoute,
    ResolvedKey,
    ResolvedRequest,
)

pytestmark = pytest.mark.verification_kind("unit")

LIMITS = ProviderLimits(
    rps=100.0,
    rpm=6000.0,
    cooldown_seconds=1.0,
    cooldown_after_failures=3,
)


@dataclass(frozen=True)
class RouteDefaultsStub:
    key_id: int


class TransportFailureError(ConnectionResetError):
    """Transport error carrying the retryable flag adapters attach."""

    retryable = True


class FlakyAdapter:
    """Fails once with a transport error, then returns the provider result."""

    def __init__(self, result: ProviderResult) -> None:
        self.calls: list[ProviderRequest] = []
        self.result = result

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.calls.append(request)
        if len(self.calls) == 1:
            raise ProviderError(
                TransportFailureError("connection reset by peer"),
                request.provider,
                request.model,
            )
        return self.result

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


def _config() -> LLMRouterConfig:
    retry = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=3)
    policy = RouterPolicyDefaults(
        max_attempts=None,
        attempt_timeout_seconds=None,
        wait_for_cooldown_if_all_blocked=False,
        round_robin_start=False,
        shuffle_fallbacks=False,
        min_routes_for_fallback_shuffle=2,
        default_limits=LIMITS,
    )
    defaults = BehaviorDefaults(
        retry_policy=retry,
        policy=policy,
        default_max_tool_rounds=1,
        structured_output_max_attempts=1,
        provider_limits=LIMITS,
    )
    return LLMRouterConfig(
        default_provider=Provider.GROQ,
        default_model=Model.LLAMA_8B,
        default_key_id=1,
        defaults=defaults,
        catalog=ProviderCatalog(),
    )


def _settings() -> EffectiveSettings:
    return EffectiveSettings(
        key_id=1,
        temperature=None,
        seed=None,
        response_schema=None,
        tools=None,
        tool_choice=None,
        max_tool_rounds=None,
        kwargs={},
        max_attempts=None,
        attempt_timeout_seconds=None,
        wait_for_cooldown_if_all_blocked=False,
        round_robin_start=False,
        shuffle_fallbacks=False,
        default_limits=LIMITS,
        limits_by_provider={},
    )


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_transport_error_is_retried_and_result_is_returned() -> None:
    result = ProviderResult(
        data={},
        provider=Provider.GROQ,
        model=Model.LLAMA_8B,
        provider_model="llama-3.1-8b-instant",
        output_text="hello back",
    )
    adapter = FlakyAdapter(result)
    executor = ProviderRouteExecutor(
        config=_config(),
        adapter_getter=lambda _provider, _config: adapter,
    )
    route = ExpandedRoute(
        route_index=0,
        model=Model.LLAMA_8B,
        provider=Provider.GROQ,
        provider_model="llama-3.1-8b-instant",
        defaults=RouteDefaultsStub(key_id=1),  # type: ignore[arg-type]
    )
    resolved = ResolvedRequest(
        request_id="req-1",
        route=route,
        settings=_settings(),
        key=ResolvedKey(key_id=1, env_var="GROQ_API_KEY_1", value="v"),
        messages=("hello",),
        content=("hello",),
    )

    response = executor.execute(resolved)

    assert len(adapter.calls) == 2
    assert response.output_text == "hello back"
