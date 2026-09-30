# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK 3ccbc7c7990f5f22
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import typing
from dataclasses import replace

import pytest

from llm_router import get_config, install_config
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
    run_retry_worker,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.fixture
def no_attempt_timeout() -> typing.Iterator[None]:
    """Install a config whose policy sets no attempt timeout, then restore."""
    original = get_config()
    defaults = original.defaults
    policy = replace(defaults.policy, attempt_timeout_seconds=None)
    install_config(replace(original, defaults=replace(defaults, policy=policy)))
    yield
    install_config(original)


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
@pytest.mark.usefixtures("no_attempt_timeout")
def test_sync_request_without_attempt_timeout_returns_provider_response() -> None:
    """With no attempt timeout the route is called and its response is returned."""
    routes = {
        ("POST", openai_chat_path()): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="plain answer"),
            )
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        result = run_retry_worker(
            case="openai",
            scenario="success",
            server_base_url=server.base_url,
        )
        received = server.request_count("POST", openai_chat_path())

    assert received == 1
    assert result.ok is True
    assert result.output_text == "plain answer"
