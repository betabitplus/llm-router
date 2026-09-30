# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION SM-E1B20E59
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
    ProviderSentinelHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import openai_chat_path

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_none_part_is_rejected_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = openai_chat_path()
    current = get_config()
    provider_spec = current.catalog.providers[Provider.OPENROUTER]
    for env_var in provider_spec.api_key_env_vars.values():
        monkeypatch.setenv(env_var, "local-test-value")
    content = ["caption", None, ""]

    with ProviderSentinelHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    body=b'{"error":{"message":"provider must not be called"}}',
                )
            ]
        },
    ) as server:
        base_urls = dict(current.provider_base_urls)
        base_urls[Provider.OPENROUTER] = f"{server.base_url}/v1"
        replacement = replace(
            current,
            catalog=replace(current.catalog, provider_base_urls=base_urls),
        )
        install_config(replacement)
        try:
            router = LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                )
            )
            with pytest.raises(TypeError, match=r"Unsupported media value"):
                router.query(content)  # type: ignore[arg-type]
        finally:
            install_config(current)

        request_count = server.request_count("POST", path)

    assert request_count == 0
