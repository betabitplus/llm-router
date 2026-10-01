# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 14f4d9793d873316
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import (
    ToolChoice,
    ToolDefinition,
    ToolRegistry,
)
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_build_payload_preserves_tool_choice() -> None:
    tool_def = ToolDefinition(
        name="lookup_weather",
        description="Look up weather information",
        parameters={"type": "object", "properties": {}},
        descriptor={
            "type": "function",
            "function": {
                "name": "lookup_weather",
                "description": "Look up weather information",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    )
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=ProviderCredential(
            key_id=1,
            env_var="QWENCHAT_AUTH",
            value="auth-val",
        ),
        messages=[normalize_content("Hello")],
        tool_registry=ToolRegistry(tools={"lookup_weather": tool_def}),
        tool_choice=ToolChoice(kind="none"),
    )

    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000")
    payload = adapter.build_payload(request)

    assert "tool_choice" in payload
    assert payload["tool_choice"] == "none"
