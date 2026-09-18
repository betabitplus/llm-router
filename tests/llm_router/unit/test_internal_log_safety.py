from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest

pytestmark = pytest.mark.verification_kind("unit")


def _marker(label: str) -> str:
    return f"protected-{label}-fixture"


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
@pytest.mark.coverage_item("VC_SECURITY_LOG_CONTEXT_FIELDS")
def test_provider_request_log_context_is_an_exact_safe_metadata_allowlist() -> None:
    credential = _marker("credential")
    prompt = _marker("prompt")
    provider_kwarg = _marker("provider-kwarg")
    request = ProviderRequest(
        request_id="req-safe-log-context",
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="provider-model-private-detail",
        credential=ProviderCredential(
            key_id=7,
            env_var="OPENROUTER_API_KEY_7",
            value=credential,
        ),
        messages=[normalize_content(prompt)],
        kwargs={"custom_payload": provider_kwarg},
        route_index=3,
    )

    context = request.log_context()

    assert context == {
        "request_id": "req-safe-log-context",
        "provider": Provider.OPENROUTER.value,
        "model": Model.DEEPSEEK_V3.value,
        "key_id": 7,
        "route_index": 3,
    }
    rendered = repr(context)
    assert credential not in rendered
    assert prompt not in rendered
    assert provider_kwarg not in rendered
    assert request.provider_model not in rendered
