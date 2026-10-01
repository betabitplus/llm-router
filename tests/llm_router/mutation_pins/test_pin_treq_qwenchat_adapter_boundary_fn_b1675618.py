# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY FN-B1675618
# pinned-by: delegate, one pin for 6 pins of QwenChatAdapter.build_payload
# kills: 14f4d9793d873316 40231175bc1ce35e 7a62ad64f09cc0a0 7f08bc96d2f666c5
# kills: 8fddc8d6682ad36b b2c437a6ff46e0ea
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

DESCRIPTOR = {
    "type": "function",
    "function": {
        "name": "lookup_weather",
        "description": "Look up weather",
        "parameters": {"type": "object", "properties": {}},
    },
}


def _request(**options: object) -> ProviderRequest:
    return ProviderRequest(
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
        **options,
    )


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_build_payload_options() -> None:
    adapter = QwenChatAdapter(base_url="http://localhost")
    tool = ToolDefinition(
        name="lookup_weather",
        description="Look up weather",
        parameters={"type": "object", "properties": {}},
        descriptor=DESCRIPTOR,
    )
    payload = adapter.build_payload(
        _request(
            temperature=1,
            seed=3.7,
            tool_registry=ToolRegistry(tools={"lookup_weather": tool}),
            tool_choice=ToolChoice(kind="none"),
            kwargs={"extra": "value"},
        )
    )
    assert payload["tools"] == [DESCRIPTOR]
    assert payload["tool_choice"] == "none"
    assert payload["extra"] == "value"
    assert payload["seed"] == 3
    assert isinstance(payload["seed"], int)
    assert payload["temperature"] == 1.0
    assert isinstance(payload["temperature"], float)

    as_text = adapter.build_payload(_request(temperature="0.5"))
    assert isinstance(as_text["temperature"], float)
    with pytest.raises(ValueError, match=r"."):
        adapter.build_payload(_request(temperature="not-a-number"))

    empty = adapter.build_payload(
        _request(tool_registry=ToolRegistry(tools={}), tool_choice=None)
    )
    assert "tool_choice" not in empty
    assert "tools" not in empty
