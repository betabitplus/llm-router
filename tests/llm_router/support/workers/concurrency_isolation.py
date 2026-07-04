"""Project-specific helpers for concurrency-isolation llm_router e2e tests.

Why:
    Keeps concurrency-isolation e2e scenarios focused on public outcomes
    instead of repeating subprocess orchestration and JSON result parsing.

When to use:
    Use from llm_router concurrency-isolation e2e tests that exercise shared
    async client state inside one process.

How:
    Call `run_concurrency_isolation_worker()` and assert on the returned
    `ConcurrencyIsolationWorkerResult`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tests.llm_router.support.workers._worker_process import run_worker_module
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk


@dataclass(frozen=True, slots=True)
class ConcurrencyIsolationWorkerResult:
    """Structured result returned by the concurrency-isolation worker."""

    ok: bool
    alpha_text: str
    beta_text: str
    alpha_history_length: int
    beta_history_length: int
    alpha_user_parts: list[str]
    beta_user_parts: list[str]
    alpha_routing_trace: list[dict[str, Any]]
    beta_routing_trace: list[dict[str, Any]]
    request_count: int
    error_type: str | None
    error_message: str | None
    returncode: int
    stdout: str
    stderr: str


def run_concurrency_isolation_worker() -> ConcurrencyIsolationWorkerResult:
    """Run the concurrency-isolation scenario in an isolated subprocess."""
    completed, payload = run_worker_module(
        module="tests.llm_router.support.workers.concurrency_isolation_worker",
        args=[],
        missing_output_message=(
            "Concurrency isolation worker did not produce any JSON output."
        ),
    )
    return ConcurrencyIsolationWorkerResult(
        ok=bool(payload["ok"]),
        alpha_text=str(payload.get("alpha_text", "")),
        beta_text=str(payload.get("beta_text", "")),
        alpha_history_length=int(payload.get("alpha_history_length", 0)),
        beta_history_length=int(payload.get("beta_history_length", 0)),
        alpha_user_parts=list(payload.get("alpha_user_parts", [])),
        beta_user_parts=list(payload.get("beta_user_parts", [])),
        alpha_routing_trace=list(payload.get("alpha_routing_trace", [])),
        beta_routing_trace=list(payload.get("beta_routing_trace", [])),
        request_count=int(payload.get("request_count", 0)),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_concurrency_isolation_inprocess() -> ConcurrencyIsolationWorkerResult:
    """Run concurrency-isolation scenario in-process (no subprocess overhead)."""
    import asyncio

    import tests.llm_router.support.workers.concurrency_isolation_worker as worker
    from tests.llm_router.support.runtime import clear_test_caches

    try:
        clear_test_caches()
        with worker.BodyAwareServer(port=18917) as server:
            with patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ):
                payload = asyncio.run(worker._run_scenario())
            payload["request_count"] = server.request_count
            payload.setdefault("error_type", None)
            payload.setdefault("error_message", None)
    except Exception as exc:
        payload = {
            "ok": False,
            "alpha_text": "",
            "beta_text": "",
            "alpha_history_length": 0,
            "beta_history_length": 0,
            "alpha_user_parts": [],
            "beta_user_parts": [],
            "alpha_routing_trace": [],
            "beta_routing_trace": [],
            "request_count": 0,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    finally:
        clear_test_caches()

    return ConcurrencyIsolationWorkerResult(
        ok=bool(payload.get("ok")),
        alpha_text=str(payload.get("alpha_text", "")),
        beta_text=str(payload.get("beta_text", "")),
        alpha_history_length=int(payload.get("alpha_history_length", 0)),
        beta_history_length=int(payload.get("beta_history_length", 0)),
        alpha_user_parts=list(payload.get("alpha_user_parts", [])),
        beta_user_parts=list(payload.get("beta_user_parts", [])),
        alpha_routing_trace=list(payload.get("alpha_routing_trace", [])),
        beta_routing_trace=list(payload.get("beta_routing_trace", [])),
        request_count=int(payload.get("request_count", 0)),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        returncode=0,
        stdout="",
        stderr="",
    )
