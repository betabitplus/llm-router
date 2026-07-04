"""Project-specific helpers for tool-failure llm_router e2e tests.

Why:
    Keeps tool-failure e2e scenarios focused on public outcomes instead of
    repeating subprocess orchestration and provider-shaped payload builders.

When to use:
    Use from llm_router tool-failure e2e tests that drive real tool-capable
    client paths through a local scripted fault server.

How:
    Start a `ScriptedHTTPServer`, then call `run_tool_failure_worker(...)` with
    the case identifier and assert on the returned `ToolFailureWorkerResult`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from tests.llm_router.support.workers.worker_patches import (
    patched_google_genai_sdk,
    patched_openai_sdk,
)


@dataclass(frozen=True, slots=True)
class ToolFailureWorkerResult:
    """Structured result returned by the tool-failure subprocess worker."""

    ok: bool
    output_text: str
    error_type: str | None
    error_message: str | None
    returncode: int
    stdout: str
    stderr: str


def run_tool_failure_worker(
    *,
    case: str,
    server_base_url: str,
) -> ToolFailureWorkerResult:
    """Run one tool-failure scenario.

    For speed, tool-failure scenarios run in-process with temporary SDK patching
    that is restored before returning.
    """

    return run_tool_failure_inprocess(case=case, server_base_url=server_base_url)


def run_tool_failure_inprocess(
    *, case: str, server_base_url: str
) -> ToolFailureWorkerResult:
    """Run one tool-failure scenario in-process (no subprocess overhead)."""
    import tests.llm_router.support.workers.tool_failure_worker as worker
    from tests.llm_router.support.runtime import clear_test_caches

    required_env_keys: dict[str, str] = {}
    if case == "openai":
        required_env_keys["OPENROUTER_API_KEY_1"] = "LOCAL_RETRY_KEY"
    elif case == "google":
        required_env_keys["GOOGLE_API_KEY_1"] = "LOCAL_RETRY_KEY"
    else:
        msg = f"Unknown tool-failure worker case: {case}"
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
        }
    finally:
        clear_test_caches()
        for key, prev_value in previous_env.items():
            if prev_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev_value

    return ToolFailureWorkerResult(
        ok=bool(payload.get("ok")),
        output_text=str(payload.get("output_text", "")),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        returncode=0,
        stdout="",
        stderr="",
    )


def openai_tool_call_response(*, tool_name: str, args: dict[str, object]) -> bytes:
    """Return a minimal OpenAI-compatible tool-call response payload."""
    return json.dumps(
        {
            "id": "chatcmpl-local-tool",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_local_tool",
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(args),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 4,
                "total_tokens": 16,
            },
        }
    ).encode("utf-8")


def google_tool_call_response(*, tool_name: str, args: dict[str, object]) -> bytes:
    """Return a minimal Google GenerateContent tool-call response payload."""
    return json.dumps(
        {
            "candidates": [
                {
                    "index": 0,
                    "content": {
                        "role": "model",
                        "parts": [
                            {
                                "functionCall": {
                                    "name": tool_name,
                                    "args": args,
                                }
                            }
                        ],
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 4,
                "totalTokenCount": 14,
            },
            "modelVersion": "local-model",
        }
    ).encode("utf-8")
