# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 76cf360dbfb7ff62
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import (
    QwenChatAdapter,
    tool_choice_payload,
)

pytestmark = pytest.mark.verification_kind("unit")


class _StubChoice:
    kind = "none"


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_abuild_payload_preserves_tool_choice() -> None:
    value = "proxy-auth"
    credential = ProviderCredential(key_id=1, env_var="TEST_AUTH", value=value)
    choice = _StubChoice()
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=[normalize_content("Hello")],
        tool_registry=ToolRegistry({}),
        tool_choice=choice,
    )
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:1/api")
    payload = await adapter.abuild_payload(request)

    assert "tool_choice" in payload
    assert payload["tool_choice"] == tool_choice_payload(request)
