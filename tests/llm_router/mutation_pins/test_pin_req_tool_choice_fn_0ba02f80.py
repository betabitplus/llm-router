# mutation-pin: REQ_TOOL_CHOICE FN-0BA02F80
# pinned-by: delegate, one pin for 3 pins of normalize_tool_choice
# kills: SM-B25D86B3 e6293e4c0f29961b eecdb1201e9ab7e6
from __future__ import annotations

import json
import typing
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    google_success_response,
)
from tests.llm_router.support.workers.tool_failure import google_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_google_genai_sdk

pytestmark = pytest.mark.verification_kind("unit")


class ReadOnlyChoice(typing.Mapping[str, Any]):
    """A read-only Mapping that cannot be deep-copied."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = dict(data)

    def __getitem__(self, name: str) -> Any:
        return self._data[name]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __deepcopy__(self, memo: dict[int, Any]) -> ReadOnlyChoice:
        msg = "cannot deep-copy a read-only mapping"
        raise TypeError(msg)


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as JSON."""
    return {"result": a * b}


def _run(
    monkeypatch: pytest.MonkeyPatch,
    bodies: list[bytes],
    **kwargs: Any,
) -> tuple[Any, dict[str, Any]]:
    monkeypatch.setenv("GOOGLE_API_KEY_1", "local-google-value")
    path = google_generate_path(model=Model.GEMINI_FLASH)
    responses = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=body,
        )
        for body in bodies
    ]
    with (
        ScriptedHTTPServer(port=0, routes={("POST", path): responses}) as server,
        patched_google_genai_sdk(server_base_url=server.base_url),
    ):
        response = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
            temperature=0.0,
            seed=42,
        ).query("Use add with a=40 and b=2.", **kwargs)
        requests = server.recorded_requests("POST", path)
    payload = json.loads(requests[0].body.decode("utf-8"))
    return response, payload


def _tool_bodies() -> list[bytes]:
    return [
        google_tool_call_response(tool_name="add", args={"a": 40, "b": 2}),
        google_success_response(text="42"),
    ]


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]")
def test_required_without_tools_asks_for_any_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, payload = _run(
        monkeypatch,
        [google_success_response(text="ok")],
        tool_choice="required",
    )
    assert payload["toolConfig"]["functionCallingConfig"]["mode"] == "ANY"


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]")
def test_read_only_mapping_named_choice_restricts_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice = ReadOnlyChoice({"type": "function", "function": {"name": "add"}})
    response, payload = _run(
        monkeypatch,
        _tool_bodies(),
        tools=[add, multiply],
        tool_choice=choice,
        max_tool_rounds=2,
    )
    assert {step.tool_name for step in response.tool_trace} == {"add"}
    calling = payload["toolConfig"]["functionCallingConfig"]
    assert calling["mode"] == "ANY"
    assert calling["allowedFunctionNames"] == ["add"]


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]")
@pytest.mark.parametrize("choice", [{}, {"type": "any"}], ids=["empty", "any"])
def test_nameless_mapping_choice_accepted(
    monkeypatch: pytest.MonkeyPatch,
    choice: dict[str, str],
) -> None:
    response, _ = _run(
        monkeypatch,
        _tool_bodies(),
        tools=[add],
        tool_choice=choice,
        max_tool_rounds=2,
    )
    assert [step.tool_name for step in response.tool_trace] == ["add"]
