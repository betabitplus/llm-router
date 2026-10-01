# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 5c98f844a8369f15
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import ToolDefinition, ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_build_payload_includes_tools_when_tool_choice_is_none() -> None:
    descriptor = {
        "type": "function",
        "function": {
            "name": "lookup_weather",
            "description": "Get current weather for a given city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                },
                "required": ["city"],
            },
        },
    }
    tool = ToolDefinition(
        name="lookup_weather",
        description="Get current weather for a given city.",
        parameters=descriptor["function"]["parameters"],
        descriptor=descriptor,
    )
    registry = ToolRegistry(tools={"lookup_weather": tool})
    credential = ProviderCredential(
        key_id=1,
        env_var="QWENCHAT_AUTH_NAME",
        value="allowed_auth_value",
    )
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=credential,
        messages=[normalize_content("What is the weather in Paris?")],
        tool_registry=registry,
        tool_choice=None,
        temperature=0.0,
        seed=42,
    )
    adapter = QwenChatAdapter(base_url="http://localhost:8000")
    payload = adapter.build_payload(request)

    assert "tools" in payload
    assert payload["tools"] == [descriptor]
    assert next(iter(payload["tools"])) == descriptor
