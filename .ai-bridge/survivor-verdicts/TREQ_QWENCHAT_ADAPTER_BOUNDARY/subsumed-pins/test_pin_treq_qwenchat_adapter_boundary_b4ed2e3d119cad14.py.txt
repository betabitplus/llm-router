# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY b4ed2e3d119cad14
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


def _request(registry: ToolRegistry | None) -> ProviderRequest:
    return ProviderRequest(
        request_id="r1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=ProviderCredential(
            key_id=1, env_var="QWENCHAT_API_KEY_1", value="value"
        ),
        messages=[normalize_content("hello")],
        tool_registry=registry,
    )


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_empty_tool_registry_omits_tools_key() -> None:
    adapter = QwenChatAdapter(base_url="http://localhost", timeout_seconds=600.0)
    empty = adapter.build_payload(_request(ToolRegistry(tools={})))
    none = adapter.build_payload(_request(None))
    assert "tools" not in none
    assert "tools" not in empty
    assert empty == none
