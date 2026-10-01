# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION SM-AA98B36D
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    Session,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    qwen_chat_path,
    qwen_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_success_remembers_original_multipart_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("QWENCHAT_API_KEY_1", value)
    original_config = get_config()
    path = qwen_chat_path()
    parts = ["Describe the scene.", "Answer briefly."]
    session = Session(system=None)
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text="a quiet street"),
                )
            ]
        },
    ) as server:
        base_urls = dict(original_config.provider_base_urls)
        base_urls[Provider.QWENCHAT] = f"{server.base_url}/api"
        catalog = replace(original_config.catalog, provider_base_urls=base_urls)
        install_config(replace(original_config, catalog=catalog))
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            session=session,
            temperature=0.0,
        )
        try:
            response = asyncio.run(router.aquery(parts))
        finally:
            install_config(original_config)

    assert response.output_text == "a quiet street"
    user_turn = next(iter(session.history))
    assert user_turn.parts == tuple(parts)
