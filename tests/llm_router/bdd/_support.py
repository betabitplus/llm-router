"""Small deterministic fakes shared by hermetic living specifications."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import replace

import pytest

from llm_router import LLMRouterResponse, Model, Provider, ProviderError, ToolCall
from llm_router._internal.config import get_config
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers import gemini_webapi as gemini_webapi_provider
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.requests import ResolvedRequest

RouteOutcome = Callable[[ResolvedRequest], LLMRouterResponse] | BaseException


def prepare_gemini_webapi_runtime(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Use fake cookie metadata for replay and real browser cookies for live runs."""
    if request.config.getoption("--disable-recording", default=False):
        from tests.llm_router.support.media.gemini_webapi import require_runtime

        require_runtime()
        return
    monkeypatch.setattr(
        gemini_webapi_provider,
        "cookie_lookup",
        lambda: {"__Secure-1PSID": "replay", "__Secure-1PSIDTS": "replay"},
    )


class ScriptedRouteExecutor:
    """Return or raise one scripted route outcome per attempt."""

    def __init__(self, outcomes: list[RouteOutcome] | None = None) -> None:
        self.outcomes = list(outcomes or [])
        self.requests: list[ResolvedRequest] = []

    def execute(self, request: ResolvedRequest) -> LLMRouterResponse:
        self.requests.append(request)
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome(request)
        return route_response(request, text=f"route-{request.route.route_index}")

    async def aexecute(self, request: ResolvedRequest) -> LLMRouterResponse:
        return self.execute(request)


class SlowFirstRouteExecutor(ScriptedRouteExecutor):
    """Make only the first route exceed a short attempt timeout."""

    def execute(self, request: ResolvedRequest) -> LLMRouterResponse:
        self.requests.append(request)
        if request.route.route_index == 0:
            time.sleep(0.25)
            return route_response(request, text="slow")
        return route_response(request, text="fast")


def route_response(request: ResolvedRequest, *, text: str) -> LLMRouterResponse:
    return LLMRouterResponse(
        data={"request_id": request.request_id},
        provider=request.route.provider.value,
        model=request.route.model.value,
        output_text=text,
    )


class ScriptedAdapter:
    """Provider adapter that consumes deterministic results or failures."""

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


def provider_result(
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


def retryable_error() -> ProviderError:
    failure = ProviderFailure(
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        message="temporary failure",
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


def permanent_error() -> ProviderError:
    failure = ProviderFailure(
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        message="permanent failure",
        retryable=False,
        status_code=400,
        retry_reason="caller_or_auth_status",
    )
    return ProviderError(
        failure,
        Provider.OPENROUTER,
        Model.DEEPSEEK_V3,
        message=failure.message,
    )


def provider_executor(
    adapter: ScriptedAdapter,
    *,
    repair_attempts: int = 2,
) -> ProviderRouteExecutor:
    config = get_config()
    config = replace(
        config,
        defaults=replace(
            config.defaults,
            retry_policy=RetryPolicy(
                min_wait_seconds=0.001,
                max_wait_seconds=0.001,
                max_attempts=2,
            ),
            structured_output_max_attempts=repair_attempts,
        ),
    )
    return ProviderRouteExecutor(
        config=config,
        adapter_getter=lambda _provider, _config: adapter,
    )
