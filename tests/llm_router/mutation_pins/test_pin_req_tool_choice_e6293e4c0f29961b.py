# mutation-pin: REQ_TOOL_CHOICE e6293e4c0f29961b
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
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


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]")
def test_named_read_only_mapping_choice_restricts_google_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "local-google-value"
    monkeypatch.setenv("GOOGLE_API_KEY_1", value)
    path = google_generate_path(model=Model.GEMINI_FLASH)
    choice = ReadOnlyChoice({"type": "function", "function": {"name": "add"}})
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=google_tool_call_response(
                        tool_name="add",
                        args={"a": 40, "b": 2},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=google_success_response(text="42"),
                ),
            ]
        },
    ) as server:
        with patched_google_genai_sdk(server_base_url=server.base_url):
            response = LLMRouter(
                RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
                temperature=0.0,
                seed=42,
            ).query(
                "Use add with a=40 and b=2, then return the result.",
                tools=[add, multiply],
                tool_choice=choice,  # type: ignore[arg-type]
                max_tool_rounds=2,
            )
        requests = server.recorded_requests("POST", path)

    assert {step.tool_name for step in response.tool_trace} == {"add"}
    first_payload = json.loads(requests[0].body.decode("utf-8"))
    calling = first_payload["toolConfig"]["functionCallingConfig"]
    assert calling["mode"] == "ANY"
    assert calling["allowedFunctionNames"] == ["add"]
