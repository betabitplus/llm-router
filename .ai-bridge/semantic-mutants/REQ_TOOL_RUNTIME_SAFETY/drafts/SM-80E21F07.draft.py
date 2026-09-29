# semantic-mutant: SM-80E21F07
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import openai_chat_path
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_PATH = openai_chat_path()


def lookup(*, value: str) -> dict[str, str]:
    """Fail locally so the tool round raises."""
    message = f"lookup failed for {value}"
    raise RuntimeError(message)


@pytest.mark.verifies("REQ_TOOL_RUNTIME_SAFETY[revision==1]")
def test_failing_tool_still_logs_called_event_before_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "test-credential")
    caplog.set_level(20, logger="llm_router")
    routes = {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_tool_call_response(
                    tool_name="lookup",
                    args={"value": "widget-42"},
                ),
            )
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            router = LLMRouter(
                RouterProfile(
                    provider=Provider.OPENROUTER,
                    model=Model.DEEPSEEK_V3,
                ),
                temperature=0.0,
                seed=42,
            )
            with pytest.raises(Exception, match=r"(?s).*"):
                router.query(
                    "Look something up.",
                    tools=[lookup],
                    tool_choice="required",
                    max_tool_rounds=3,
                )
        request_count = server.request_count("POST", _PATH)

    event_types = [
        record.msg.get("event_type")
        for record in caplog.records
        if isinstance(record.msg, dict)
    ]

    assert request_count == 1
    assert "llm_router.capability.tool.called" in event_types
