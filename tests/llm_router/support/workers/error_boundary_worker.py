"""Subprocess worker for public-error-boundary llm_router e2e tests.

Why:
    Keeps env shaping and external SDK patching out of the main pytest process
    so error-boundary behavior is tested through the public API.

When to use:
    Use only via
    `tests.llm_router.support.workers.error_boundary.run_error_boundary_worker(...)`.

How:
    Prepare one scenario, execute one public `LLMRouter(...).query(...)` call
    or constructor path, and print a JSON result.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Never

from tests.llm_router.support.workers.worker_patches import prepare_fault_case


def _clear_provider_keys(*, provider_prefix: str) -> None:
    """Remove numbered API key variables for one provider prefix."""
    for key in list(os.environ):
        if key.startswith(f"{provider_prefix}_API_KEY_"):
            os.environ.pop(key, None)


def _prepare_missing_api_key() -> None:
    """Ensure API key lookup cannot succeed through environment variables."""
    _clear_provider_keys(provider_prefix="OPENROUTER")


def _require_server_base_url(*, server_base_url: str | None) -> str:
    """Return a required server base URL or raise a stable worker error."""
    if server_base_url:
        return server_base_url
    msg = "provider_error requires --server-base-url"
    raise ValueError(msg)


def _raise_unknown_scenario(scenario: str) -> Never:
    """Raise the stable worker error for an unknown scenario."""
    raise ValueError(f"Unknown error-boundary worker scenario: {scenario}")


def _run_case(*, scenario: str, server_base_url: str | None) -> dict[str, Any]:
    try:
        if scenario == "missing_api_key":
            _prepare_missing_api_key()
            from llm_router import LLMRouter, Model, Provider, RouterProfile

            router = LLMRouter(
                RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
                temperature=0.0,
                seed=1,
            )
            router.query("Reply with one word.")
            return _success_payload()

        if scenario == "invalid_model":
            from llm_router import LLMRouter, Provider, RouterProfile

            LLMRouter(
                RouterProfile(
                    model="definitely-not-a-model",
                    provider=Provider.OPENROUTER,
                ),
                temperature=0.0,
                seed=1,
            )
            return _success_payload()

        if scenario == "provider_error":
            prepare_fault_case(
                case="openai",
                server_base_url=_require_server_base_url(
                    server_base_url=server_base_url
                ),
            )
            from llm_router import LLMRouter, Model, Provider, RouterProfile

            router = LLMRouter(
                RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
                temperature=0.0,
                seed=1,
            )
            router.query("Reply with one word.")
            return _success_payload()

        _raise_unknown_scenario(scenario)
    except Exception as exc:  # Defensive: keep worker output structured.
        return _error_payload(exc)


def _success_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "error_type": None,
        "error_message": None,
    }


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--server-base-url")
    args = parser.parse_args()

    try:
        result = _run_case(
            scenario=args.scenario,
            server_base_url=args.server_base_url,
        )
    except Exception as exc:  # Defensive: worker should always emit JSON.
        result = _error_payload(exc)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
