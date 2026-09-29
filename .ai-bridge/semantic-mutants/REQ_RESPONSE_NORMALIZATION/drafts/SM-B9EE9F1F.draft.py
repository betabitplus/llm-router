# semantic-mutant: SM-B9EE9F1F
from __future__ import annotations

import pytest
from llm_router._api.types import Model, Provider, ToolCall
from llm_router._internal.providers.base import ProviderResult
from llm_router._internal.runtime.output import build_public_response

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_explicit_empty_overrides_do_not_leak_provider_values() -> None:
    call = ToolCall(id="call_1", name="lookup", args={"q": "x"})
    result = ProviderResult(
        data={},
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH_LITE,
        provider_model="parsed",
        output_text="parsed",
        usage=None,
        tool_calls=(call,),
        tool_call_metadata=(),
    )
    response = build_public_response(
        result, output_text="", tool_calls=(), tool_trace=()
    )
    assert response.output_text == ""
    assert response.tool_calls == []
