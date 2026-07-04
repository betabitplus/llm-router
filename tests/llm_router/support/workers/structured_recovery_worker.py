"""Subprocess worker for structured-recovery llm_router e2e tests.

Why:
    Keeps external SDK patching out of the main pytest process so local
    structured-output repair behavior can be tested through the public API.

When to use:
    Use only via
    `tests.llm_router.support.workers.structured_recovery.run_structured_recovery_worker(...)`.

How:
    Patch external SDK entry points before importing `llm_router`, then execute
    one public `LLMRouter(...).query(...)` call and print a JSON result.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from pydantic import BaseModel, Field

from tests.llm_router.support.workers._worker_process import ensure_worker_env
from tests.llm_router.support.workers.worker_patches import prepare_fault_case


class TicketSummary(BaseModel):
    """Structured output used by the structured-recovery scenarios."""

    incident_id: str
    severity: str = Field(min_length=4)
    tags: list[str] = Field(min_length=2, max_length=2)


def _build_router(*, case: str) -> Any:
    from llm_router import LLMRouter, Model, Provider, RouterProfile

    if case == "qwenchat":
        return LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
            seed=1,
        )

    if case == "gemini_webapi":
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
            temperature=0.0,
            seed=1,
        )

    msg = f"Unknown structured-recovery worker case: {case}"
    raise ValueError(msg)


def _build_prompt() -> str:
    """Build the deterministic structured-output prompt."""
    return (
        "Return incident JSON.\n\n"
        "Constraints:\n"
        "- incident_id must be INC-2048\n"
        "- severity must be SEV2\n"
        "- tags must be exactly 2 short strings\n"
    )


def _run_case(*, case: str) -> dict[str, Any]:
    router = _build_router(case=case)

    try:
        response = router.query(
            _build_prompt(),
            response_schema=TicketSummary,
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
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--server-base-url", required=True)
    args = parser.parse_args()

    _ = args.scenario

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
