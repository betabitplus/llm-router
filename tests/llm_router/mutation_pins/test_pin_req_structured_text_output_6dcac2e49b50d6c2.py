# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 6dcac2e49b50d6c2
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest
from pydantic import RootModel

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_OPENAI_PATH = openai_chat_path()


class Label(RootModel[str]):
    """A caller-requested schema whose result is a bare JSON string."""


def _unmatched_bracket_response() -> ScriptedResponse:
    raw_text = '"a]"'
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=raw_text),
    )


def _build_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_unmatched_closing_bracket_in_string_result_survives_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin: a lone ']' inside a scalar result must not be sliced away."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "unmatched-bracket-route-value")

    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", _OPENAI_PATH): [_unmatched_bracket_response()]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = _build_router().query(
            "Return the requested string value only.",
            response_schema=Label,
        )

    assert json.loads(response.output_text) == "a]"
    assert Label.model_validate_json(response.output_text) == Label(root="a]")
