"""Subprocess worker for response-normalization llm_router e2e tests.

Why:
    Keeps external SDK patching out of the main pytest process so public
    response parity is exercised through the library boundary.

When to use:
    Use only via
    `tests.llm_router.support.workers.response_normalization.run_response_normalization_worker(...)`.

How:
    Patch one provider family before importing `llm_router`, execute one public
    `LLMRouter(...).query(...)` call, and emit normalized response data.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from tests.llm_router.support.workers._worker_process import ensure_worker_env
from tests.llm_router.support.workers.worker_patches import prepare_fault_case


def _build_router(*, case: str) -> Any:
    from llm_router import LLMRouter, Model, Provider, RouterProfile

    if case == "openai":
        return LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
            seed=1,
        )

    if case == "google":
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.GOOGLE),
            temperature=0.0,
            seed=1,
        )

    msg = f"Unknown response-normalization worker case: {case}"
    raise ValueError(msg)


def _run_case(*, case: str) -> dict[str, Any]:
    router = _build_router(case=case)

    try:
        response = router.query("Reply with parity-ok only.")
    except Exception as exc:
        return {
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
        }

    return {
        "ok": True,
        "output_text": response.output_text,
        "provider": response.provider,
        "model": response.model,
        "usage": None if response.usage is None else response.usage.model_dump(),
        "routing_trace": [attempt.model_dump() for attempt in response.routing_trace],
        "tool_trace": [step.model_dump() for step in response.tool_trace],
        "tool_calls": [call.model_dump() for call in response.tool_calls],
        "error_type": None,
        "error_message": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--server-base-url", required=True)
    args = parser.parse_args()

    try:
        ensure_worker_env()
        prepare_fault_case(case=args.case, server_base_url=args.server_base_url)
        result = _run_case(case=args.case)
    except Exception as exc:  # Defensive: worker should always emit JSON.
        result = {
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
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
