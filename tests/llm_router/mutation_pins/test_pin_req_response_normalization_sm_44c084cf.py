# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-44C084CF
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import llm_router
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")

EXPECTED_USAGE = {"input_tokens": 12, "output_tokens": 5, "total_tokens": 17}


def _point_openrouter_at(base_url: str) -> None:
    config = llm_router.get_config()
    base_urls = dict(config.catalog.provider_base_urls)
    base_urls[llm_router.Provider.OPENROUTER] = f"{base_url}/v1"
    catalog = replace(config.catalog, provider_base_urls=base_urls)
    llm_router.install_config(replace(config, catalog=catalog))


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_parsed_model_is_json_safe_and_provider_is_plain_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "local-openrouter-value")
    reply = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=json.dumps(EXPECTED_USAGE)),
    )
    with ScriptedHTTPServer(
        port=0,
        routes={("POST", openai_chat_path()): [reply]},
    ) as server:
        _point_openrouter_at(server.base_url)
        router = llm_router.LLMRouter(
            llm_router.RouterProfile(
                model=llm_router.Model.DEEPSEEK_V3,
                provider=llm_router.Provider.OPENROUTER,
            ),
        )
        response = router.query(
            "Report the token counts of the last run.",
            response_schema=llm_router.UsageStats,
        )

    parsed = response.data["parsed"]
    assert not isinstance(parsed, llm_router.UsageStats)
    assert isinstance(parsed, dict)
    assert parsed == EXPECTED_USAGE
    assert json.loads(json.dumps(response.data))["parsed"] == EXPECTED_USAGE
    assert type(response.provider) is str
    assert response.provider == "openrouter"
