# mutation-pin: REQ_STRUCTURED_OUTPUT_REPAIR SM-12FA1E31
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    qwen_chat_path,
    qwen_success_response,
)
from tests.llm_router.support.workers.structured_recovery import (
    run_structured_recovery_worker,
)

pytestmark = pytest.mark.verification_kind("unit")

_VALID = {"incident_id": "INC-2048", "severity": "SEV2", "tags": ["a", "b"]}


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]")
def test_repair_request_keeps_schema_and_final_attempt_succeeds() -> None:
    path = qwen_chat_path()
    headers = {"Content-Type": "application/json"}
    routes = {
        ("POST", path): [
            ScriptedResponse(
                status_code=200,
                headers=headers,
                body=qwen_success_response(text='{"incident_id": "INC-2048"}'),
            ),
            ScriptedResponse(
                status_code=200,
                headers=headers,
                body=qwen_success_response(text=json.dumps(_VALID)),
            ),
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        result = run_structured_recovery_worker(
            case="qwenchat",
            scenario="recovery",
            server_base_url=server.base_url,
            max_attempts=2,
        )
        records = server.recorded_requests("POST", path)
    assert result.ok is True, result.error_message
    bodies = [r.body.decode() for r in records]
    assert len(bodies) == 2
    first, second = bodies
    marker = "You are a JSON API"
    assert marker in first
    assert marker in second
    assert second.count("incident_id") > first.count("incident_id")
    assert "Return only valid JSON that satisfies the schema" in second
