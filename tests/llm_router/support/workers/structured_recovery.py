"""Project-specific helpers for structured-recovery llm_router e2e tests.

Why:
    Keeps structured-recovery e2e scenarios focused on public outcomes instead
    of repeating subprocess orchestration and JSON result parsing.

When to use:
    Use from llm_router structured-recovery e2e tests that drive real provider
    paths through a local scripted fault server.

How:
    Start a `ScriptedHTTPServer`, then call `run_structured_recovery_worker(...)`
    with the case and scenario identifier and assert on the returned
    `StructuredRecoveryWorkerResult`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import NoReturn

from tests.llm_router.support.workers.worker_patches import (
    install_worker_provider_base_url,
    patched_gemini_webapi_sdk,
)


@dataclass(frozen=True, slots=True)
class StructuredRecoveryWorkerResult:
    """Structured result returned by the structured-recovery worker."""

    ok: bool
    output_text: str
    error_type: str | None
    error_message: str | None
    returncode: int
    stdout: str
    stderr: str


def _raise_unknown_structured_recovery_case(case: str) -> NoReturn:
    raise ValueError(f"Unknown structured-recovery worker case: {case}")


def run_structured_recovery_worker(
    *,
    case: str,
    scenario: str,
    server_base_url: str,
) -> StructuredRecoveryWorkerResult:
    """Run one structured-recovery scenario.

    For speed, structured-recovery cases run in-process (no subprocess overhead)
    with temporary dependency patching that is restored before returning.
    """

    _ = scenario

    return run_structured_recovery_inprocess(
        case=case,
        server_base_url=server_base_url,
    )


def run_structured_recovery_inprocess(
    *,
    case: str,
    server_base_url: str,
) -> StructuredRecoveryWorkerResult:
    """Run one structured-recovery scenario in-process (no subprocess overhead)."""
    import tests.llm_router.support.workers.structured_recovery_worker as worker
    from llm_router import get_config, install_config
    from tests.llm_router.support.runtime import clear_test_caches

    original_config = get_config()
    previous_qwen_key = os.environ.get("QWENCHAT_API_KEY_1")
    if case == "qwenchat":
        os.environ.setdefault("QWENCHAT_API_KEY_1", "LOCAL_RETRY_KEY")

    try:
        clear_test_caches()
        if case == "qwenchat":
            install_worker_provider_base_url(
                provider="qwenchat",
                base_url=f"{server_base_url}/api",
            )
            payload = worker._run_case(case=case)
        elif case == "gemini_webapi":
            with patched_gemini_webapi_sdk(server_base_url=server_base_url):
                payload = worker._run_case(case=case)
        else:
            _raise_unknown_structured_recovery_case(case)
    except Exception as exc:
        payload = {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    finally:
        clear_test_caches()
        install_config(original_config)
        if case == "qwenchat":
            if previous_qwen_key is None:
                os.environ.pop("QWENCHAT_API_KEY_1", None)
            else:
                os.environ["QWENCHAT_API_KEY_1"] = previous_qwen_key

    return StructuredRecoveryWorkerResult(
        ok=bool(payload.get("ok")),
        output_text=str(payload.get("output_text", "")),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        returncode=0,
        stdout="",
        stderr="",
    )
