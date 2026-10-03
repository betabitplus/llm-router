# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 69c9a7cc23c00f7e
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pydantic
import pytest

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
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

_CHAT_PATH = openai_chat_path()
_FORM_FEED = "\x0c"
_NO_BREAK_SPACE = chr(0xA0)


class ItemCount(pydantic.RootModel[int]):
    """A scalar item count returned as the whole structured result."""


def _query_with_body(
    monkeypatch: pytest.MonkeyPatch, body_text: str
) -> LLMRouterResponse:
    value = "inventory-assurance-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    response_body = openai_success_response(text=body_text)
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
    ):
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
        )
        return router.query(
            "How many items are in the record?",
            response_schema=ItemCount,
        )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
@pytest.mark.parametrize(
    "padded_text",
    [
        f"{_FORM_FEED} 42  ",
        f"{_NO_BREAK_SPACE}42{_NO_BREAK_SPACE}",
        f"\t{_FORM_FEED}42\n{_FORM_FEED}",
    ],
    ids=["form-feed-lead", "no-break-space-around", "tab-and-form-feed"],
)
def test_whitespace_padded_scalar_parses_like_bare_value(
    monkeypatch: pytest.MonkeyPatch,
    padded_text: str,
) -> None:
    """A scalar padded with Unicode whitespace parses to the bare value's result."""
    bare_response = _query_with_body(monkeypatch, "42")
    padded_response = _query_with_body(monkeypatch, padded_text)

    assert bare_response.data["parsed"] == 42
    assert padded_response.data["parsed"] == bare_response.data["parsed"]
