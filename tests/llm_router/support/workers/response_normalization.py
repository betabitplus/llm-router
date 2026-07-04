"""Project-specific helpers for response-normalization llm_router e2e tests.

Why:
    Keeps response-normalization e2e scenarios focused on public outcomes
    instead of repeating subprocess orchestration and JSON result parsing.

When to use:
    Use from llm_router response-normalization e2e tests that drive distinct
    provider families through local scripted servers.

How:
    Start a `ScriptedHTTPServer`, then call `run_response_normalization_worker(...)`
    with the case identifier and assert on the returned
    `ResponseNormalizationWorkerResult`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from tests.llm_router.support.workers._worker_process import run_worker_module
from tests.llm_router.support.workers.worker_patches import (
    patched_google_genai_sdk,
    patched_openai_sdk,
)


@dataclass(frozen=True, slots=True)
class ResponseNormalizationWorkerResult:
    """Structured result returned by the response-normalization worker."""

    ok: bool
    output_text: str
    provider: str
    model: str
    usage: dict[str, int] | None
    routing_trace: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    error_type: str | None
    error_message: str | None
    returncode: int
    stdout: str
    stderr: str


def run_response_normalization_worker(
    *,
    case: str,
    server_base_url: str,
) -> ResponseNormalizationWorkerResult:
    """Run one response-normalization scenario in an isolated subprocess."""
    completed, payload = run_worker_module(
        module="tests.llm_router.support.workers.response_normalization_worker",
        args=[
            "--case",
            case,
            "--server-base-url",
            server_base_url,
        ],
        missing_output_message=(
            "Response normalization worker did not produce any JSON output."
        ),
    )
    return ResponseNormalizationWorkerResult(
        ok=bool(payload["ok"]),
        output_text=str(payload.get("output_text", "")),
        provider=str(payload.get("provider", "")),
        model=str(payload.get("model", "")),
        usage=payload.get("usage"),
        routing_trace=list(payload.get("routing_trace", [])),
        tool_trace=list(payload.get("tool_trace", [])),
        tool_calls=list(payload.get("tool_calls", [])),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_response_normalization_dual_worker(
    *,
    openai_server_base_url: str,
    google_server_base_url: str,
) -> tuple[ResponseNormalizationWorkerResult, ResponseNormalizationWorkerResult]:
    """Run OpenAI-compatible + Google representative scenarios.

    For speed, this runs in-process with temporary SDK patching that is
    restored before returning.
    """

    import tests.llm_router.support.workers.response_normalization_dual_worker as worker
    from tests.llm_router.support.runtime import clear_test_caches

    previous_openrouter_key = os.environ.get("OPENROUTER_API_KEY_1")
    previous_google_key = os.environ.get("GOOGLE_API_KEY_1")
    os.environ.setdefault("OPENROUTER_API_KEY_1", "LOCAL_RETRY_KEY")
    os.environ.setdefault("GOOGLE_API_KEY_1", "LOCAL_RETRY_KEY")

    try:
        clear_test_caches()
        with (
            patched_openai_sdk(
                forced_base_url=f"{openai_server_base_url}/v1",
                disable_sdk_retries=True,
            ),
            patched_google_genai_sdk(server_base_url=google_server_base_url),
        ):
            openai_result = worker._run_case(case="openai")
            google_result = worker._run_case(case="google")

        payload = {
            "openai": openai_result,
            "google": google_result,
        }
        completed_returncode = 0
        completed_stdout = ""
        completed_stderr = ""
    except Exception as exc:
        payload = {
            "openai": {
                "ok": False,
                "output_text": "",
                "provider": "",
                "model": "",
                "usage": None,
                "routing_trace": [],
                "tool_trace": [],
                "tool_calls": [],
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            "google": {},
        }
        completed_returncode = 0
        completed_stdout = ""
        completed_stderr = ""
    finally:
        clear_test_caches()
        if previous_openrouter_key is None:
            os.environ.pop("OPENROUTER_API_KEY_1", None)
        else:
            os.environ["OPENROUTER_API_KEY_1"] = previous_openrouter_key
        if previous_google_key is None:
            os.environ.pop("GOOGLE_API_KEY_1", None)
        else:
            os.environ["GOOGLE_API_KEY_1"] = previous_google_key

    def parse_case(case_payload: dict[str, Any]) -> ResponseNormalizationWorkerResult:
        return ResponseNormalizationWorkerResult(
            ok=bool(case_payload.get("ok")),
            output_text=str(case_payload.get("output_text", "")),
            provider=str(case_payload.get("provider", "")),
            model=str(case_payload.get("model", "")),
            usage=case_payload.get("usage"),
            routing_trace=list(case_payload.get("routing_trace", [])),
            tool_trace=list(case_payload.get("tool_trace", [])),
            tool_calls=list(case_payload.get("tool_calls", [])),
            error_type=case_payload.get("error_type"),
            error_message=case_payload.get("error_message"),
            returncode=completed_returncode,
            stdout=completed_stdout,
            stderr=completed_stderr,
        )

    openai_payload = payload.get("openai") or {}
    google_payload = payload.get("google") or {}
    return parse_case(openai_payload), parse_case(google_payload)
