# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK b9accd29af1a644f
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import dataclasses
import typing

import hypothesis
import pytest

import llm_router
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_ATTEMPT_TIMEOUT = 0.2
_BLOCKED_ROUTE_SECONDS = 4.0
_DEADLINE_MS = 1500
_FALLBACK_TEXT = "fallback route answer"
_PROMPT = "Reply with the timeout marker only."
_OPEN_LIMITS = llm_router.ProviderLimits(
    rps=0.0,
    rpm=0.0,
    cooldown_seconds=0.0,
    cooldown_after_failures=0,
)
_BOUNDED_SETTINGS = hypothesis.settings(
    deadline=_DEADLINE_MS,
    max_examples=1,
    database=None,
    derandomize=True,
    suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
)


@dataclasses.dataclass(frozen=True)
class _Scene:
    """A router wired to a local provider whose first answer is held back."""

    router: llm_router.LLMRouter
    server: ScriptedHTTPServer


def _answer(*, text: str, delay_seconds: float) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
        delay_seconds=delay_seconds,
    )


def _blocked_profile() -> llm_router.RouterProfile:
    return llm_router.RouterProfile(
        model=llm_router.Model.DEEPSEEK_V3,
        provider=llm_router.Provider.OPENROUTER,
    )


def _fast_profile() -> llm_router.RouterProfile:
    return llm_router.RouterProfile(
        model=llm_router.Model.LLAMA_SCOUT,
        provider=llm_router.Provider.GROQ,
    )


def _serve(
    *,
    profiles: list[llm_router.RouterProfile],
    answers: list[ScriptedResponse],
) -> typing.Iterator[_Scene]:
    router = llm_router.LLMRouter(
        profiles,
        limits_by_provider={
            llm_router.Provider.OPENROUTER: _OPEN_LIMITS,
            llm_router.Provider.GROQ: _OPEN_LIMITS,
        },
        round_robin_start=False,
        shuffle_fallbacks=False,
        attempt_timeout_seconds=_ATTEMPT_TIMEOUT,
    )
    routes = {("POST", openai_chat_path()): answers}
    with (
        ScriptedHTTPServer(port=0, routes=routes) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        yield _Scene(router=router, server=server)


def _install_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    value = "local-provider-credential"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    monkeypatch.setenv("GROQ_API_KEY_1", value)


@pytest.fixture
def fallback_scene(monkeypatch: pytest.MonkeyPatch) -> typing.Iterator[_Scene]:
    """First route is held far beyond the attempt timeout; second answers."""
    _install_credentials(monkeypatch)
    yield from _serve(
        profiles=[_blocked_profile(), _fast_profile()],
        answers=[
            _answer(text="late blocked answer", delay_seconds=_BLOCKED_ROUTE_SECONDS),
            _answer(text=_FALLBACK_TEXT, delay_seconds=0.0),
        ],
    )


@pytest.fixture
def terminal_scene(monkeypatch: pytest.MonkeyPatch) -> typing.Iterator[_Scene]:
    """The only route is held far beyond the attempt timeout."""
    _install_credentials(monkeypatch)
    yield from _serve(
        profiles=[_blocked_profile()],
        answers=[
            _answer(text="late blocked answer", delay_seconds=_BLOCKED_ROUTE_SECONDS),
        ],
    )


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
@_BOUNDED_SETTINGS
@hypothesis.given(content=hypothesis.strategies.just(_PROMPT))
def test_sync_timeout_falls_back_without_waiting_for_blocked_route(
    fallback_scene: _Scene,
    content: str,
) -> None:
    """The fallback answer arrives well before the blocked route would answer."""
    response = fallback_scene.router.query(content)

    assert response.output_text == _FALLBACK_TEXT
    assert [attempt.error_type for attempt in response.routing_trace] == [
        "TimeoutError",
        None,
    ]
    assert fallback_scene.server.request_count("POST", openai_chat_path()) == 2


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
@_BOUNDED_SETTINGS
@hypothesis.given(content=hypothesis.strategies.just(_PROMPT))
def test_sync_terminal_timeout_surfaces_without_waiting_for_blocked_route(
    terminal_scene: _Scene,
    content: str,
) -> None:
    """With no fallback left, the timeout error surfaces after one attempt."""
    with pytest.raises(TimeoutError, match=r"Attempt timed out"):
        terminal_scene.router.query(content)

    assert terminal_scene.server.request_count("POST", openai_chat_path()) == 1
