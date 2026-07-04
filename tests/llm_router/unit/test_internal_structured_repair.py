from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import pytest
from pydantic import BaseModel, Field

from llm_router import Model, Provider, ProviderError, ProviderLimits
from llm_router._internal.config import build_default_config
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.effective_settings import EffectiveSettings
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.limiter import ResolvedKey
from llm_router._internal.runtime.requests import ResolvedRequest
from llm_router._internal.runtime.routes import ExpandedRoute, RouteGenerationDefaults


class TicketSummary(BaseModel):
    incident_id: str
    severity: str = Field(min_length=4)
    tags: list[str] = Field(min_length=2)


class ScriptedAdapter:
    capabilities = ProviderCapabilities(supports_json_schema=True)

    def __init__(self, outcomes: Sequence[ProviderResult]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        return self.outcomes.pop(0)

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


def _provider_result(text: str) -> ProviderResult:
    return ProviderResult(
        data={"text": text},
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        output_text=text,
    )


def _request(*, response_schema: object = TicketSummary) -> ResolvedRequest:
    limits = ProviderLimits(
        rps=1_000_000.0,
        rpm=1_000_000.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=0,
    )
    settings = EffectiveSettings(
        key_id=1,
        temperature=0.0,
        seed=1,
        response_schema=response_schema,
        tools=None,
        tool_choice=None,
        max_tool_rounds=2,
        kwargs={},
        max_attempts=None,
        attempt_timeout_seconds=None,
        wait_for_cooldown_if_all_blocked=True,
        round_robin_start=False,
        shuffle_fallbacks=False,
        default_limits=limits,
        limits_by_provider={Provider.QWENCHAT: limits},
    )
    return ResolvedRequest(
        request_id="req-1",
        route=ExpandedRoute(
            route_index=0,
            model=Model.QWEN_MAX_LATEST,
            provider=Provider.QWENCHAT,
            provider_model="qwen-max-latest",
            defaults=RouteGenerationDefaults(key_id=1),
        ),
        settings=settings,
        key=ResolvedKey(
            key_id=1,
            env_var="QWENCHAT_API_KEY_1",
            value="secret",
        ),
        messages=("Return incident JSON.",),
        content="Return incident JSON.",
    )


def _executor(adapter: ScriptedAdapter) -> ProviderRouteExecutor:
    config = build_default_config()
    fast_retry = RetryPolicy(
        min_wait_seconds=0.001,
        max_wait_seconds=0.001,
        max_attempts=2,
    )
    fast_config = replace(
        config,
        defaults=replace(config.defaults, retry_policy=fast_retry),
    )
    return ProviderRouteExecutor(
        config=fast_config,
        adapter_getter=lambda _provider, _config: adapter,
    )


def test_structured_output_repairs_invalid_first_response() -> None:
    adapter = ScriptedAdapter(
        [
            _provider_result('{"incident_id": "INC-2048"}'),
            _provider_result(
                '{"incident_id": "INC-2048", "severity": "SEV2", "tags": ["db", "api"]}'
            ),
        ]
    )

    response = _executor(adapter).execute(_request())

    assert response.output_text == (
        '{"incident_id": "INC-2048", "severity": "SEV2", "tags": ["db", "api"]}'
    )
    assert response.data["parsed"] == {
        "incident_id": "INC-2048",
        "severity": "SEV2",
        "tags": ["db", "api"],
    }
    assert len(adapter.requests) == 2
    second_request_text = "\n".join(
        part.text
        for message in adapter.requests[1].messages
        for part in message.parts
        if part.kind == "text"
    )
    assert (
        "The previous response did not match the required schema."
        in second_request_text
    )
    assert "INC-2048" in second_request_text
    assert "minLength" in second_request_text
    assert "minItems" in second_request_text


def test_structured_output_exhaustion_raises_public_provider_error() -> None:
    adapter = ScriptedAdapter(
        [
            _provider_result('{"incident_id": "INC-2048"}'),
            _provider_result('{"incident_id": "INC-2048"}'),
            _provider_result('{"incident_id": "INC-2048"}'),
        ]
    )

    with pytest.raises(ProviderError, match="Structured output validation failed"):
        _executor(adapter).execute(_request())

    assert len(adapter.requests) == 3
    assert {request.provider for request in adapter.requests} == {Provider.QWENCHAT}


def test_no_schema_skips_structured_repair() -> None:
    adapter = ScriptedAdapter([_provider_result("plain text")])

    response = _executor(adapter).execute(_request(response_schema=None))

    assert response.output_text == "plain text"
    assert len(adapter.requests) == 1
