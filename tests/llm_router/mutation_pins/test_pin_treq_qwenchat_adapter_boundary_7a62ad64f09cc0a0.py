# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 7a62ad64f09cc0a0
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_empty_registry_without_tool_choice_omits_tool_keys() -> None:
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=ProviderCredential(
            key_id=1,
            env_var="QWENCHAT_API_KEY_1",
            value="value",
        ),
        messages=[normalize_content("hello")],
        temperature=0.5,
        seed=7,
        tool_registry=ToolRegistry(tools={}),
        tool_choice=None,
    )
    adapter = QwenChatAdapter(base_url="http://localhost")
    payload = adapter.build_payload(request)
    assert "tool_choice" not in payload
    assert "tools" not in payload
    assert payload["model"] == "qwen-max-latest"
