# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT FN-EF7D2612
# pinned-by: delegate, one pin for 5 pins of _extract_json_payload
# kills: 01fd76634a96fdbd 0bd04ba951d7aa46 0ddb26b38c02ad8c 5b5f64ae9f619fd8
# kills: 6dcac2e49b50d6c2
from __future__ import annotations

from typing import Any

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
from tests.llm_router.support.workers.worker_patches import (
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


class TextResult(RootModel[str]):
    root: str


class IntListResult(RootModel[list[int]]):
    root: list[int]


class StrListResult(RootModel[list[str]]):
    root: list[str]


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
@pytest.mark.parametrize(
    ("body_text", "response_schema", "expected"),
    [
        ('"a ] b ["', TextResult, "a ] b ["),
        ("Note: [101, 102]", IntListResult, [101, 102]),
        (
            '["service-api", "worker-queue"] finished :}',
            StrListResult,
            ["service-api", "worker-queue"],
        ),
        (
            '["marker_status: closed}", "{marker_scope: internal"]',
            StrListResult,
            ["marker_status: closed}", "{marker_scope: internal"],
        ),
        ('"a]"', TextResult, "a]"),
    ],
    ids=[
        "bracket_before_opener",
        "prose_before_array",
        "trailing_brace",
        "inverted_braces",
        "unmatched_closing_bracket",
    ],
)
def test_structured_text_payload_extraction(
    monkeypatch: pytest.MonkeyPatch,
    body_text: str,
    response_schema: type[RootModel[Any]],
    expected: Any,
) -> None:
    env_name = "OPENROUTER_API_KEY_1"
    value = "test-provider-credential"
    monkeypatch.setenv(env_name, value)

    chat_path = openai_chat_path()
    response_body = openai_success_response(text=body_text)
    server_routes = {
        ("POST", chat_path): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=response_body,
            )
        ]
    }
    with (
        ScriptedHTTPServer(port=0, routes=server_routes) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router = LLMRouter(
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
            ),
            temperature=0.0,
        )
        response = router.query(
            "Extract the requested structured result.",
            response_schema=response_schema,
        )

    assert response.data["parsed"] == expected
