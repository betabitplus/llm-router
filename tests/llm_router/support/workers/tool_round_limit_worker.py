"""Subprocess worker for tool-round-limit llm_router e2e tests.

Why:
    Keeps external SDK patching out of the main pytest process so the public
    tool-round contract is exercised through real provider-shaped responses.

When to use:
    Use only via
    `tests.llm_router.support.workers.tool_round_limit.run_tool_round_limit_worker(...)`.

How:
    Patch external SDK entry points before importing `llm_router`, then execute
    one public `LLMRouter(...).query(...)` call with a tool that keeps getting
    requested until `max_tool_rounds` is exhausted.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from tests.llm_router.support.workers._worker_process import ensure_worker_env
from tests.llm_router.support.workers.worker_patches import prepare_fault_case


def ping(*, value: int) -> dict[str, int]:
    """Return a deterministic tool result for repeated tool-call loops."""
    return {"echo": value}


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

    msg = f"Unknown tool-round-limit worker case: {case}"
    raise ValueError(msg)


def _run_case(*, case: str) -> dict[str, Any]:
    router = _build_router(case=case)

    try:
        response = router.query(
            "Keep using ping(value=7).",
            tools=[ping],
            tool_choice="required",
            max_tool_rounds=2,
        )
    except Exception as exc:
        return {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "tool_trace": [],
            "tool_calls": [],
        }

    return {
        "ok": True,
        "output_text": response.output_text,
        "error_type": None,
        "error_message": None,
        "tool_trace": [step.model_dump() for step in response.tool_trace],
        "tool_calls": [call.model_dump() for call in response.tool_calls],
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
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "tool_trace": [],
            "tool_calls": [],
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
