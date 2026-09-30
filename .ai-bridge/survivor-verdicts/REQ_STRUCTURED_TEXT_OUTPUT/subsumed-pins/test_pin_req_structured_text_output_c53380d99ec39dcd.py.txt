# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT c53380d99ec39dcd
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest
from pydantic import RootModel

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_OPENAI_PATH = openai_chat_path()
_BRACKET_ONLY_REPLY = '"a]"'


class BracketOnlyText(RootModel[str]):
    """A bare JSON string payload: a ']' with no '[' anywhere in it."""


def _openrouter_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_closing_bracket_without_opening_bracket_is_kept_intact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reply with ']' but no '[' or braces must pass through unchanged."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "bracket-reply-assurance-value")
    scripted_response = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=_BRACKET_ONLY_REPLY),
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", _OPENAI_PATH): [scripted_response]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = _openrouter_router().query(
            "Reply with exactly the bracket-only payload, no extra text.",
            response_schema=BracketOnlyText,
        )

    assert response.data is not None
    assert json.loads(response.output_text) == "a]"
