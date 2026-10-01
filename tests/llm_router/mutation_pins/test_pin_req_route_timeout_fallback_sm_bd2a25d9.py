# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK SM-BD2A25D9
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.timeout import run_timeout_inprocess

pytestmark = pytest.mark.verification_kind("unit")

_PATH = openai_chat_path()
_SLOW_SECONDS = 1.5
_HEADERS = {"Content-Type": "application/json"}


def _slow(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers=_HEADERS,
        body=openai_success_response(text=text),
        delay_seconds=_SLOW_SECONDS,
    )


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
def test_sync_timeout_moves_to_fallback_without_grace_wait() -> None:
    """A first route answering after 1.5 timeouts is abandoned for the fallback."""
    fast = ScriptedResponse(
        status_code=200,
        headers=_HEADERS,
        body=openai_success_response(text="fallback answer"),
    )
    routes = {("POST", _PATH): [_slow("slow answer"), fast]}
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        result = run_timeout_inprocess(
            scenario="fallback_after_timeout",
            server_base_url=server.base_url,
        )

    assert result.ok is True, result.error_message
    assert result.output_text == "fallback answer"
    assert [a["error_type"] for a in result.routing_trace] == ["TimeoutError", None]
