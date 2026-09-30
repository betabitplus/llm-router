# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-2265B496
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")

_SCHEMA = {
    "title": "Vehicle",
    "type": "object",
    "properties": {"plate": {"type": "string"}, "dock": {"type": "integer"}},
    "required": ["plate", "dock"],
}


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_structured_parsed_is_normalized_public_data(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "normalization-value")
    body = openai_success_response(text='{"plate": "AB-12", "dock": 4}')
    with ScriptedHTTPServer(
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
    ) as server:
        original = get_config()
        request.addfinalizer(lambda: install_config(original))
        urls = dict(original.provider_base_urls)
        urls[Provider.OPENROUTER] = f"{server.base_url}/v1"
        catalog = replace(original.catalog, provider_base_urls=urls)
        install_config(replace(original, catalog=catalog))
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
        )
        response = router.query("Which vehicle?", response_schema=_SCHEMA)

    parsed = response.data["parsed"]
    assert parsed == {"plate": "AB-12", "dock": 4}
    assert parsed.plate == "AB-12"
    assert json.loads(json.dumps(dict(response.data)))["parsed"]["dock"] == 4
