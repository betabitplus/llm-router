# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 6de617b610b093eb
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

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

_OPENAI_PATH = openai_chat_path()
_EXPECTED = {"scene": "urban traffic", "vehicle_count": 5}
_MISSING_FIELD_BODY = {"vehicle_count": 5}


class Observation(BaseModel):
    scene: str
    vehicle_count: int


def _invalid_schema_response() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=json.dumps(_MISSING_FIELD_BODY)),
    )


def _valid_schema_response() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=json.dumps(_EXPECTED)),
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_schema_validation_failure_triggers_retry_not_false_positive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin: a schema-invalid attempt is rejected, not accepted as valid."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "unit-test-value")
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
        max_attempts=2,
    )
    routes = {
        ("POST", _OPENAI_PATH): [
            _invalid_schema_response(),
            _valid_schema_response(),
        ],
    }

    with ScriptedHTTPServer(port=0, routes=routes) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = router.query(
                "Describe the observed scene using the requested schema.",
                response_schema=Observation,
            )
        requests = server.recorded_requests("POST", _OPENAI_PATH)

    assert len(requests) == 2
    assert response.data["parsed"] == _EXPECTED
    assert json.loads(response.output_text) == _EXPECTED
