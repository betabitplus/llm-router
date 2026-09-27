# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 40231175bc1ce35e
# pinned-by: claude-opus-5-5: The mutant quietly removes the registered tool descriptors from the QwenChat payload. The provider never sees the tools, so the normalized request is not carried across the native boundary, which REQ_PROVIDER_ADAPTER_INTEROPERABILITY requires. Running the confirmed input shows the 'tools' key is mis
from __future__ import annotations

import pytest
from llm_router import Model, Provider
from llm_router._internal.capabilities.tools import ToolDefinition, ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_build_payload_includes_registered_tools() -> None:
    tool_descriptor = {
        "type": "function",
        "function": {
            "name": "fetch_weather",
            "description": "Fetch the current weather for a specified location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or zip code",
                    },
                },
                "required": ["location"],
            },
        },
    }
    tool = ToolDefinition(
        name="fetch_weather",
        description="Fetch the current weather for a specified location",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or zip code",
                },
            },
            "required": ["location"],
        },
        descriptor=tool_descriptor,
    )
    request = ProviderRequest(
        request_id="req-qwen-tool-payload-001",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=ProviderCredential(
            key_id=1,
            env_var="QWEN_API_KEY",
            value="secret-api-key",
        ),
        messages=(),
        tool_registry=ToolRegistry(tools={"fetch_weather": tool}),
        kwargs={},
    )
    adapter = QwenChatAdapter(base_url="http://localhost:8000", timeout_seconds=600.0)

    payload = adapter.build_payload(request)

    assert "tools" in payload
    assert payload["tools"] == [dict(tool_descriptor)]
