"""Project-specific helpers for attempt-timeout llm_router e2e tests.

Why:
    Keeps attempt-timeout e2e scenarios focused on public outcomes instead of
    repeating subprocess orchestration and JSON result parsing.

When to use:
    Use from llm_router timeout e2e tests that drive real SDK traffic through a
    local scripted fault server.

How:
    Start a `ScriptedHTTPServer`, then call `run_timeout_worker(...)` with the
    scenario identifier and assert on the returned `TimeoutWorkerResult`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from tests.llm_router.support.workers._worker_process import run_worker_module
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk


@dataclass(frozen=True, slots=True)
class TimeoutWorkerResult:
    """Structured result returned by the timeout subprocess worker."""

    ok: bool
    output_text: str
    error_type: str | None
    error_message: str | None
    routing_trace: list[dict[str, Any]]
    returncode: int
    stdout: str
    stderr: str


def run_timeout_worker(
    *,
    scenario: str,
    server_base_url: str,
) -> TimeoutWorkerResult:
    """Run one attempt-timeout scenario in an isolated subprocess."""
    completed, payload = run_worker_module(
        module="tests.llm_router.support.workers.timeout_worker",
        args=[
            "--scenario",
            scenario,
            "--server-base-url",
            server_base_url,
        ],
        missing_output_message="Timeout worker did not produce any JSON output.",
    )
    return TimeoutWorkerResult(
        ok=bool(payload["ok"]),
        output_text=str(payload.get("output_text", "")),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        routing_trace=list(payload.get("routing_trace", [])),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_timeout_inprocess(
    *,
    scenario: str,
    server_base_url: str,
) -> TimeoutWorkerResult:
    """Run one attempt-timeout scenario in-process (no subprocess overhead)."""
    import tests.llm_router.support.workers.timeout_worker as worker
    from tests.llm_router.support.runtime import clear_test_caches

    previous_openrouter_key = os.environ.get("OPENROUTER_API_KEY_1")
    previous_groq_key = os.environ.get("GROQ_API_KEY_1")
    os.environ.setdefault("OPENROUTER_API_KEY_1", "LOCAL_RETRY_KEY")
    os.environ.setdefault("GROQ_API_KEY_1", "LOCAL_RETRY_KEY")

    try:
        # Mirror subprocess isolation: clear singleton adapters so cached
        # OpenAI clients cannot reuse a stale base URL from prior tests.
        clear_test_caches()
        with patched_openai_sdk(
            forced_base_url=f"{server_base_url}/v1",
            disable_sdk_retries=True,
        ):
            payload = worker._run_scenario(scenario=scenario)
    except Exception as exc:
        payload = {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "routing_trace": [],
        }
    finally:
        clear_test_caches()
        if previous_openrouter_key is None:
            os.environ.pop("OPENROUTER_API_KEY_1", None)
        else:
            os.environ["OPENROUTER_API_KEY_1"] = previous_openrouter_key
        if previous_groq_key is None:
            os.environ.pop("GROQ_API_KEY_1", None)
        else:
            os.environ["GROQ_API_KEY_1"] = previous_groq_key

    return TimeoutWorkerResult(
        ok=bool(payload.get("ok")),
        output_text=str(payload.get("output_text", "")),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        routing_trace=list(payload.get("routing_trace", [])),
        returncode=0,
        stdout="",
        stderr="",
    )
