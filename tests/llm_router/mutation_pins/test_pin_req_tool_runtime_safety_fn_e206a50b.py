# mutation-pin: REQ_TOOL_RUNTIME_SAFETY FN-E206A50B
# pinned-by: delegate, one pin for 2 pins of _run_logged_tool_round
# kills: 4180d032448ab8db SM-2027036F
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
_CALLS: list[str] = []


def lookup(*, value: str) -> dict[str, str]:
    """Fail on the first call, succeed afterwards."""
    _CALLS.append(value)
    if len(_CALLS) == 1:
        raise RuntimeError("lookup backend failure")
    return {"value": value}


def make_routes() -> dict:
    return {
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


def make_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        temperature=0.0,
        seed=42,
    )


@pytest.mark.verifies("REQ_TOOL_RUNTIME_SAFETY[revision==1]")
def test_exhausted_round_limit_keeps_call_outstanding_and_logs_no_call(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "test-credential")
    caplog.set_level(20, logger="llm_router")
    _CALLS.clear()
    with ScriptedHTTPServer(port=0, routes=make_routes()) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = make_router().query(
                "Look something up.",
                tools=[lookup],
                tool_choice="required",
                max_tool_rounds=0,
            )
        request_count = server.request_count("POST", _PATH)

    event_types = [
        record.msg.get("event_type")
        for record in caplog.records
        if isinstance(record.msg, dict)
    ]
    assert request_count == 1
    assert _CALLS == []
    assert response.tool_trace == []
    assert len(response.tool_calls) == 1
    outstanding = next(iter(response.tool_calls))
    assert outstanding.name == "lookup"
    assert outstanding.args == {"value": "widget-42"}
    assert "llm_router.capability.tool.called" not in event_types


@pytest.mark.verifies("REQ_TOOL_RUNTIME_SAFETY[revision==1]")
def test_failing_tool_runs_once_and_error_surfaces_without_extra_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "test-credential")
    _CALLS.clear()
    with ScriptedHTTPServer(port=0, routes=make_routes()) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            router = make_router()
            with pytest.raises(Exception, match=r"(?s).*"):
                router.query(
                    "Look something up.",
                    tools=[lookup],
                    tool_choice="required",
                    max_tool_rounds=3,
                )
        request_count = server.request_count("POST", _PATH)

    assert len(_CALLS) == 1
    assert request_count == 1
