# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY b1c0fd5ecaa6d923
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
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
)
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


def _request(
    request_id: str,
    registry: ToolRegistry | None,
    choice: ToolChoice | None,
) -> ProviderRequest:
    credential = ProviderCredential(key_id=1, env_var="BASE_URL", value="value")
    return ProviderRequest(
        request_id=request_id,
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=credential,
        messages=[normalize_content("Hello world")],
        tool_registry=registry,
        tool_choice=choice,
    )


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_abuild_payload_tool_choice_only_when_set() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000/api")
    parameters = {"type": "object", "properties": {}}
    definition = ToolDefinition(
        name="lookup",
        description="Look up a value",
        parameters=parameters,
        descriptor={
            "type": "function",
            "function": {
                "name": "lookup",
                "description": "Look up a value",
                "parameters": parameters,
            },
        },
    )
    registry = ToolRegistry(tools={"lookup": definition})

    with_tools = await adapter.abuild_payload(_request("req-a", registry, None))
    assert "tools" in with_tools
    assert "tool_choice" not in with_tools

    no_registry = await adapter.abuild_payload(
        _request("req-b", None, ToolChoice(kind="auto"))
    )
    assert "tool_choice" in no_registry
