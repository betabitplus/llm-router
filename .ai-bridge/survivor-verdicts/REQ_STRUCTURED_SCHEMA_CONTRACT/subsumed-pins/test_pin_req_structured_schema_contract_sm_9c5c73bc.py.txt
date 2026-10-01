# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-9C5C73BC
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json

import pytest

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
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.tool_failure import (
    openai_tool_call_response,
)
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


def scripted(body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_caller_nested_schema_edit_mid_query_does_not_weaken_validation(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "local-openrouter-value")
    original = get_config()
    request.addfinalizer(lambda: install_config(original))
    install_fast_worker_runtime_config(structured_output_max_attempts=2)

    count_rule: dict[str, object] = {"type": "integer", "minimum": 1}
    schema: dict[str, object] = {
        "title": "StockCount",
        "type": "object",
        "properties": {"count": count_rule},
        "required": ["count"],
    }

    def lookup_stock(*, sku: str) -> dict[str, str]:
        """Look up stock for a SKU; the caller reuses its schema dict meanwhile."""
        count_rule["type"] = "string"
        return {"sku": sku, "status": "in-stock"}

    path = openai_chat_path()
    routes = {
        ("POST", path): [
            scripted(
                openai_tool_call_response(
                    tool_name="lookup_stock",
                    args={"sku": "SKU-1042"},
                )
            ),
            scripted(openai_success_response(text=json.dumps({"count": "seven"}))),
            scripted(openai_success_response(text=json.dumps({"count": 7}))),
        ]
    }
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
        seed=3,
    )
    with (
        ScriptedHTTPServer(port=0, routes=routes) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query(
            "How many units of SKU-1042 are in stock?",
            tools=[lookup_stock],
            response_schema=schema,
        )
        request_count = server.request_count("POST", path)

    # The caller's edit happened after normalization; router-side validation
    # must still enforce the integer rule declared when the query started.
    assert count_rule["type"] == "string"
    assert response.data["parsed"] == {"count": 7}
    assert request_count == 3
    assert len(response.tool_trace) == 1
