# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION 4e35b24fc276e4ad
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest
from PIL import Image

from llm_router import (
    LLMRouter,
    LLMRouterError,
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
_MAX_DIMENSION = 16384


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_width_at_max_passes_normalization_and_above_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = get_config()
    provider_spec = current.catalog.providers[Provider.OPENROUTER]
    for env_var in provider_spec.api_key_env_vars.values():
        monkeypatch.setenv(env_var, "local-test-value")

    with ProviderSentinelHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    body=b'{"error":{"message":"sentinel"}}',
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
            with pytest.raises(ValueError, match=r"too large"):
                router.query([Image.new("RGB", (_MAX_DIMENSION + 1, 10))])
            rejected_count = server.request_count("POST", _OPENAI_PATH)
            with pytest.raises(LLMRouterError, match=r"(?s).*"):
                router.query([Image.new("RGB", (_MAX_DIMENSION, 10))])
        finally:
            install_config(current)

    assert rejected_count == 0
