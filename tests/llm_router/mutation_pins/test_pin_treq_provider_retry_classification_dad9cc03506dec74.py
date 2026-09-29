# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION dad9cc03506dec74
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime import executor as executor_module
from llm_router._internal.runtime.executor import ProviderRouteExecutor

pytestmark = pytest.mark.verification_kind("unit")


class _Attempt:
    def __init__(self) -> None:
        self.error: BaseException | None = None

    def __enter__(self) -> _Attempt:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.error = exc
        return exc is not None


class _FakeRetrying:
    def __iter__(self) -> Any:
        last: BaseException | None = None
        for _ in range(3):
            attempt = _Attempt()
            yield attempt
            last = attempt.error
        if last is not None:
            raise last


class _Config:
    retry_policy = None


class _StubAdapter:
    def __init__(self, result: ProviderResult) -> None:
        self.seen: list[ProviderRequest] = []
        self._result = result

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.seen.append(request)
        if len(self.seen) == 1:
            msg = "transport down"
            raise ConnectionError(msg)
        return self._result


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_sync_execution_uses_resolved_adapter_and_retries_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH,
        provider_model="gemini-flash",
        credential=ProviderCredential(key_id=1, env_var="ENV_VAR", value="v"),
        messages=(),
    )
    expected = ProviderResult(
        data={},
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH,
        provider_model="gemini-flash",
        output_text="ok",
    )
    adapter = _StubAdapter(expected)
    requested: list[ProviderRequest] = []

    class _Executor(ProviderRouteExecutor):
        def _adapter_for(self, request: ProviderRequest) -> Any:
            requested.append(request)
            return adapter

    monkeypatch.setattr(
        executor_module,
        "build_provider_retrying",
        lambda **_kwargs: _FakeRetrying(),
    )
    instance = object.__new__(_Executor)
    instance._config = _Config()  # type: ignore[assignment]

    result = instance._execute_provider_sync(request)

    assert result is expected
    assert requested == [request]
    assert adapter.seen == [request, request]
