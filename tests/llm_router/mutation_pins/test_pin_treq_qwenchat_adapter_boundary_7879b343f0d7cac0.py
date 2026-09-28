# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 7879b343f0d7cac0
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
)
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
@pytest.mark.asyncio
async def test_abuild_payload_omits_tools_when_registry_missing_or_empty() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:1/api")
    credential = ProviderCredential(1, "LLM_ROUTER_ENV", "test-value")
    messages = [normalize_content("hello")]

    request_without_registry = ProviderRequest(
        request_id="req-without-registry",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=messages,
        tool_registry=None,
    )
    payload_without_registry = await adapter.abuild_payload(request_without_registry)
    assert "tools" not in payload_without_registry

    request_with_empty_registry = ProviderRequest(
        request_id="req-empty-registry",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=messages,
        tool_registry=ToolRegistry(tools={}),
    )
    payload_with_empty_registry = await adapter.abuild_payload(
        request_with_empty_registry
    )
    assert "tools" not in payload_with_empty_registry
