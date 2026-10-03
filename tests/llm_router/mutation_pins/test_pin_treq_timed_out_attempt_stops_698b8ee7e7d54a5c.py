# mutation-pin: TREQ_TIMED_OUT_ATTEMPT_STOPS 698b8ee7e7d54a5c
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.config import RetryPolicy
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.executor import ProviderRouteExecutor

pytestmark = pytest.mark.verification_kind("unit")


class LeftFlag:
    """The part of an event the executor reads."""

    def is_set(self) -> bool:
        return False


@dataclass(frozen=True)
class Config:
    retry_policy: RetryPolicy


@dataclass(frozen=True)
class Route:
    route_index: int = 0
    model: Model = Model.LLAMA_8B
    provider: Provider = Provider.GROQ
    provider_model: str = "llama-3.1-8b-instant"


@dataclass(frozen=True)
class Settings:
    temperature: float | None = None
    seed: int | None = None
    response_schema: object | None = None
    tools: tuple[object, ...] | None = None
    tool_choice: str | None = None
    max_tool_rounds: int | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Credential:
    key_id: int = 1
    env_var: str = "GROQ_API_ENV"
    value: str = "v"


@dataclass(frozen=True)
class Resolved:
    request_id: str = "req-1"
    route: Route = field(default_factory=Route)
    settings: Settings = field(default_factory=Settings)
    key: Credential = field(default_factory=Credential)
    messages: tuple[str, ...] = ("hello",)
    content: object = "hello"


CAPABILITIES = ProviderCapabilities(
    supports_images=True,
    supports_files=False,
    supports_json_schema=True,
    supports_tools=True,
)


class FailingAdapter:
    """Fails at once, non-retryably, so the traceback shows its caller."""

    def __init__(self) -> None:
        self.capabilities = CAPABILITIES

    def execute(self, request: ProviderRequest) -> ProviderResult:
        msg = f"stop {request.request_id}"
        raise ValueError(msg)


def build_executor(adapter: FailingAdapter) -> ProviderRouteExecutor:
    def getter(_provider: Provider, _config: object) -> FailingAdapter:
        return adapter

    policy = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=1)
    return ProviderRouteExecutor(
        config=Config(retry_policy=policy),  # type: ignore[arg-type]
        adapter_getter=getter,  # type: ignore[arg-type]
    )


@pytest.mark.verifies("TREQ_TIMED_OUT_ATTEMPT_STOPS[revision==1]")
def test_guard_around_adapter_exposes_wrapped_capabilities() -> None:
    adapter = FailingAdapter()
    executor = build_executor(adapter)
    with pytest.raises(ProviderError, match=r"ValueError") as info:
        executor.execute(Resolved(), left=LeftFlag())  # type: ignore[arg-type]
    cause = info.value.__cause__
    assert cause is not None
    trace = cause.__traceback__
    guard = None
    while trace is not None:
        if trace.tb_frame.f_locals.get("self") is adapter:
            caller = trace.tb_frame.f_back
            assert caller is not None
            guard = caller.f_locals["self"]
        trace = trace.tb_next
    assert guard is not None
    assert guard is not adapter
    assert guard.capabilities == CAPABILITIES
