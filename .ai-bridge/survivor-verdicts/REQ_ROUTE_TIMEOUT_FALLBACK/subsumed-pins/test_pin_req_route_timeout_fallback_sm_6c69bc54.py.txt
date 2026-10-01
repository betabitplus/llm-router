# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK SM-6C69BC54
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import typing

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_PATH = openai_chat_path()

_HEADERS = {"Content-Type": "application/json"}

# Each attempt may run for 0.25 s. The first route answers only after 2.0 s,
# so a request that keeps waiting on it cannot finish within the 700 ms deadline.
_ATTEMPT_TIMEOUT_SECONDS = 0.25

_SLOW_SECONDS = 2.0

_FALLBACK_TEXT = "fallback answer"

_NO_LIMITS = ProviderLimits(
    rps=0.0,
    rpm=0.0,
    cooldown_seconds=0.0,
    cooldown_after_failures=0,
)


@pytest.fixture
def slow_first_route_router(
    monkeypatch: pytest.MonkeyPatch,
) -> typing.Iterator[LLMRouter]:
    """Route to a slow OpenRouter answer first, then to a prompt Groq answer."""
    value = "local-provider-credential"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    monkeypatch.setenv("GROQ_API_KEY_1", value)
    routes = {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers=_HEADERS,
                body=openai_success_response(text="slow answer"),
                delay_seconds=_SLOW_SECONDS,
            ),
            ScriptedResponse(
                status_code=200,
                headers=_HEADERS,
                body=openai_success_response(text=_FALLBACK_TEXT),
            ),
        ]
    }
    with (
        ScriptedHTTPServer(port=0, routes=routes) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        yield LLMRouter(
            [
                RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
                RouterProfile(model=Model.LLAMA_SCOUT, provider=Provider.GROQ),
            ],
            limits_by_provider={
                Provider.OPENROUTER: _NO_LIMITS,
                Provider.GROQ: _NO_LIMITS,
            },
            attempt_timeout_seconds=_ATTEMPT_TIMEOUT_SECONDS,
        )


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
@settings(
    max_examples=1,
    deadline=700,
    database=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(prompt=st.just("Reply with the fallback marker only."))
def test_sync_timeout_falls_back_without_waiting_for_slow_route(
    slow_first_route_router: LLMRouter,
    prompt: str,
) -> None:
    """The fallback answers soon after the timeout, not after the slow route."""
    response = slow_first_route_router.query(prompt)

    assert response.output_text == _FALLBACK_TEXT
    trace_errors = [attempt.error_type for attempt in response.routing_trace]
    assert trace_errors == ["TimeoutError", None]
