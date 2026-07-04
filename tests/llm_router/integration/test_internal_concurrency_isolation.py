from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import replace

import pytest

from llm_router import Model, Provider, RouterProfile, Session, ToolCall
from llm_router._internal.config import get_config
from llm_router._internal.config.models import RetryPolicy
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.router import RouterRuntime


class EchoAsyncAdapter:
    capabilities = ProviderCapabilities()

    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        return self._result(request)

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        await asyncio.sleep(0.001)
        return self._result(request)

    def _result(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        text = _message_text(request.messages)
        return ProviderResult(
            data={"text": text},
            provider=request.provider,
            model=request.model,
            provider_model=request.provider_model,
            output_text=text,
        )


def _message_text(messages: Sequence[object]) -> str:
    texts: list[str] = []
    for message in messages:
        texts.extend(
            part.text for part in message.parts if getattr(part, "kind", None) == "text"
        )
    return " ".join(texts)


def _fast_config():
    config = get_config()
    return replace(
        config,
        defaults=replace(
            config.defaults,
            retry_policy=RetryPolicy(
                min_wait_seconds=0.001,
                max_wait_seconds=0.001,
                max_attempts=2,
            ),
        ),
    )


def _runtime(adapter: EchoAsyncAdapter, session: Session) -> RouterRuntime:
    executor = ProviderRouteExecutor(
        config=_fast_config(),
        adapter_getter=lambda _provider, _config: adapter,
    )
    return RouterRuntime(
        spec=RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        session=session,
        _executor=executor,
        round_robin_start=False,
        shuffle_fallbacks=False,
    )


@pytest.mark.asyncio
async def test_concurrent_sessions_traces_and_responses_are_isolated(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "key")
    adapter = EchoAsyncAdapter()
    alpha_session = Session()
    beta_session = Session()
    alpha = _runtime(adapter, alpha_session)
    beta = _runtime(adapter, beta_session)

    alpha_response, beta_response = await asyncio.gather(
        alpha.aquery("alpha prompt"),
        beta.aquery("beta prompt"),
    )

    alpha_response.tool_calls.append(ToolCall(name="alpha_marker"))

    assert alpha_response.output_text == "User: alpha prompt"
    assert beta_response.output_text == "User: beta prompt"
    assert beta_response.tool_calls == []
    assert alpha_response.routing_trace is not beta_response.routing_trace
    assert len(alpha_session.history) == 2
    assert len(beta_session.history) == 2
    assert alpha_session.history[0].parts == ("alpha prompt",)
    assert beta_session.history[0].parts == ("beta prompt",)
    assert len({request.request_id for request in adapter.requests}) == 2
