# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 18f725f3ce572a15
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

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
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_typeless_mapping_schema_is_accepted_and_validates_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "route-credential")
    schema = {
        "title": "city_report",
        "properties": {
            "city": {"type": "string", "minLength": 1},
            "population": {"type": "integer", "minimum": 0},
        },
        "required": ["city"],
    }
    body = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text='{"city": "Oslo", "population": 7}'),
    )
    routes = {("POST", openai_chat_path()): [body]}
    router = LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        temperature=0.0,
        seed=7,
    )
    original_config = get_config()
    install_fast_worker_runtime_config(structured_output_max_attempts=1)
    try:
        with (
            ScriptedHTTPServer(port=0, routes=routes) as server,
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
        ):
            response = router.query("Describe Oslo.", response_schema=schema)
    finally:
        install_config(original_config)

    assert response.data["parsed"] == {"city": "Oslo", "population": 7}
