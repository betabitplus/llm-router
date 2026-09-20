"""Parent provider-interoperability matrix with one evidence identity per family."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest

from tests.llm_router.integration import (
    test_aistudio_adapter_fake,
    test_gemini_webapi_adapter_fake,
    test_google_genai_adapter_fake,
    test_openai_compatible_adapter_fake_server,
    test_qwenchat_adapter_fake,
)


def _google_async_success() -> None:
    asyncio.run(
        test_google_genai_adapter_fake.test_async_google_adapter_uses_sdk_async_boundary()
    )


_PROVIDER_EXERCISES: tuple[object, ...] = (
    pytest.param(
        test_openai_compatible_adapter_fake_server.test_sync_success_crosses_openai_http_boundary,
        id="openai-compatible",
        marks=pytest.mark.coverage_path("OpenAI-compatible"),
    ),
    pytest.param(
        test_qwenchat_adapter_fake.test_qwenchat_text_crosses_proxy_http_boundary,
        id="qwenchat",
        marks=pytest.mark.coverage_path("QwenChat"),
    ),
    pytest.param(
        test_aistudio_adapter_fake.test_aistudio_text_uses_openai_compatible_transport,
        id="aistudio",
        marks=pytest.mark.coverage_path("AI Studio"),
    ),
    pytest.param(
        test_gemini_webapi_adapter_fake.test_sync_gemini_webapi_crosses_sdk_boundary,
        id="gemini-webapi",
        marks=pytest.mark.coverage_path("Gemini WebAPI"),
    ),
    pytest.param(
        _google_async_success,
        id="google-genai",
        marks=pytest.mark.coverage_path("Google GenAI"),
    ),
)


@pytest.mark.verifies("REQ_PROVIDER_ADAPTER_INTEROPERABILITY[revision==2]")
@pytest.mark.coverage_item("VC_PROVIDER_ADAPTER_INTEROPERABILITY_MATRIX")
@pytest.mark.verification_kind("integration")
@pytest.mark.parametrize("exercise", _PROVIDER_EXERCISES)
def test_provider_adapter_interoperability_matrix(exercise: Callable[[], None]) -> None:
    """Each supported adapter family preserves one normalized success boundary."""
    exercise()
