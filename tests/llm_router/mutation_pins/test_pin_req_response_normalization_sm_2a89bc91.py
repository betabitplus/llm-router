# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-2A89BC91
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

import llm_router

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_normalized_output_text_overrides_raw_provider_text() -> None:
    types = llm_router._api.types
    base = llm_router._internal.providers.base
    output = llm_router._internal.runtime.output
    usage = types.UsageStats(input_tokens=12, output_tokens=18, total_tokens=30)
    result = base.ProviderResult(
        data={},
        provider=types.Provider.GOOGLE,
        model=types.Model.GEMINI_FLASH_LITE,
        provider_model="gemini-raw",
        output_text="raw provider text",
        usage=usage,
        tool_calls=(),
        tool_call_metadata=(),
    )
    response = output.build_public_response(result, output_text="normalized")
    assert response.output_text == "normalized"
    assert response.provider == "google"
    assert response.usage == usage
