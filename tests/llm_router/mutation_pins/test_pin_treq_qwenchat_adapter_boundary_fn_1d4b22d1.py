# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY FN-1D4B22D1
# pinned-by: delegate, one pin for 3 pins of QwenChatAdapter.execute
# kills: 8654a7b1099c3580 aeeb7e44dc927403 cb633e63a453812c
from __future__ import annotations

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter, transport_failure

pytestmark = pytest.mark.verification_kind("unit")

BASE_URL = "http://127.0.0.1:1"


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=ProviderCredential(
            key_id=1,
            env_var="QWEN_VALUE",
            value="value",
        ),
        messages=[normalize_content("ping")],
    )


def _failure(timeout_seconds: float) -> ProviderError:
    adapter = QwenChatAdapter(base_url=BASE_URL, timeout_seconds=timeout_seconds)
    with pytest.raises(ProviderError, match=r".+") as exc_info:
        adapter.execute(_request())
    return exc_info.value


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_execute_transport_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _failure(1.0)
    base_cause = baseline.__cause__
    assert isinstance(base_cause, Exception)

    # The public message is the normalized transport failure's message.
    expected = transport_failure(request=_request(), exc=base_cause).message
    assert expected
    assert str(baseline).endswith(f"Reason: {expected}")

    # The configured timeout is handed to the HTTP client: an invalid value
    # changes how the transport fails, while the default timeout would not.
    invalid_timeout = _failure(-1.0)
    assert type(invalid_timeout.__cause__) is not type(base_cause)

    # Ambient proxy settings are ignored (trust_env disabled): a proxy URL
    # that httpx would reject must not change the failure.
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, "badscheme://proxy.invalid:1")
    proxied = _failure(1.0)
    assert type(proxied.__cause__) is type(base_cause)
