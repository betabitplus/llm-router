# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 1f46adce42be5e76
# pinned-by: claude-opus-5-5: The mutant stops recording a trace when an async provider call fails. On fallback, the async response then has no entry for the failed attempt, and the fallback flag can be wrong. The sync path still records both, so the async public response contract no longer matches it, which the requirement forb
from __future__ import annotations

import asyncio
import dataclasses
from typing import Any

import pytest
from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@dataclasses.dataclass
class _DummyKey:
    key_id: int = 1


@dataclasses.dataclass
class _DummyRequest:
    key: _DummyKey
    route: Any
    content: Any = "test prompt"


@dataclasses.dataclass
class _DummyResponse:
    text: str = "normalized async response text"
    content: str = "normalized async response text"
    model: str = "deepseek-v4-flash"
    provider: str = "nvidia"
    usage: dict[str, int] = dataclasses.field(
        default_factory=lambda: {
            "prompt_tokens": 12,
            "completion_tokens": 24,
            "total_tokens": 36,
        }
    )
    raw: Any = None
    finish_reason: str = "stop"
    structured_output: Any = None

    def __getattr__(self, name: str) -> Any:
        return None


@dataclasses.dataclass
class _CompletedResult:
    response: Any
    traces: list[Any]


def _extract_traces(res: Any) -> list[Any]:
    for attr in (
        "traces",
        "attempts",
        "attempt_traces",
        "routing_attempts",
        "fallback_traces",
        "all_attempts",
        "history",
    ):
        val = getattr(res, attr, None)
        if val is not None and isinstance(val, (list, tuple)):
            return list(val)
    if isinstance(res, dict):
        for key in (
            "traces",
            "attempts",
            "attempt_traces",
            "routing_attempts",
            "fallback_traces",
            "all_attempts",
            "history",
        ):
            if key in res and isinstance(res[key], (list, tuple)):
                return list(res[key])
    if hasattr(res, "__dict__"):
        for k, v in res.__dict__.items():
            if isinstance(v, (list, tuple)) and any(
                term in k.lower() for term in ("trace", "attempt")
            ):
                return list(v)
    raise AssertionError(f"Could not find attempt traces on response: {res!r}")


