# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT FN-98E4D6A0
# pinned-by: delegate, one pin for 4 pins of normalize_schema
# kills: 155610404a9b2a0a 2ac6551daf76c11a 8585b2a84ecd44f0 SM-9C5C73BC
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

_SCHEMA_ID = "https://example.com/stock_count"


def scripted(body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_structured_schema_contract(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    value = "local-openrouter-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    original = get_config()
    request.addfinalizer(lambda: install_config(original))
    install_fast_worker_runtime_config(structured_output_max_attempts=2)

    count_rule: dict[str, object] = {"type": "integer", "minimum": 1}
    # A read-only mapping (class namespace) without a title, named by "$id".
    holder = type(
        "StockSchema",
        (),
        {
            "__slots__": (),
            "$id".replace("$", "$"): _SCHEMA_ID,
            "type": "object",
            "properties": {"count": count_rule},
            "required": ["count"],
        },
    )
    schema = holder.__dict__

    def lookup_stock(*, sku: str) -> dict[str, str]:
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

    with pytest.raises(
        TypeError,
        match=r"^response_schema must be a Pydantic model type"
        r" or JSON schema mapping\.$",
    ):
        router.query("report", response_schema="not a schema")

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
        recorded = server.recorded_requests("POST", path)
        request_count = server.request_count("POST", path)

    last_body = json.loads(recorded[-1].body)
    assert last_body["response_format"]["json_schema"]["name"] == _SCHEMA_ID
    # The caller's nested edit happened after normalization; the declared
    # integer rule must still reject "seven" and force a second attempt.
    assert count_rule["type"] == "string"
    assert response.data["parsed"] == {"count": 7}
    assert request_count == 3
    assert len(response.tool_trace) == 1
