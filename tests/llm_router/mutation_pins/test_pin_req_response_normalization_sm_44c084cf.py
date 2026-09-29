# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-44C084CF
# pinned-by: claude-opus-5-5
from __future__ import annotations

from types import MappingProxyType, SimpleNamespace

import pytest

import llm_router

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_structured_data_is_json_safe_and_provider_is_plain_string() -> None:
    output = llm_router._internal.runtime.output
    result = output.ProviderResult(
        data=MappingProxyType({}),
        provider=llm_router.Provider.GOOGLE,
        model=llm_router.Model.GEMINI_FLASH_LITE,
        provider_model="parsed",
        output_text="parsed",
        usage=None,
        tool_calls=(),
        tool_call_metadata=(),
    )
    response = output.build_public_response(result, structured_data=SimpleNamespace())
    assert response.data["parsed"] == {
        "type": "SimpleNamespace",
        "preview": "namespace()",
    }
    assert type(response.provider) is str
    assert response.provider == "google"
