# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION 4e35b24fc276e4ad
# pinned-by: claude-opus-5-5
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
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_width_at_max_passes_normalization_and_above_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    max_dimension = 16384
    openai_path = openai_chat_path()
    current = get_config()
    provider_spec = current.catalog.providers[Provider.OPENROUTER]
    for env_var in provider_spec.api_key_env_vars.values():
        monkeypatch.setenv(env_var, "local-test-value")

    with ProviderSentinelHTTPServer(
        port=0,
        routes={
            ("POST", openai_path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="ok"),
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
                    max_attempts=1,
                )
            )
            with pytest.raises(ValueError, match=r"too large"):
                router.query([Image.new("RGB", (max_dimension + 1, 10))])
            rejected_count = server.request_count("POST", openai_path)
            response = router.query([Image.new("RGB", (max_dimension, 10))])
            assert response is not None
        finally:
            install_config(current)

    assert rejected_count == 0
