# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION e9186235c6377e40
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
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")

_MAX_DIMENSION = 16384


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_height_at_max_accepted_and_above_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = get_config()
    provider_spec = current.catalog.providers[Provider.OPENROUTER]
    for env_var in provider_spec.api_key_env_vars.values():
        monkeypatch.setenv(env_var, "local-test-value")
    path = openai_chat_path()
    at_limit = Image.new("RGB", (32, _MAX_DIMENSION))
    too_tall = Image.new("RGB", (32, _MAX_DIMENSION + 1))

    with ProviderSentinelHTTPServer(
        port=0,
        routes={
            ("POST", path): [
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
        install_config(
            replace(
                current,
                catalog=replace(current.catalog, provider_base_urls=base_urls),
            )
        )
        try:
            router = LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                )
            )
            accepted = router.query([at_limit])
            with pytest.raises(ValueError, match=r"too large"):
                router.query([too_tall])
        finally:
            install_config(current)

        assert accepted.output_text == "ok"
        assert server.request_count("POST", path) == 1
