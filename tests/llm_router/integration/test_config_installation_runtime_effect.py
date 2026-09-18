from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
@pytest.mark.coverage_item("VC_CONFIG_INSTALLATION_RUNTIME_EFFECT")
@pytest.mark.verification_kind("integration")
def test_installed_replacement_changes_subsequent_provider_request_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = get_config()
    replacement_key_id = current.default_key_id + 1
    replacement = replace(current, default_key_id=replacement_key_id)
    monkeypatch.setenv(
        f"{Provider.OPENROUTER.name}_API_KEY_{replacement_key_id}",
        "replacement-runtime-key",
    )
    path = openai_chat_path()

    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="replacement-active"),
                )
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            install_config(replacement)
            response = LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                )
            ).query("confirm replacement configuration")

        recorded = server.recorded_requests("POST", path)

    assert response.output_text == "replacement-active"
    assert len(recorded) == 1
    assert recorded[0].headers["Authorization"] == "Bearer replacement-runtime-key"
