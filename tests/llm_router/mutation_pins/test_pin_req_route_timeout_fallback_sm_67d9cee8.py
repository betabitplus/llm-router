# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK SM-67D9CEE8
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import typing

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_PATH = openai_chat_path()

_HEADERS = {"Content-Type": "application/json"}

# The router gives each attempt 0.2 s; the first route answers only after 1.2 s.
_ATTEMPT_TIMEOUT_SECONDS = 0.2

_SLOW_ROUTE_SECONDS = 1.2

# Hypothesis flags a query slower than 1.25 x 600 ms = 750 ms: far above the
# 0.2 s attempt timeout, far below the 1.2 s the slow route keeps the call busy.
_QUERY_DEADLINE_MS = 600

_FALLBACK_TEXT = "fallback route answer"

_NO_LIMITS = ProviderLimits(
    rps=0.0,
    rpm=0.0,
    cooldown_seconds=0.0,
    cooldown_after_failures=0,
)


@pytest.fixture
def timeout_router(monkeypatch: pytest.MonkeyPatch) -> typing.Iterator[LLMRouter]:
    """A slow OpenRouter route followed by a fast Groq route on a local server."""
    value = "local-test-credential"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    monkeypatch.setenv("GROQ_API_KEY_1", value)
    routes = {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers=_HEADERS,
                body=openai_success_response(text="slow route answer"),
                delay_seconds=_SLOW_ROUTE_SECONDS,
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
            temperature=0.0,
            seed=1,
            attempt_timeout_seconds=_ATTEMPT_TIMEOUT_SECONDS,
        )


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
@settings(
    max_examples=1,
    deadline=_QUERY_DEADLINE_MS,
    database=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(prompt=st.just("Reply with the fallback marker only."))
def test_sync_timeout_falls_back_without_waiting_for_the_slow_route(
    timeout_router: LLMRouter,
    prompt: str,
) -> None:
    """The fallback answers near the attempt timeout, not after the slow route."""
    response = timeout_router.query(prompt)

    assert response.output_text == _FALLBACK_TEXT
    assert [attempt.error_type for attempt in response.routing_trace] == [
        "TimeoutError",
        None,
    ]
