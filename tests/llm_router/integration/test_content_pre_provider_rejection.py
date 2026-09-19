from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from PIL import Image
from py_lib_testkit import evidence

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

_OPENAI_PATH = openai_chat_path()


def _invalid_content(case: str) -> Any:
    if case == "unsupported-top-level":
        return object()
    if case == "invalid-image-mode":
        return [Image.new("CMYK", (10, 10))]
    raise AssertionError(case)


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
@pytest.mark.coverage_item("VC_CONTENT_PRE_PROVIDER_REJECTION")
@pytest.mark.verification_kind("integration")
@pytest.mark.parametrize(
    ("case", "error_type", "message"),
    [
        pytest.param(
            "unsupported-top-level",
            TypeError,
            "Unsupported media value",
            id="unsupported-top-level",
        ),
        pytest.param(
            "invalid-image-mode",
            ValueError,
            "mode",
            id="invalid-image-mode",
        ),
    ],
)
def test_invalid_public_content_never_reaches_provider_boundary(
    case: str,
    error_type: type[Exception],
    message: str,
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
            with pytest.raises(error_type, match=message):
                router.query(_invalid_content(case))
        finally:
            install_config(current)

        request_count = server.request_count("POST", _OPENAI_PATH)
        evidence.observation(
            "Provider boundary sentinel",
            kind="boundary-interaction-check",
            payload={
                "boundary": "provider-http",
                "requests_received": request_count,
                "interaction": "none" if request_count == 0 else "substitute",
            },
        )

    assert request_count == 0
