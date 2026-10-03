# mutation-pin: TREQ_TIMED_OUT_ATTEMPT_STOPS 39d5d1ce764651c8
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import typing
from dataclasses import replace

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.tool_failure import (
    openai_tool_call_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

HEADERS = {"Content-Type": "application/json"}
CALLS: list[str] = []


def lookup(query: str) -> str:
    """Look a query up."""
    CALLS.append(query)
    return f"found {query}"


@pytest.fixture
def no_attempt_timeout() -> typing.Iterator[None]:
    """Install a config whose policy sets no attempt timeout, then restore."""
    original = get_config()
    defaults = original.defaults
    policy = replace(defaults.policy, attempt_timeout_seconds=None)
    install_config(replace(original, defaults=replace(defaults, policy=policy)))
    yield
    install_config(original)


def build_router(monkeypatch: pytest.MonkeyPatch) -> LLMRouter:
    value = "neutral-auth-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    return LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id=1,
        ),
    )


def build_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    return {
        ("POST", openai_chat_path()): [
            ScriptedResponse(
                status_code=200,
                headers=HEADERS,
                body=openai_tool_call_response(
                    tool_name="lookup", args={"query": "alpha"}
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers=HEADERS,
                body=openai_success_response(text="all done"),
            ),
        ]
    }


@pytest.mark.usefixtures("no_attempt_timeout")
@pytest.mark.verifies("TREQ_TIMED_OUT_ATTEMPT_STOPS[revision==1]")
def test_attempt_without_timeout_runs_requests_and_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = build_router(monkeypatch)
    path = openai_chat_path()
    CALLS.clear()

    with ScriptedHTTPServer(port=0, routes=build_routes()) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            sync_response = router.query("sync question", tools=[lookup])
        sync_requests = server.request_count("POST", path)

    assert sync_response.output_text == "all done"
    assert sync_requests == 2
    assert CALLS == ["alpha"]
