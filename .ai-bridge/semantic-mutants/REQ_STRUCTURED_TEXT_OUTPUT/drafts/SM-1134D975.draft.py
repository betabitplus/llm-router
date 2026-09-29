# semantic-mutant: SM-1134D975
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_JSON_STRING_BODY = '"x {\\"a\\":1} y"'


class Counter(BaseModel):
    """Object result."""

    a: int


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_quoted_prose_fails_as_invalid_json_not_wrong_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Payload extraction runs first, so the failure is invalid JSON."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-assurance-value")
    response_body = openai_success_response(text=_JSON_STRING_BODY)
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _CHAT_PATH): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=response_body,
                    )
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
        pytest.raises(Exception, match=r"validation failed") as exc_info,
    ):
        router.query(
            "Give the count. Use the requested schema.",
            response_schema=Counter,
        )

    chain = []
    current = exc_info.value
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    names = [type(item).__name__ for item in chain]
    assert "TypeError" not in names
    assert "ValueError" in names
