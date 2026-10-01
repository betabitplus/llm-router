# semantic-mutant: SM-2DBB5B58
from __future__ import annotations

import pytest
from llm_router import Model, Provider, ToolCall
from llm_router._internal.providers.base import ProviderResult
from llm_router._internal.runtime.output import build_public_response

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_build_public_response_preserves_normalized_tool_calls_override() -> None:
    raw_tool = ToolCall(
        id="call_raw_001",
        name="provider_tool",
        args={"query": "test"},
    )
    normalized_tool = ToolCall(
        id="call_norm_001",
        name="standard_tool",
        args={"query": "test"},
    )
    result = ProviderResult(
        data={},
        provider=Provider.GOOGLE,
        model=Model.GEMINI_PRO,
        provider_model="gemini-3.1-pro-preview",
        output_text="",
        tool_calls=(raw_tool,),
    )
    response = build_public_response(
        result=result,
        tool_calls=[normalized_tool],
    )
    assert response.tool_calls == [normalized_tool]
