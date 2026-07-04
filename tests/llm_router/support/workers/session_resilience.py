"""Project-specific helpers for session-resilience llm_router e2e tests.

Why:
    Keeps session-resilience e2e scenarios focused on public outcomes instead
    of repeating subprocess orchestration and JSON result parsing.

When to use:
    Use from llm_router session-resilience e2e tests that drive real SDK
    traffic through a local scripted server.

How:
    Start a `ScriptedHTTPServer`, then call `run_session_resilience_worker(...)`
    with the scenario identifier and assert on the returned
    `SessionResilienceWorkerResult`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from tests.llm_router.support.workers._worker_process import run_worker_module
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk


@dataclass(frozen=True, slots=True)
class SessionResilienceWorkerResult:
    """Structured result returned by the session-resilience worker."""

    ok: bool
    output_text: str
    error_type: str | None
    error_message: str | None
    saved_history_length: int
    first_assistant_meta: dict[str, Any]
    second_assistant_meta: dict[str, Any]
    returncode: int
    stdout: str
    stderr: str


def run_session_resilience_worker(
    *,
    scenario: str,
    server_base_url: str,
) -> SessionResilienceWorkerResult:
    """Run one session-resilience scenario in an isolated subprocess."""
    completed, payload = run_worker_module(
        module="tests.llm_router.support.workers.session_resilience_worker",
        args=[
            "--scenario",
            scenario,
            "--server-base-url",
            server_base_url,
        ],
        missing_output_message=(
            "Session resilience worker did not produce any JSON output."
        ),
    )
    return SessionResilienceWorkerResult(
        ok=bool(payload["ok"]),
        output_text=str(payload.get("output_text", "")),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        saved_history_length=int(payload.get("saved_history_length", 0)),
        first_assistant_meta=dict(payload.get("first_assistant_meta", {})),
        second_assistant_meta=dict(payload.get("second_assistant_meta", {})),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_session_resilience_inprocess(
    *,
    scenario: str,
    server_base_url: str,
) -> SessionResilienceWorkerResult:
    """Run one session-resilience scenario in-process (no subprocess overhead)."""
    from dataclasses import replace

    import tests.llm_router.support.workers.session_resilience_worker as worker
    from llm_router import Provider, get_config, install_config
    from tests.llm_router.support.runtime import clear_test_caches

    previous_openrouter_key = os.environ.get("OPENROUTER_API_KEY_1")
    previous_groq_key = os.environ.get("GROQ_API_KEY_1")
    os.environ.setdefault("OPENROUTER_API_KEY_1", "LOCAL_RETRY_KEY")
    os.environ.setdefault("GROQ_API_KEY_1", "LOCAL_RETRY_KEY")

    base_config = get_config()
    provider_base_urls = dict(base_config.catalog.provider_base_urls)
    provider_base_urls[Provider.OPENROUTER] = f"{server_base_url}/openrouter/v1"
    provider_base_urls[Provider.GROQ] = f"{server_base_url}/groq/v1"
    catalog = replace(base_config.catalog, provider_base_urls=provider_base_urls)

    try:
        clear_test_caches()
        install_config(replace(base_config, catalog=catalog))
        with patched_openai_sdk(
            forced_base_url=None,
            disable_sdk_retries=True,
        ):
            payload = worker._run_scenario(scenario=scenario)
    except Exception as exc:
        payload = {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "saved_history_length": 0,
            "first_assistant_meta": {},
            "second_assistant_meta": {},
        }
    finally:
        clear_test_caches()
        install_config(base_config)
        if previous_openrouter_key is None:
            os.environ.pop("OPENROUTER_API_KEY_1", None)
        else:
            os.environ["OPENROUTER_API_KEY_1"] = previous_openrouter_key
        if previous_groq_key is None:
            os.environ.pop("GROQ_API_KEY_1", None)
        else:
            os.environ["GROQ_API_KEY_1"] = previous_groq_key

    return SessionResilienceWorkerResult(
        ok=bool(payload.get("ok")),
        output_text=str(payload.get("output_text", "")),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        saved_history_length=int(payload.get("saved_history_length", 0)),
        first_assistant_meta=dict(payload.get("first_assistant_meta", {})),
        second_assistant_meta=dict(payload.get("second_assistant_meta", {})),
        returncode=0,
        stdout="",
        stderr="",
    )
