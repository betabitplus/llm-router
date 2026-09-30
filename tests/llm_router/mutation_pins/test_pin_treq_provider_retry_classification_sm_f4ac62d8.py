# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION SM-F4AC62D8
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
from llm_router._internal.runtime.executor import ProviderRouteExecutor

pytestmark = pytest.mark.verification_kind("unit")

EXHAUSTED_EVENT = "llm_router.provider.retry.exhausted"


class Config:
    def __init__(self) -> None:
        self.retry_policy = RetryPolicy(
            min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=1
        )


@dataclass
class Route:
    route_index: int = 0
    model: Model = Model.LLAMA_8B
    provider: Provider = Provider.GROQ
    provider_model: str = "llama-3.1-8b-instant"


@dataclass
class Key:
    key_id: int = 1
    env_var: str = "GROQ_API_ENV"
    value: str = "v"


@dataclass
class Settings:
    temperature: float | None = None
    seed: int | None = None
    response_schema: object | None = None
    tools: tuple[object, ...] | None = None
    tool_choice: str | None = None
    max_tool_rounds: int | None = None
    kwargs: dict[str, object] = field(default_factory=dict)


@dataclass
class Resolved:
    request_id: str = "req-1"
    route: Route = field(default_factory=Route)
    settings: Settings = field(default_factory=Settings)
    key: Key = field(default_factory=Key)
    messages: tuple[str, ...] = ("hello",)
    content: object = "hello"


class RaisingAdapter:
    def execute(self, request: ProviderRequest) -> ProviderResult:
        msg = f"retry budget: timeout while parsing ({request.request_id})"
        raise ValueError(msg)


def adapter_getter(provider: Provider, config: Any) -> RaisingAdapter:
    assert provider is Provider.GROQ
    assert config is not None
    return RaisingAdapter()


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_retry_like_message_does_not_log_exhausted_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    executor = ProviderRouteExecutor(
        config=Config(),  # type: ignore[arg-type]
        adapter_getter=adapter_getter,  # type: ignore[arg-type]
    )
    caplog.set_level(0)

    with pytest.raises(ProviderError, match=r"Failure type: ValueError"):
        executor.execute(Resolved())  # type: ignore[arg-type]

    seen = [
        record
        for record in caplog.records
        if EXHAUSTED_EVENT in record.getMessage()
        or EXHAUSTED_EVENT in str(record.__dict__)
    ]
    assert seen == []
