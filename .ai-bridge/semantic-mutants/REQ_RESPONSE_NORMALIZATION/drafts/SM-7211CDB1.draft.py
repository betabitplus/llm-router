# semantic-mutant: SM-7211CDB1
from __future__ import annotations

import pytest
from llm_router import Model, Provider
from llm_router._internal.runtime.output import (
    ProviderResult,
    build_public_response,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_explicit_empty_text_and_tool_calls_are_kept() -> None:
    result = ProviderResult(
        data={},
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH_LITE,
        provider_model="parsed",
        output_text="parsed",
        usage=None,
        tool_calls=(),
        tool_call_metadata=(),
    )
    response = build_public_response(
        result, output_text="", tool_calls=(), tool_trace=()
    )
    assert response.output_text == ""
    assert response.tool_calls == []
