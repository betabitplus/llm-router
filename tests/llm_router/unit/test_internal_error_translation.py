from __future__ import annotations

from collections.abc import Sequence

import pytest

from llm_router import Model, Provider, ProviderError, ToolCall, ToolExecutionError
from llm_router._internal.config import build_default_config
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderFailure,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from tests.llm_router.unit.test_internal_structured_repair import _request


class RaisingAdapter:
    capabilities = ProviderCapabilities(supports_tools=True)

    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        raise self.exc

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


class ScriptedAdapter:
    capabilities = ProviderCapabilities(supports_tools=True)

    def __init__(self, results: Sequence[ProviderResult]) -> None:
        self.results = list(results)
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        return self.results.pop(0)

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


def explode(*, value: int) -> dict[str, int]:
    msg = f"tool exploded with value={value}"
    raise RuntimeError(msg)


def _executor(adapter: object) -> ProviderRouteExecutor:
    return ProviderRouteExecutor(
        config=build_default_config(),
        adapter_getter=lambda _provider, _config: adapter,
    )


def test_unwrapped_provider_exception_becomes_public_provider_error() -> None:
    adapter = RaisingAdapter(RuntimeError("sdk broke"))

    with pytest.raises(ProviderError) as exc_info:
        _executor(adapter).execute(_request(response_schema=None))

    assert exc_info.value.provider == Provider.QWENCHAT
    assert exc_info.value.model == Model.QWEN_MAX_LATEST
    assert "sdk broke" in str(exc_info.value)


def test_existing_provider_error_crosses_boundary_once() -> None:
    failure = ProviderFailure(
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        message="bad request",
        retryable=False,
        status_code=400,
        retry_reason="caller_or_auth_status",
    )
    provider_error = ProviderError(
        failure,
        Provider.QWENCHAT,
        Model.QWEN_MAX_LATEST,
        message=failure.message,
    )
    adapter = RaisingAdapter(provider_error)

    with pytest.raises(ProviderError) as exc_info:
        _executor(adapter).execute(_request(response_schema=None))

    assert exc_info.value is provider_error
    assert len(adapter.requests) == 1


def test_local_tool_failure_surfaces_as_tool_execution_error() -> None:
    adapter = ScriptedAdapter(
        [
            ProviderResult(
                data={},
                provider=Provider.QWENCHAT,
                model=Model.QWEN_MAX_LATEST,
                provider_model="qwen-max-latest",
                output_text="",
                tool_calls=(ToolCall(name="explode", args={"value": 7}),),
            )
        ]
    )
    request = _request(response_schema=None)
    request = type(request)(
        request_id=request.request_id,
        route=request.route,
        settings=type(request.settings)(
            key_id=request.settings.key_id,
            temperature=request.settings.temperature,
            seed=request.settings.seed,
            response_schema=request.settings.response_schema,
            tools=(explode,),
            tool_choice="required",
            max_tool_rounds=2,
            kwargs=request.settings.kwargs,
            max_attempts=request.settings.max_attempts,
            attempt_timeout_seconds=request.settings.attempt_timeout_seconds,
            wait_for_cooldown_if_all_blocked=(
                request.settings.wait_for_cooldown_if_all_blocked
            ),
            round_robin_start=request.settings.round_robin_start,
            shuffle_fallbacks=request.settings.shuffle_fallbacks,
            default_limits=request.settings.default_limits,
            limits_by_provider=request.settings.limits_by_provider,
        ),
        key=request.key,
        messages=request.messages,
        content=request.content,
    )

    with pytest.raises(ToolExecutionError) as exc_info:
        _executor(adapter).execute(request)

    assert "explode" in str(exc_info.value)
    assert "value=7" in str(exc_info.value)
    assert len(adapter.requests) == 1
