# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION dad9cc03506dec74
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.config import RetryPolicy, build_default_config
from llm_router._internal.providers.base import ProviderRequest, ProviderResult
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.requests import ResolvedRequest

pytestmark = pytest.mark.verification_kind("unit")


@dataclass(frozen=True)
class _Route:
    route_index: int
    model: Model
    provider: Provider
    provider_model: str


@dataclass(frozen=True)
class _Settings:
    temperature: float | None
    seed: int | None
    response_schema: object | None
    tools: tuple[object, ...] | None
    tool_choice: str | None
    max_tool_rounds: int | None
    kwargs: dict[str, object]


@dataclass(frozen=True)
class _Key:
    key_id: int
    env_var: str
    value: str


class _TransportFailureError(ConnectionResetError):
    retryable = True


class _FlakyAdapter:
    def __init__(self, result: ProviderResult) -> None:
        self.result = result
        self.calls: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.calls.append(request)
        if len(self.calls) == 1:
            msg = "reset by peer"
            raise ProviderError(
                _TransportFailureError(msg),
                request.provider,
                request.model,
            )
        return self.result


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_transport_exception_is_retried_on_resolved_adapter() -> None:
    base = build_default_config()
    config = replace(
        base,
        defaults=replace(
            base.defaults,
            retry_policy=RetryPolicy(
                min_wait_seconds=0.0,
                max_wait_seconds=0.0,
                max_attempts=3,
            ),
        ),
    )
    expected = ProviderResult(
        data={},
        provider=Provider.GROQ,
        model=Model.LLAMA_8B,
        provider_model="llama-8b",
        output_text="hello",
    )
    adapter = _FlakyAdapter(expected)

    def getter(_provider: Provider, _config: Any) -> _FlakyAdapter:
        return adapter

    executor = ProviderRouteExecutor(
        config=config,
        adapter_getter=getter,  # type: ignore[arg-type]
    )
    request = ResolvedRequest(
        request_id="req-1",
        route=_Route(  # type: ignore[arg-type]
            route_index=0,
            model=Model.LLAMA_8B,
            provider=Provider.GROQ,
            provider_model="llama-8b",
        ),
        settings=_Settings(  # type: ignore[arg-type]
            temperature=None,
            seed=None,
            response_schema=None,
            tools=None,
            tool_choice=None,
            max_tool_rounds=None,
            kwargs={},
        ),
        key=_Key(key_id=1, env_var="LLM_ENV", value="value"),  # type: ignore[arg-type]
        messages=("hello",),
        content="hello",
    )

    response = executor.execute(request)

    assert len(adapter.calls) == 2
    assert response.output_text == "hello"
