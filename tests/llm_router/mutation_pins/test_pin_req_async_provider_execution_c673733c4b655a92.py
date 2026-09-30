# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION c673733c4b655a92
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")

_PATH = openai_chat_path()


def _success(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@pytest.mark.asyncio
@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
async def test_async_fallback_success_is_remembered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key_id in (1, 2):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{key_id}", f"openrouter-value-{key_id}")
    failure = ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message="route 0 failed"),
    )
    original = get_config()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _PATH): [
                failure,
                _success("first"),
                _success("second"),
                _success("third"),
            ]
        },
    ) as server:
        urls = {
            **original.provider_base_urls,
            Provider.OPENROUTER: f"{server.base_url}/v1",
        }
        catalog = replace(original.catalog, provider_base_urls=urls)
        install_config(replace(original, catalog=catalog))
        router = LLMRouter(
            [
                RouterProfile(
                    provider=Provider.OPENROUTER,
                    model=Model.DEEPSEEK_V3,
                    key_id=key_id,
                )
                for key_id in (1, 2)
            ],
            shuffle_fallbacks=False,
            round_robin_start=False,
            limits_by_provider={
                Provider.OPENROUTER: ProviderLimits(
                    rps=0.0,
                    rpm=1_000_000.0,
                    cooldown_seconds=0.0,
                    cooldown_after_failures=0,
                )
            },
        )
        first = await router.aquery("one")
        second = await router.aquery("two")
        install_config(original)
    assert [a.route_index for a in first.routing_trace] == [0, 1]
    assert [a.route_index for a in second.routing_trace] == [1]
