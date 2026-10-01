# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY FN-E736B01D
# pinned-by: delegate, one pin for 6 pins of QwenChatAdapter.abuild_payload
# kills: 14086e0bf74da773 36fb82fcc47860a2 7879b343f0d7cac0 8f495188e4365ff8
# kills: b1c0fd5ecaa6d923 cebb90925a422d7e
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider
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


def _request(**extra: object) -> ProviderRequest:
    credential = ProviderCredential(key_id=1, env_var="BASE_URL", value="value")
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=credential,
        messages=[normalize_content("hello")],
        **extra,
    )


def _registry() -> tuple[ToolRegistry, dict[str, object]]:
    parameters: dict[str, object] = {"type": "object", "properties": {}}
    descriptor: dict[str, object] = {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "Look up",
            "parameters": parameters,
        },
    }
    definition = ToolDefinition(
        name="lookup",
        description="Look up",
        parameters=parameters,
        descriptor=descriptor,
    )
    return ToolRegistry(tools={"lookup": definition}), descriptor


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_abuild_payload_semantics() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000/api")

    plain = await adapter.abuild_payload(_request())
    assert "tools" not in plain
    assert "tool_choice" not in plain

    empty = await adapter.abuild_payload(_request(tool_registry=ToolRegistry(tools={})))
    assert "tools" not in empty

    scalars = await adapter.abuild_payload(_request(temperature=1, seed=True))
    assert scalars["temperature"] == 1.0
    assert isinstance(scalars["temperature"], float)
    assert scalars["seed"] == 1
    assert type(scalars["seed"]) is int

    registry, descriptor = _registry()
    with_tools = await adapter.abuild_payload(_request(tool_registry=registry))
    assert "tool_choice" not in with_tools
    entry = next(iter(with_tools["tools"]))
    assert entry == descriptor
    assert entry is not descriptor
    entry["type"] = "mutated"
    assert descriptor["type"] == "function"

    choice_only = await adapter.abuild_payload(
        _request(tool_choice=ToolChoice(kind="auto"))
    )
    assert "tool_choice" in choice_only

    extra = await adapter.abuild_payload(
        _request(kwargs={"stream": True, "top_p": 0.8})
    )
    assert extra["stream"] is True
    assert extra["top_p"] == 0.8
