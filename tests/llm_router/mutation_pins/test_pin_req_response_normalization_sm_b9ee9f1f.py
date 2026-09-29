# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-B9EE9F1F
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

import llm_router

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_explicit_empty_text_and_tool_calls_override_provider_values() -> None:
    providers = llm_router._internal.providers.base
    output = llm_router._internal.runtime.output
    result = providers.ProviderResult(
        data={},
        provider=llm_router.Provider.GOOGLE,
        model=llm_router.Model.GEMINI_FLASH_LITE,
        provider_model="gemini-3.5-flash-lite",
        output_text="provider text",
        usage=llm_router.UsageStats(input_tokens=12, output_tokens=5, total_tokens=17),
        tool_calls=(llm_router.ToolCall(id="call-1", name="lookup", args={"q": "x"}),),
    )
    response = output.build_public_response(result, output_text="", tool_calls=())
    assert response.output_text == ""
    assert response.tool_calls == []
