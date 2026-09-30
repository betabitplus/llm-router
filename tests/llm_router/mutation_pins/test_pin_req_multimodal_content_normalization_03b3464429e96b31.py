# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION 03b3464429e96b31
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest
from PIL import Image

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

_OPENAI_PATH = openai_chat_path()


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_with_valid_width_and_short_height_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = get_config()
    provider_spec = current.catalog.providers[Provider.OPENROUTER]
    for env_var in provider_spec.api_key_env_vars.values():
        monkeypatch.setenv(env_var, "local-test-key")

    with ProviderSentinelHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
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
            with pytest.raises(ValueError, match=r"too small"):
                router.query([Image.new("RGB", (32, 0))])
        finally:
            install_config(current)

        request_count = server.request_count("POST", _OPENAI_PATH)

    assert request_count == 0
