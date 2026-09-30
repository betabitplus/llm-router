# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION bc22a7f5ad518a96
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

from dataclasses import dataclass, field
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
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderCredential,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.providers.retry import classify_exception
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.requests import ResolvedRequest

pytestmark = pytest.mark.verification_kind("unit")


@dataclass(frozen=True)
class RouteStub:
    provider: Provider
    model: Model
    provider_model: str
    route_index: int


@dataclass(frozen=True)
class SettingsStub:
    response_schema: object | None = None
    tools: tuple[object, ...] | None = None
    tool_choice: str | None = None
    max_tool_rounds: int | None = None
    temperature: float | None = None
    seed: int | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)


class TransportFlakyAdapter:
    """Fail once with a classified transport error, then succeed."""

    def __init__(self, result: ProviderResult) -> None:
        self.capabilities = ProviderCapabilities()
        self.requests: list[ProviderRequest] = []
        self.result = result

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        if len(self.requests) == 1:
            transport_error = ConnectionResetError("reset by peer")
            decision = classify_exception(transport_error)
            failure = ProviderFailure(
                provider=request.provider,
                model=request.model,
                message="connection reset",
                retryable=decision.retryable,
                retry_reason=decision.reason,
            )
            raise ProviderError(
                failure,
                request.provider,
                request.model,
            ) from transport_error
        return self.result

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


class RecordingAdapterGetter:
    """Hand out one adapter and remember which provider asked for it."""

    def __init__(self, adapter: TransportFlakyAdapter) -> None:
        self.adapter = adapter
        self.providers: list[Provider] = []

    def __call__(
        self,
        provider: Provider,
        config: LLMRouterConfig,
    ) -> TransportFlakyAdapter:
        assert config.retry_policy.max_attempts == 3
        self.providers.append(provider)
        return self.adapter


def build_config() -> LLMRouterConfig:
    limits = ProviderLimits(
        rps=10.0,
        rpm=600.0,
        cooldown_seconds=1.0,
        cooldown_after_failures=3,
    )
    return LLMRouterConfig(
        default_provider=Provider.GROQ,
        default_model=Model.LLAMA_8B,
        default_key_id=1,
        defaults=BehaviorDefaults(
            retry_policy=RetryPolicy(
                min_wait_seconds=0.0,
                max_wait_seconds=0.0,
                max_attempts=3,
            ),
            policy=RouterPolicyDefaults(
                max_attempts=None,
                attempt_timeout_seconds=None,
                wait_for_cooldown_if_all_blocked=False,
                round_robin_start=False,
                shuffle_fallbacks=False,
                min_routes_for_fallback_shuffle=2,
                default_limits=limits,
            ),
            default_max_tool_rounds=1,
            structured_output_max_attempts=1,
            provider_limits=limits,
        ),
        catalog=ProviderCatalog(),
    )


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_retryable_transport_failure_is_retried_and_result_returned() -> None:
    expected = ProviderResult(
        data={"id": "chatcmpl-1"},
        provider=Provider.GROQ,
        model=Model.LLAMA_8B,
        provider_model="llama-3.1-8b-instant",
        output_text="hello after retry",
    )
    adapter = TransportFlakyAdapter(expected)
    getter = RecordingAdapterGetter(adapter)
    executor = ProviderRouteExecutor(config=build_config(), adapter_getter=getter)
    request = ResolvedRequest(
        request_id="req-retry-1",
        route=RouteStub(  # type: ignore[arg-type]
            provider=Provider.GROQ,
            model=Model.LLAMA_8B,
            provider_model="llama-3.1-8b-instant",
            route_index=0,
        ),
        settings=SettingsStub(),  # type: ignore[arg-type]
        key=ProviderCredential(  # type: ignore[arg-type]
            key_id=1,
            env_var="GROQ_API_KEY",
            value="gsk-test-value",
        ),
        messages=("Say hello",),
        content="Say hello",
    )

    response = executor.execute(request)

    assert getter.providers == [Provider.GROQ]
    assert len(adapter.requests) == 2
    assert adapter.requests[0] == adapter.requests[1]
    assert adapter.requests[1].request_id == "req-retry-1"
    assert response.output_text == "hello after retry"
    assert response.provider == Provider.GROQ
    assert response.model == Model.LLAMA_8B
