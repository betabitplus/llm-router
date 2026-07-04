"""Project-specific helpers for tool-round-limit llm_router e2e tests.

Why:
    Keeps tool-round-limit e2e scenarios focused on public outcomes instead of
    repeating subprocess orchestration and JSON result parsing.

When to use:
    Use from llm_router tool-round-limit e2e tests that drive real tool-capable
    paths through a local scripted server.

How:
    Start a `ScriptedHTTPServer`, then call `run_tool_round_limit_worker(...)`
    with the case identifier and assert on the returned
    `ToolRoundLimitWorkerResult`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from tests.llm_router.support.workers.worker_patches import (
    patched_google_genai_sdk,
    patched_openai_sdk,
)


@dataclass(frozen=True, slots=True)
class ToolRoundLimitWorkerResult:
    """Structured result returned by the tool-round-limit worker."""

    ok: bool
    output_text: str
    error_type: str | None
    error_message: str | None
    tool_trace: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    returncode: int
    stdout: str
    stderr: str


def run_tool_round_limit_worker(
    *,
    case: str,
    server_base_url: str,
) -> ToolRoundLimitWorkerResult:
    """Run one tool-round-limit scenario.

    For speed, tool-round-limit scenarios run in-process with temporary SDK
    patching that is restored before returning.
    """

    return run_tool_round_limit_inprocess(case=case, server_base_url=server_base_url)


def run_tool_round_limit_inprocess(
    *,
    case: str,
    server_base_url: str,
) -> ToolRoundLimitWorkerResult:
    """Run one tool-round-limit scenario in-process (no subprocess overhead)."""
    import tests.llm_router.support.workers.tool_round_limit_worker as worker
    from tests.llm_router.support.runtime import clear_test_caches

    required_env_keys: dict[str, str] = {}
    if case == "openai":
        required_env_keys["OPENROUTER_API_KEY_1"] = "LOCAL_RETRY_KEY"
    elif case == "google":
        required_env_keys["GOOGLE_API_KEY_1"] = "LOCAL_RETRY_KEY"
    else:
        msg = f"Unknown tool-round-limit worker case: {case}"
        raise ValueError(msg)

    previous_env: dict[str, str | None] = {
        key: os.environ.get(key) for key in required_env_keys
    }
    for key, value in required_env_keys.items():
        os.environ.setdefault(key, value)

    try:
        clear_test_caches()
        if case == "openai":
            with patched_openai_sdk(
                forced_base_url=f"{server_base_url}/v1",
                disable_sdk_retries=True,
            ):
                payload = worker._run_case(case=case)
        elif case == "google":
            with patched_google_genai_sdk(server_base_url=server_base_url):
                payload = worker._run_case(case=case)
        else:  # pragma: no cover
            payload = worker._run_case(case=case)
    except Exception as exc:
        payload = {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "tool_trace": [],
            "tool_calls": [],
        }
    finally:
        clear_test_caches()
        for key, prev_value in previous_env.items():
            if prev_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev_value

    return ToolRoundLimitWorkerResult(
        ok=bool(payload.get("ok")),
        output_text=str(payload.get("output_text", "")),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        tool_trace=list(payload.get("tool_trace", [])),
        tool_calls=list(payload.get("tool_calls", [])),
        returncode=0,
        stdout="",
        stderr="",
    )