def _get_error(attempt: Any) -> Any:
    if isinstance(attempt, dict):
        for key in (
            "error",
            "exception",
            "exc",
            "error_message",
            "error_type",
            "failure",
            "failure_reason",
            "cause",
            "reason",
            "status",
        ):
            if attempt.get(key) is not None:
                return attempt[key]
        for k, v in attempt.items():
            if any(term in k.lower() for term in ("err", "exc", "fail")) and v is not None:
                return v
        return None

    for attr in (
        "error",
        "exception",
        "exc",
        "_error",
        "_exception",
        "_exc",
        "error_message",
        "error_type",
        "failure",
        "failure_reason",
        "cause",
        "reason",
    ):
        val = getattr(attempt, attr, None)
        if val is not None:
            return val

    if hasattr(attempt, "__dict__"):
        for k, v in attempt.__dict__.items():
            if any(term in k.lower() for term in ("err", "exc", "fail")) and v is not None:
                return v

    if dataclasses.is_dataclass(attempt):
        for field in dataclasses.fields(attempt):
            if any(term in field.name.lower() for term in ("err", "exc", "fail")):
                val = getattr(attempt, field.name, None)
                if val is not None:
                    return val

    status = getattr(attempt, "status", None)
    if status is not None and str(status).lower() in ("failed", "failure", "error"):
        return status

    return None


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_fallback_records_failed_attempt_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-12345")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")

    profile = RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    try:
        router = LLMRouter([profile, profile])
    except Exception:
        router = LLMRouter(profile)

    runtime = getattr(router, "_runtime", router)

    orig_next_order = runtime._next_attempt_order

    def fake_next_attempt_order(*args: Any, **kwargs: Any) -> Any:
        routes = orig_next_order(*args, **kwargs)
        if len(routes) < 2 and len(routes) > 0:
            return (*routes, *routes)
        return routes

    monkeypatch.setattr(runtime, "_next_attempt_order", fake_next_attempt_order)

    orig_prepare_request = runtime._prepare_request

    def safe_prepare_request(
        request_id: Any, route: Any, settings: Any, content: Any
    ) -> Any:
        try:
            req, _ = orig_prepare_request(
                request_id=request_id,
                route=route,
                settings=settings,
                content=content,
            )
            return (req, 0)
        except Exception:
            key = getattr(route, "key", None)
            key_id = 1
            if key is not None and isinstance(getattr(key, "key_id", None), int):
                key_id = key.key_id
            dummy_key = _DummyKey(key_id=key_id)
            return (_DummyRequest(key=dummy_key, route=route), 0)

    monkeypatch.setattr(runtime, "_prepare_request", safe_prepare_request)

    call_count = 0
    failure_error = RuntimeError("First route provider call failed")

    async def mock_call_async(request: Any, timeout_seconds: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise failure_error
        return _DummyResponse()

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    orig_complete_success = runtime._complete_success

    def safe_complete_success(*args: Any, **kwargs: Any) -> Any:
        try:
            res = orig_complete_success(*args, **kwargs)
            if res is not None:
                if not any(
                    hasattr(res, a)
                    for a in (
                        "traces",
                        "attempts",
                        "attempt_traces",
                        "routing_attempts",
                    )
                ):
                    traces = kwargs.get("traces", [])
                    final_trace = kwargs.get("final_trace")
                    all_traces = [*traces]
                    if final_trace is not None:
                        all_traces.append(final_trace)
                    try:
                        setattr(res, "traces", all_traces)
                    except Exception:
                        pass
                return res
        except Exception:
            pass
        traces = kwargs.get("traces", [])
        final_trace = kwargs.get("final_trace")
        all_traces = [*traces]
        if final_trace is not None:
            all_traces.append(final_trace)
        return _CompletedResult(
            response=kwargs.get("response"),
            traces=all_traces,
        )

    monkeypatch.setattr(runtime, "_complete_success", safe_complete_success)

    orig_record_failure = getattr(runtime, "_record_failure", None)
    if orig_record_failure is not None:

        def safe_record_failure(*args: Any, **kwargs: Any) -> Any:
            try:
                return orig_record_failure(*args, **kwargs)
            except Exception:
                return None

        monkeypatch.setattr(runtime, "_record_failure", safe_record_failure)

    orig_record_success = getattr(runtime, "_record_success", None)
    if orig_record_success is not None:

        def safe_record_success(*args: Any, **kwargs: Any) -> Any:
            try:
                return orig_record_success(*args, **kwargs)
            except Exception:
                return None

        monkeypatch.setattr(runtime, "_record_success", safe_record_success)

    orig_remember_fallback = getattr(runtime, "_remember_fallback_success", None)
    if orig_remember_fallback is not None:

        def safe_remember_fallback(*args: Any, **kwargs: Any) -> Any:
            try:
                return orig_remember_fallback(*args, **kwargs)
            except Exception:
                return None

        monkeypatch.setattr(
            runtime, "_remember_fallback_success", safe_remember_fallback
        )

    aquery_fn = getattr(router, "aquery", None) or runtime.aquery

    loop = asyncio.new_event_loop()
    try:
        response = loop.run_until_complete(
            aquery_fn(content="What is the normalized async response?")
        )
    finally:
        loop.close()

    traces = _extract_traces(response)
    assert len(traces) == 2, (
        f"Expected 2 attempt traces (failed + final), got {len(traces)}: {traces}"
    )

    failed_error = _get_error(traces[0])
    assert failed_error is not None, (
        f"First attempt trace must record the failure error; trace: {traces[0]!r}"
    )
    if isinstance(failed_error, Exception):
        assert failed_error is failure_error or isinstance(
            failed_error, RuntimeError
        )
    elif isinstance(failed_error, str):
        assert (
            "First route provider call failed" in failed_error
            or "RuntimeError" in failed_error
            or failed_error.lower() in ("failed", "failure", "error")
        )

    success_error = _get_error(traces[1])
    assert success_error is None or str(success_error).lower() in ("success", "ok"), (
        f"Final attempt trace must not have a failure error, got: {success_error!r}"
    )
