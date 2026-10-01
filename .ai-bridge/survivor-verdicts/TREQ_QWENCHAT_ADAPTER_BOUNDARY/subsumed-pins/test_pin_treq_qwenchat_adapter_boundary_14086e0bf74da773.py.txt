# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 14086e0bf74da773
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import ToolDefinition, ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_abuild_payload_tools_are_copies_of_descriptor() -> None:
    parameters: dict[str, object] = {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    }
    descriptor: dict[str, object] = {
        "type": "function",
        "function": {
            "name": "lookup_weather",
            "description": "Fetch weather information for a given city.",
            "parameters": parameters,
        },
    }
    tool_def = ToolDefinition(
        name="lookup_weather",
        description="Fetch weather information for a given city.",
        parameters=parameters,
        descriptor=descriptor,
    )
    registry = ToolRegistry(tools={"lookup_weather": tool_def})
    credential = ProviderCredential(
        key_id=1,
        env_var="ENV_VAR",
        value="credential_value",
    )
    message = normalize_content("What is the weather in Paris?")
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=credential,
        messages=[message],
        tool_registry=registry,
    )
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000")
    payload = await adapter.abuild_payload(request)

    tool_entry = next(iter(payload["tools"]))

    assert tool_entry == descriptor
    assert tool_entry is not descriptor

    tool_entry["type"] = "mutated"

    assert descriptor["type"] == "function"
