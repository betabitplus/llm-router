# mutation-pin: REQ_STRUCTURED_OUTPUT_REPAIR 8d730e921a4ddffa
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json
from dataclasses import replace

import pytest
from pydantic import BaseModel, Field

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.runtime import clear_test_caches
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
)

pytestmark = pytest.mark.verification_kind("unit")

_PATH = openai_chat_path()
_VALID_JSON = {
    "incident_id": "INC-2048",
    "severity": "SEV2",
    "tags": ["db", "api"],
}
_INVALID_JSON = json.dumps({"incident_id": "INC-2048"})


class TicketSummary(BaseModel):
    """Structured output used by the repair scenario."""

    incident_id: str
    severity: str = Field(min_length=4)
    tags: list[str] = Field(min_length=2, max_length=2)


def _response(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]")
def test_repair_on_final_attempt_returns_parsed_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "LOCAL_RETRY_KEY"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    routes = {
        ("POST", _PATH): [
            _response(_INVALID_JSON),
            _response(json.dumps(_VALID_JSON)),
        ]
    }
    original_config = get_config()
    clear_test_caches()
    try:
        install_fast_worker_runtime_config(structured_output_max_attempts=2)
        with ScriptedHTTPServer(port=0, routes=routes) as server:
            config = get_config()
            urls = dict(config.provider_base_urls)
            urls[Provider.OPENROUTER] = f"{server.base_url}/v1"
            catalog = replace(config.catalog, provider_base_urls=urls)
            install_config(replace(config, catalog=catalog))
            profile = RouterProfile(
                model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER
            )
            router = LLMRouter(profile, temperature=0.0, seed=1)
            response = router.query(
                "Return incident JSON.", response_schema=TicketSummary
            )
            request_count = server.request_count("POST", _PATH)
    finally:
        clear_test_caches()
        install_config(original_config)

    assert request_count == 2
    assert response.data["parsed"] == _VALID_JSON
