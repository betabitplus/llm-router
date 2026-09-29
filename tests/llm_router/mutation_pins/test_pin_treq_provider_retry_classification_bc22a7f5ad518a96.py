# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION bc22a7f5ad518a96
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


class _Config:
    retry_policy = None


class _Attempt:
    def __init__(self, owner: _Retrying) -> None:
        self._owner = owner

    def __enter__(self) -> None:
        return None

    def __exit__(self, _exc_type: Any, exc: Any, _tb: Any) -> bool:
        if exc is None:
            return False
        self._owner.failed = True
        return True


class _Retrying:
    def __init__(self) -> None:
        self.failed = False

    def __iter__(self) -> Any:
        yield _Attempt(self)
        if self.failed:
            yield _Attempt(self)


class _Adapter:
    def __init__(self, result: ProviderResult) -> None:
        self.requests: list[ProviderRequest] = []
        self._result = result

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        if len(self.requests) == 1:
            msg = "transient transport failure"
            raise ConnectionError(msg)
        return self._result


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_sync_retry_returns_adapter_result_after_transient_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.GROQ,
        model=Model.LLAMA_8B,
        provider_model="llama-8b",
        credential=ProviderCredential(key_id=1, env_var="ENV_VAR", value="v"),
        messages=(),
    )
    result = ProviderResult(
        data={},
        provider=Provider.GROQ,
        model=Model.LLAMA_8B,
        provider_model="llama-8b",
        output_text="hello",
    )
    adapter = _Adapter(result)
    monkeypatch.setattr(
        executor_module,
        "build_provider_retrying",
        lambda **_kwargs: _Retrying(),
    )
    executor = ProviderRouteExecutor(config=_Config())  # type: ignore[arg-type]
    monkeypatch.setattr(executor, "_adapter_for", lambda _request: adapter)

    returned = executor._execute_provider_sync(request)

    assert len(adapter.requests) == 2
    assert adapter.requests[1] is request
    assert returned is result
