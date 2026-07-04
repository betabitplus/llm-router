"""Subprocess worker for tool-failure llm_router e2e tests.

Why:
    Keeps external SDK patching out of the main pytest process so tool-failure
    behavior can be tested through the public API with real tool-capable client
    paths.

When to use:
    Use only via
    `tests.llm_router.support.workers.tool_failure.run_tool_failure_worker(...)`.

How:
    Patch external SDK entry points before importing `llm_router`, then execute
    one public `LLMRouter(...).query(...)` call with a failing tool and print a
    JSON result.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from tests.llm_router.support.workers._worker_process import ensure_worker_env
from tests.llm_router.support.workers.worker_patches import prepare_fault_case


def explode(*, value: int) -> dict[str, int]:
    """Raise a deterministic tool failure for e2e testing."""
    msg = f"tool exploded with value={value}"
    raise RuntimeError(msg)


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

    msg = f"Unknown tool-failure worker case: {case}"
    raise ValueError(msg)


def _build_query_kwargs(*, case: str) -> dict[str, Any]:
    tool_choice: str | dict[str, Any]
    if case == "openai":
        tool_choice = {"type": "function", "function": {"name": "explode"}}
    else:
        tool_choice = {"type": "function", "function": {"name": "explode"}}

    return {
        "tools": [explode],
        "tool_choice": tool_choice,
        "max_tool_rounds": 2,
    }


def _run_case(*, case: str) -> dict[str, Any]:
    router = _build_router(case=case)

    try:
        response = router.query(
            "Use the explode tool with value=7.",
            **_build_query_kwargs(case=case),
        )
    except Exception as exc:
        return {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    return {
        "ok": True,
        "output_text": response.output_text,
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
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
