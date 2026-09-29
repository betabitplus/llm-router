# semantic-mutant: SM-44C084CF
from __future__ import annotations

from types import SimpleNamespace

import pytest
from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderResult
from llm_router._internal.runtime.output import build_public_response

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_public_response_is_json_safe_with_plain_provider_value() -> None:
    result = ProviderResult(
        data={},
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH_LITE,
        provider_model="parsed",
        output_text="parsed",
    )
    response = build_public_response(
        result,
        output_text="parsed",
        structured_data=SimpleNamespace(),
    )
    assert type(response.provider) is str
    assert response.provider == "google"
    assert isinstance(response.data["parsed"], dict)
    assert response.data["parsed"]["type"] == "SimpleNamespace"
