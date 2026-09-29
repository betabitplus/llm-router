# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 9d019d63a7b5816c
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_build_payload_omits_tool_choice_when_unset() -> None:
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=ProviderCredential(
            key_id=1,
            env_var="QWENCHAT_API_KEY_1",
            value="secret",
        ),
        messages=[normalize_content("hello")],
        temperature=None,
        seed=None,
        tool_registry=None,
        tool_choice=None,
    )
    adapter = QwenChatAdapter(base_url="http://localhost:8000")

    payload = adapter.build_payload(request)

    assert "tool_choice" not in payload
    assert "tools" not in payload
    assert payload["model"] == "qwen-max-latest"
    assert payload["stream"] is False
