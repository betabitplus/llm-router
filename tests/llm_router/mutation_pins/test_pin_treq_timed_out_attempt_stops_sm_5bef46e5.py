# mutation-pin: TREQ_TIMED_OUT_ATTEMPT_STOPS SM-5BEF46E5
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.config import RetryPolicy
from llm_router._internal.providers.base import ProviderRequest, ProviderResult
from llm_router._internal.runtime.errors import AttemptLeftError
from llm_router._internal.runtime.executor import ProviderRouteExecutor

pytestmark = pytest.mark.verification_kind("unit")


class LeftFlag:
    """The part of an event the executor reads and the adapter sets."""

    def __init__(self) -> None:
        self.flag = False

    def set(self) -> None:
        self.flag = True

    def is_set(self) -> bool:
        return self.flag


class TransientCauseError(ConnectionResetError):
    retryable = True


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


RESULT = ProviderResult(
    data={},
    provider=Provider.GROQ,
    model=Model.LLAMA_8B,
    provider_model="llama-3.1-8b-instant",
    output_text="late answer",
)


class LeavingAdapter:
    """Leave the attempt during the first call, which then fails transiently."""

    def __init__(self, left: LeftFlag, leave_on_call: bool) -> None:
        self.left = left
        self.leave_on_call = leave_on_call
        self.calls = 0

    def execute(self, request: ProviderRequest) -> ProviderResult:
        assert request.request_id == "req-1"
        self.calls += 1
        if self.leave_on_call:
            self.left.set()
            cause = ProviderError(
                TransientCauseError("reset"), Provider.GROQ, Model.LLAMA_8B
            )
            raise cause
        return RESULT


def build_executor(adapter: LeavingAdapter) -> ProviderRouteExecutor:
    def getter(_provider: Provider, _config: object) -> LeavingAdapter:
        return adapter

    policy = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=3)
    return ProviderRouteExecutor(
        config=Config(retry_policy=policy),  # type: ignore[arg-type]
        adapter_getter=getter,  # type: ignore[arg-type]
    )


@pytest.mark.verifies("TREQ_TIMED_OUT_ATTEMPT_STOPS[revision==1]")
def test_left_attempt_sends_no_provider_request() -> None:
    left = LeftFlag()
    left.set()
    adapter = LeavingAdapter(left, leave_on_call=False)
    executor = build_executor(adapter)
    with pytest.raises(ProviderError, match=r"AttemptLeftError") as info:
        executor.execute(Resolved(), left=left)  # type: ignore[arg-type]
    assert isinstance(info.value.__cause__, AttemptLeftError)
    assert adapter.calls == 0


@pytest.mark.verifies("TREQ_TIMED_OUT_ATTEMPT_STOPS[revision==1]")
def test_left_attempt_starts_no_provider_retry() -> None:
    left = LeftFlag()
    adapter = LeavingAdapter(left, leave_on_call=True)
    executor = build_executor(adapter)
    with pytest.raises(ProviderError, match=r"AttemptLeftError") as info:
        executor.execute(Resolved(), left=left)  # type: ignore[arg-type]
    assert isinstance(info.value.__cause__, AttemptLeftError)
    assert adapter.calls == 1
