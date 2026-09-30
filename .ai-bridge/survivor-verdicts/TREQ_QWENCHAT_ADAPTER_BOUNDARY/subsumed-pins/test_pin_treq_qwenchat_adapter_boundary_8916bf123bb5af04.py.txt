# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 8916bf123bb5af04
# pinned-by: claude-opus-5-5
from __future__ import annotations

import dataclasses

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@dataclasses.dataclass(frozen=True)
class ToolDefinition:
    descriptor: dict[str, object]


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_abuild_payload_preserves_tools_from_tool_registry() -> None:
    descriptor: dict[str, object] = {
        "type": "function",
        "function": {
            "name": "lookup_weather",
            "description": "Fetch weather information for a given city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                },
                "required": ["city"],
            },
        },
    }
    tool_def = ToolDefinition(descriptor=descriptor)
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

    assert payload["tools"] == [dict(tool_def.descriptor)]
