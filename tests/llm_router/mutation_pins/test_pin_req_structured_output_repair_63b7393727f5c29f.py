# mutation-pin: REQ_STRUCTURED_OUTPUT_REPAIR 63b7393727f5c29f
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    RetryWorkerResult,
    openai_chat_path,
    openai_success_response,
    run_retry_worker,
)

pytestmark = pytest.mark.verification_kind("unit")

_TEXT = "plain answer"


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]")
def test_plain_request_without_schema_is_accepted_first_time() -> None:
    path = openai_chat_path()
    routes = {
        ("POST", path): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_TEXT),
            ),
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        result = run_retry_worker(
            case="openai",
            scenario="retryable",
            server_base_url=server.base_url,
        )
        count = server.request_count("POST", path)
    assert isinstance(result, RetryWorkerResult)
    assert result.ok is True, result.error_message
    assert result.output_text == _TEXT
    assert count == 1
