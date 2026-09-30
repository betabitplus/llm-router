# mutation-pin: REQ_STRUCTURED_OUTPUT_REPAIR ea1a8657cd65d4b1
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

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
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")

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


def _reply(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]")
def test_repair_on_final_attempt_returns_structured_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "LOCAL_RETRY_KEY")
    original_config = get_config()
    endpoint = openai_chat_path()
    routes = {
        ("POST", endpoint): [
            _reply(_INVALID_JSON),
            _reply(json.dumps(_VALID_JSON)),
        ]
    }
    clear_test_caches()
    install_fast_worker_runtime_config(
        retry_max_attempts=2,
        structured_output_max_attempts=2,
    )
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
            seed=1,
        )
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = router.query(
                "Return incident JSON.", response_schema=TicketSummary
            )
        request_count = server.request_count("POST", endpoint)
    clear_test_caches()
    install_config(original_config)

    assert request_count == 2
    assert response.data["parsed"] == _VALID_JSON
