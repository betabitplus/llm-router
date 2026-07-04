"""Subprocess worker for contract-focused llm_router e2e tests.

Why:
    Keeps provider SDK patching out of the main pytest process so request
    precedence and schema-default behavior are exercised through the public API.

When to use:
Use only via `tests.llm_router.support.workers.contract.run_contract_worker(...)`
or `run_contract_worker_batch(...)`.

How:
    Patch the external SDK before importing `llm_router`, execute one public
    `LLMRouter(...).query(...)` call, and emit a JSON summary of the result.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, NoReturn

from pydantic import BaseModel

from tests.llm_router.support.workers._worker_process import ensure_worker_env
from tests.llm_router.support.workers.worker_patches import prepare_fault_case


class RouteDefaultEnvelope(BaseModel):
    """Structured output used for the route-default schema scenario."""

    status: str


class CallOverrideEnvelope(BaseModel):
    """Structured output used for the per-call schema-override scenario."""

    code: int


def _build_router(*, scenario: str) -> Any:
    from llm_router import LLMRouter, Model, Provider, RouterProfile

    if scenario in {
        "router_defaults",
        "call_overrides",
        "call_none_clears_defaults",
    }:
        return LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.7,
            seed=11,
        )

    if scenario in {
        "route_schema_default",
        "call_schema_override",
        "call_schema_none_clears_default",
    }:
        return LLMRouter(
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
                response_schema=RouteDefaultEnvelope,
            ),
            temperature=0.0,
            seed=1,
        )

    _raise_unknown_scenario(scenario)
    raise AssertionError("unreachable")
    return None


def _raise_unknown_scenario(scenario: str) -> NoReturn:
    """Raise the stable worker error for an unknown scenario."""
    msg = f"Unknown contract worker scenario: {scenario}"
    raise ValueError(msg)


def _run_case(*, scenario: str) -> dict[str, Any]:
    router = _build_router(scenario=scenario)

    try:
        if scenario == "router_defaults":
            response = router.query("Reply with precedence-ok only.")
        elif scenario == "call_overrides":
            response = router.query(
                "Reply with precedence-ok only.",
                temperature=0.0,
                seed=42,
            )
        elif scenario == "call_none_clears_defaults":
            response = router.query(
                "Reply with precedence-ok only.",
                temperature=None,
                seed=None,
            )
        elif scenario == "route_schema_default":
            response = router.query("Return JSON with only the status field.")
        elif scenario == "call_schema_override":
            response = router.query(
                "Return JSON with only the code field.",
                response_schema=CallOverrideEnvelope,
            )
        elif scenario == "call_schema_none_clears_default":
            response = router.query(
                "Reply with schema-cleared-ok only.",
                response_schema=None,
            )
        else:
            _raise_unknown_scenario(scenario)
    except Exception as exc:
        return _error_payload(exc)

    return {
        "ok": True,
        "output_text": response.output_text,
        "routing_trace": [attempt.model_dump() for attempt in response.routing_trace],
        "error_type": None,
        "error_message": None,
    }


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "output_text": "",
        "routing_trace": [],
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }


def _run_batch(*, scenarios: list[str]) -> dict[str, dict[str, Any]]:
    """Run multiple contract scenarios in one worker process."""
    return {scenario: _run_case(scenario=scenario) for scenario in scenarios}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", action="append", required=True)
    parser.add_argument("--server-base-url", required=True)
    args = parser.parse_args()

    try:
        ensure_worker_env()
        prepare_fault_case(case="openai", server_base_url=args.server_base_url)
        if len(args.scenario) == 1:
            result = _run_case(scenario=args.scenario[0])
        else:
            result = _run_batch(scenarios=list(args.scenario))
    except Exception as exc:  # Defensive: worker should always emit JSON.
        result = _error_payload(exc)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
