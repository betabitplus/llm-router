# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 3c58e8e9e5eaec8a
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from llm_router._internal.runtime import executor as executor_module
from llm_router._internal.runtime.executor import ProviderRouteExecutor

pytestmark = pytest.mark.verification_kind("unit")


@dataclass
class _Config:
    retry_policy: object | None = None


class _Attempt:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_args: object) -> bool:
        return False


class _Retrying:
    def __iter__(self):
        yield _Attempt()


class _FailingAdapter:
    def execute(self, _request: object) -> Any:
        msg = "provider failed"
        raise ValueError(msg)


def _run(monkeypatch: pytest.MonkeyPatch, *, retryable: bool) -> list[object]:
    logged: list[object] = []
    adapter = _FailingAdapter()
    monkeypatch.setattr(
        ProviderRouteExecutor, "_adapter_for", lambda _self, _request: adapter
    )
    monkeypatch.setattr(
        executor_module, "build_provider_retrying", lambda **_kw: _Retrying()
    )
    monkeypatch.setattr(
        executor_module, "is_retryable_provider_error", lambda _exc: retryable
    )
    monkeypatch.setattr(executor_module, "_retry_context", lambda _request: {})
    monkeypatch.setattr(
        executor_module,
        "log_retry_exhausted",
        lambda *_a, **kw: logged.append(kw["event_type"]),
    )
    monkeypatch.setattr(
        executor_module,
        "_provider_boundary_error",
        lambda _exc, **_kw: RuntimeError("boundary"),
    )
    executor = ProviderRouteExecutor(config=_Config())  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match=r"boundary"):
        executor._execute_provider_sync(object())  # type: ignore[arg-type]
    return logged


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_exhausted_event_logged_only_for_retryable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    permanent = _run(monkeypatch, retryable=False)
    transient = _run(monkeypatch, retryable=True)

    assert permanent == []
    assert transient == ["llm_router.provider.retry.exhausted"]
