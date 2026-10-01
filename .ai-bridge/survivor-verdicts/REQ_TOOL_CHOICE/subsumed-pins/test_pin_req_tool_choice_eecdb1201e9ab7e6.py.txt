# mutation-pin: REQ_TOOL_CHOICE eecdb1201e9ab7e6
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

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


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]")
@pytest.mark.parametrize(
    "choice",
    [{}, {"type": "any"}],
    ids=["empty", "any"],
)
def test_nameless_mapping_choice_is_accepted_and_tool_runs(
    monkeypatch: pytest.MonkeyPatch,
    choice: dict[str, str],
) -> None:
    value = "local-google-value"
    monkeypatch.setenv("GOOGLE_API_KEY_1", value)
    path = google_generate_path(model=Model.GEMINI_FLASH)
    with (
        ScriptedHTTPServer(
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
        ) as server,
        patched_google_genai_sdk(server_base_url=server.base_url),
    ):
        response = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
            temperature=0.0,
            seed=42,
        ).query(
            "Use add with a=40 and b=2, then return the result.",
            tools=[add],
            tool_choice=choice,
            max_tool_rounds=2,
        )

    assert [step.tool_name for step in response.tool_trace] == ["add"]
