# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 1d475cc4b98b3b39
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_SCHEMA = {
    "type": "object",
    "properties": {"1": {"type": "string"}},
    "required": ["1"],
    "additionalProperties": False,
}

_MARKER = '{"marker": "decoded-with-int-key"}'

_REAL_LOADS = json.loads


def _fake_loads(text, *args, **kwargs):
    if isinstance(text, str) and text == _MARKER:
        return {1: "x"}
    return _REAL_LOADS(text, *args, **kwargs)


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_decoded_non_string_key_validates_as_string_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A decoded mapping with an int key validates against a string-key schema."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "assurance-value")
    body = openai_success_response(text=_MARKER)
    monkeypatch.setattr(json, "loads", _fake_loads)
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", openai_chat_path()): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=body,
                    )
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
        )
        response = router.query("Return the object.", response_schema=_SCHEMA)

    parsed = response.data["parsed"]
    assert parsed == {"1": "x"}
    assert all(isinstance(key, str) for key in parsed)
