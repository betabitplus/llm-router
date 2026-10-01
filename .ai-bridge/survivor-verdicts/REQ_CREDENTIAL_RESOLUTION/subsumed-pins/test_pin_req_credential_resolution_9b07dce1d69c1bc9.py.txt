# mutation-pin: REQ_CREDENTIAL_RESOLUTION 9b07dce1d69c1bc9
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
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
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    qwen_chat_path,
    qwen_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_qwenchat_request_runs_without_bearer_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QWENCHAT_API_KEY_1", raising=False)
    path = qwen_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text="ok"),
                )
            ]
        },
    ) as server:
        config = get_config()
        base_urls = dict(config.catalog.provider_base_urls)
        base_urls[Provider.QWENCHAT] = f"{server.base_url}/api"
        install_config(
            replace(
                config,
                catalog=replace(config.catalog, provider_base_urls=base_urls),
            )
        )
        router = LLMRouter(
            RouterProfile(
                model=Model.QWEN_MAX_LATEST,
                provider=Provider.QWENCHAT,
                key_id=1,
            ),
            temperature=0.0,
            seed=1,
        )

        response = router.query("Reply with one word.")
        install_config(config)

        assert response.output_text == "ok"
        assert server.request_count("POST", path) == 1
