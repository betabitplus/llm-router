# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 1cb6c482c58e73ea
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
)
from llm_router._internal.runtime import executor as executor_module
from llm_router._internal.runtime.executor import (
    ProviderRouteExecutor,
    _provider_boundary_error,
)

pytestmark = pytest.mark.verification_kind("unit")


class _StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__("bad request")
        self.status_code = status_code


class _Config:
    retry_policy = None


class _Attempt:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_args: object) -> None:
        return None


class _Adapter:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def execute(self, _request: ProviderRequest) -> Any:
        raise self._exc


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.GROQ,
        model=Model.LLAMA_8B,
        provider_model="llama-8b",
        credential=ProviderCredential(key_id=1, env_var="ENV_VALUE", value="v"),
        messages=(),
    )


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
@pytest.mark.parametrize(
    ("exc", "retryable"),
    [
        (_StatusError(400), False),
        (ConnectionError("connection dropped"), True),
    ],
)
def test_sync_failure_raises_chained_boundary_error(
    monkeypatch: pytest.MonkeyPatch, exc: Exception, retryable: bool
) -> None:
    request = _request()
    monkeypatch.setattr(
        executor_module, "build_provider_retrying", lambda **_k: [_Attempt()]
    )
    monkeypatch.setattr(
        executor_module, "is_retryable_provider_error", lambda _e: retryable
    )
    monkeypatch.setattr(executor_module, "log_retry_exhausted", lambda *_a, **_k: None)
    monkeypatch.setattr(executor_module, "_retry_context", lambda _r: {})

    executor = object.__new__(ProviderRouteExecutor)
    executor._config = _Config()
    executor._adapter_for = lambda _r: _Adapter(exc)

    expected = _provider_boundary_error(exc, request=request)

    with pytest.raises(Exception, match=r".*") as info:
        executor._execute_provider_sync(request)

    assert type(info.value) is type(expected)
    assert info.value.__cause__ is exc
    if type(expected) is not RuntimeError:
        assert type(info.value) is not RuntimeError
