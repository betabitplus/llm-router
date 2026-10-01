# mutation-pin: REQ_STRUCTURED_OUTPUT_REPAIR 759bb71cc9f30188
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


class Empty(BaseModel):
    def __bool__(self) -> bool:
        return False


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def ok_response(body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]")
def test_structured_output_repair_clears_tool_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_var = "OPENROUTER_API_KEY_1"
    credential_value = "route-credential"
    monkeypatch.setenv(env_var, credential_value)
    chat_path = openai_chat_path()
    routes = {
        ("POST", chat_path): [
            ok_response(openai_success_response(text="not json at all")),
            ok_response(openai_success_response(text="{}")),
        ]
    }
    router = LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        temperature=0.0,
        seed=7,
    )
    original_config = get_config()
    install_fast_worker_runtime_config(structured_output_max_attempts=2)
    try:
        with (
            ScriptedHTTPServer(port=0, routes=routes) as server,
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
        ):
            response = router.query(
                "Return an empty object.",
                tools=[add],
                tool_choice="auto",
                response_schema=Empty,
            )
            records = server.recorded_requests("POST", chat_path)
    finally:
        install_config(original_config)

    assert response.data["parsed"] == {}
    assert len(records) == 2
    first_req, repair_req = records
    first_payload = parse_json_object(first_req.body.decode())
    repair_payload = parse_json_object(repair_req.body.decode())
    assert first_payload.get("tool_choice") == "auto"
    assert "tool_choice" not in repair_payload
