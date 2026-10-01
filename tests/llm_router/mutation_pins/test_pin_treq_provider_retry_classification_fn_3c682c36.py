# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION FN-3C682C36
# pinned-by: delegate, 6 pins of ProviderRouteExecutor._execute_provider_sync
# kills: 103e134c5bae2419 1cb6c482c58e73ea 3c58e8e9e5eaec8a SM-F4AC62D8 bc22a7f5ad518a96
# kills: dad9cc03506dec74
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.config import RetryPolicy
from llm_router._internal.providers.base import ProviderRequest, ProviderResult
from llm_router._internal.runtime.executor import ProviderRouteExecutor

pytestmark = pytest.mark.verification_kind("unit")

EVENT = "llm_router.provider.retry.exhausted"


class TransientCauseError(ConnectionResetError):
    retryable = True


class PermanentCauseError(Exception):
    retryable = False


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
    output_text="hello back",
)


class ScriptedAdapter:
    """Raise the error for the first `failures` calls, then return RESULT."""

    def __init__(self, error: Exception, failures: int) -> None:
        self.error = error
        self.failures = failures
        self.calls = 0

    def execute(self, request: ProviderRequest) -> ProviderResult:
        assert request.request_id == "req-1"
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return RESULT


def build_executor(adapter: ScriptedAdapter) -> ProviderRouteExecutor:
    def getter(_provider: Provider, _config: object) -> ScriptedAdapter:
        return adapter

    policy = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=2)
    return ProviderRouteExecutor(
        config=Config(retry_policy=policy),  # type: ignore[arg-type]
        adapter_getter=getter,  # type: ignore[arg-type]
    )


def wrapped(cause: Exception) -> ProviderError:
    return ProviderError(cause, Provider.GROQ, Model.LLAMA_8B)


def event_logged(caplog: pytest.LogCaptureFixture) -> bool:
    return any(
        EVENT in record.getMessage() or EVENT in str(record.__dict__)
        for record in caplog.records
    )


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_transport_error_retried_then_result_returned() -> None:
    adapter = ScriptedAdapter(wrapped(TransientCauseError("reset")), failures=1)
    response = build_executor(adapter).execute(Resolved())  # type: ignore[arg-type]
    assert adapter.calls == 2
    assert response.output_text == "hello back"


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_exhausted_transient_logs_event_and_chains(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(0)
    cause = wrapped(TransientCauseError("busy"))
    adapter = ScriptedAdapter(cause, failures=10)
    with pytest.raises(ProviderError, match=r".*") as info:
        build_executor(adapter).execute(Resolved())  # type: ignore[arg-type]
    assert adapter.calls == 2
    assert info.value.__cause__ is cause
    assert event_logged(caplog)


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_permanent_failures_not_retried_and_no_exhausted_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(0)
    permanent = wrapped(PermanentCauseError("bad request"))
    adapter = ScriptedAdapter(permanent, failures=10)
    with pytest.raises(ProviderError, match=r".*") as info:
        build_executor(adapter).execute(Resolved())  # type: ignore[arg-type]
    assert adapter.calls == 1
    assert info.value.__cause__ is permanent
    assert not event_logged(caplog)

    caplog.clear()
    plain = ValueError("retry budget: timeout while parsing")
    adapter = ScriptedAdapter(plain, failures=10)
    with pytest.raises(ProviderError, match=r"ValueError") as info:
        build_executor(adapter).execute(Resolved())  # type: ignore[arg-type]
    assert adapter.calls == 1
    assert info.value.__cause__ is plain
    assert not event_logged(caplog)
