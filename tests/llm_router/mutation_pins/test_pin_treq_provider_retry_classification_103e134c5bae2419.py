# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 103e134c5bae2419
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.providers.base import ProviderResult
from llm_router._internal.runtime import executor as executor_module
from llm_router._internal.runtime.executor import ProviderRouteExecutor

pytestmark = pytest.mark.verification_kind("unit")


class _Config:
    retry_policy = None


class _Attempt:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return exc_type is not None and issubclass(exc_type, ConnectionError)


class _Adapter:
    def __init__(self, result: ProviderResult) -> None:
        self.requests: list[object] = []
        self._result = result

    def execute(self, request: object) -> ProviderResult:
        self.requests.append(request)
        if len(self.requests) == 1:
            msg = "transport down"
            raise ConnectionError(msg)
        return self._result


def _fake_retrying(**_kwargs: Any) -> Any:
    for _ in range(3):
        yield _Attempt()


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_retryable_transport_error_is_retried_and_result_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = ProviderResult(
        data={"ok": True},
        provider=Provider.GROQ,
        model=Model.LLAMA_8B,
        provider_model="llama-8b",
        output_text="hello",
    )
    adapter = _Adapter(result)
    seen: list[object] = []

    def adapter_for(request: object) -> _Adapter:
        seen.append(request)
        return adapter

    monkeypatch.setattr(executor_module, "build_provider_retrying", _fake_retrying)
    executor = ProviderRouteExecutor(config=_Config())
    monkeypatch.setattr(executor, "_adapter_for", adapter_for)
    request = object()

    returned = executor._execute_provider_sync(request)

    assert seen == [request]
    assert adapter.requests == [request, request]
    assert returned is result
