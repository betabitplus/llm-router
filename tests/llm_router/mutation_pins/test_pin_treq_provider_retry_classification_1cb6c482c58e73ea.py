# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 1cb6c482c58e73ea
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.config import RetryPolicy
from llm_router._internal.providers.base import ProviderRequest
from llm_router._internal.runtime.executor import ProviderRouteExecutor

pytestmark = pytest.mark.verification_kind("unit")


@dataclass(frozen=True)
class FakeConfig:
    retry_policy: RetryPolicy


@dataclass(frozen=True)
class FakeRoute:
    provider: Provider = Provider.GROQ
    model: Model = Model.LLAMA_8B
    provider_model: str = "llama-3.1-8b-instant"
    route_index: int | None = 0


@dataclass(frozen=True)
class FakeSettings:
    response_schema: object | None = None
    tools: tuple[object, ...] = ()
    tool_choice: object | None = None
    max_tool_rounds: int | None = None
    temperature: float | None = None
    seed: int | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FakeKey:
    key_id: int = 1
    env_var: str = "GROQ_API_KEY"
    value: str = "v"


@dataclass(frozen=True)
class FakeResolved:
    request_id: str
    route: FakeRoute
    settings: FakeSettings
    key: FakeKey
    messages: tuple[str, ...]
    content: object


class FailingAdapter:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def execute(self, _request: ProviderRequest) -> Any:
        self.calls += 1
        raise self.error


def _run(error: Exception) -> tuple[ProviderError, FailingAdapter]:
    adapter = FailingAdapter(error)

    def getter(_provider: Provider, _config: object) -> FailingAdapter:
        return adapter

    policy = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=2)
    executor = ProviderRouteExecutor(
        config=FakeConfig(retry_policy=policy),  # type: ignore[arg-type]
        adapter_getter=getter,  # type: ignore[arg-type]
    )
    request = FakeResolved(
        request_id="req-1",
        route=FakeRoute(),
        settings=FakeSettings(),
        key=FakeKey(),
        messages=("hello",),
        content="hello",
    )
    with pytest.raises(ProviderError, match=r".*") as info:
        executor.execute(request)  # type: ignore[arg-type]
    return info.value, adapter


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_provider_failures_surface_boundary_error_chained_from_original() -> None:
    permanent = ValueError("400 bad request")
    boundary, adapter = _run(permanent)
    assert adapter.calls == 1
    assert boundary.__cause__ is permanent

    transport = ConnectionResetError("reset by peer")
    boundary, adapter = _run(transport)
    assert boundary.__cause__ is transport
