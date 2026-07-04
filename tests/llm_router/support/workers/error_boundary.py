"""Project-specific helpers for public-error-boundary llm_router e2e tests.

Why:
    Keeps error-boundary e2e scenarios focused on public outcomes instead of
    repeating subprocess orchestration in every file.

When to use:
    Use from llm_router error-boundary e2e tests that need isolated process
    setup before importing `llm_router`.

How:
    Call `run_error_boundary_worker(...)` with the scenario identifier and
    optional local server URL, then assert on the returned
    `ErrorBoundaryWorkerResult`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import NoReturn

from tests.llm_router.support.workers._worker_process import run_worker_module


@dataclass(frozen=True, slots=True)
class ErrorBoundaryWorkerResult:
    """Structured result returned by the public-error-boundary worker."""

    ok: bool
    error_type: str | None
    error_message: str | None
    returncode: int
    stdout: str
    stderr: str


def _raise_worker_value_error(message: str) -> NoReturn:
    raise ValueError(message)


_OPENROUTER_ENV_PREFIX = "OPENROUTER_API_KEY_"


def _clear_prefixed_env_vars(prefix: str) -> None:
    for key in [key for key in os.environ if key.startswith(prefix)]:
        os.environ.pop(key, None)


def _restore_prefixed_env_vars(prefix: str, previous_values: dict[str, str]) -> None:
    _clear_prefixed_env_vars(prefix)
    for key, value in previous_values.items():
        os.environ[key] = value


def _run_missing_api_key_scenario(*, openrouter_env_prefix: str) -> None:
    from llm_router import LLMRouter, Model, Provider, RouterProfile

    _clear_prefixed_env_vars(openrouter_env_prefix)
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
        seed=1,
    )
    router.query("Reply with one word.")


def _run_invalid_model_scenario() -> None:
    from llm_router import LLMRouter, Provider, RouterProfile

    LLMRouter(
        RouterProfile(
            model="definitely-not-a-model",
            provider=Provider.OPENROUTER,
        ),
        temperature=0.0,
        seed=1,
    )


def _run_provider_error_scenario(*, server_base_url: str) -> None:
    from dataclasses import replace

    from llm_router import (
        LLMRouter,
        Model,
        Provider,
        RouterProfile,
        get_config,
        install_config,
    )
    from tests.llm_router.support.runtime import clear_test_caches

    os.environ.setdefault("OPENROUTER_API_KEY_1", "LOCAL_RETRY_KEY")

    # Avoid global SDK patching here: force base URL through config so this
    # remains deterministic even if other background threads are still running
    # provider calls in the same xdist worker process.
    config = get_config()
    provider_base_urls = dict(config.catalog.provider_base_urls)
    provider_base_urls[Provider.OPENROUTER] = f"{server_base_url}/v1"
    install_config(
        replace(
            config,
            catalog=replace(
                config.catalog,
                provider_base_urls=provider_base_urls,
            ),
        )
    )

    clear_test_caches()
    router = LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=Provider.OPENROUTER,
        ),
        temperature=0.0,
        seed=1,
    )
    router.query("Reply with one word.")


def run_error_boundary_worker(
    *,
    scenario: str,
    server_base_url: str | None = None,
) -> ErrorBoundaryWorkerResult:
    """Run one public-error-boundary scenario in an isolated subprocess."""
    args = ["--scenario", scenario]
    if server_base_url is not None:
        args.extend(["--server-base-url", server_base_url])

    completed, payload = run_worker_module(
        module="tests.llm_router.support.workers.error_boundary_worker",
        args=args,
        missing_output_message=(
            "Error-boundary worker did not produce any JSON output."
        ),
    )
    return ErrorBoundaryWorkerResult(
        ok=bool(payload["ok"]),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_error_boundary_inprocess(
    *,
    scenario: str,
    server_base_url: str | None = None,
) -> ErrorBoundaryWorkerResult:
    """Run one public-error-boundary scenario in-process (no subprocess overhead)."""
    from llm_router import get_config, install_config
    from tests.llm_router.support.runtime import clear_test_caches

    previous_openrouter_keys = {
        key: value
        for key, value in os.environ.items()
        if key.startswith(_OPENROUTER_ENV_PREFIX)
    }

    original_config = get_config()

    try:
        clear_test_caches()

        if scenario == "missing_api_key":
            _run_missing_api_key_scenario(openrouter_env_prefix=_OPENROUTER_ENV_PREFIX)
        elif scenario == "invalid_model":
            _run_invalid_model_scenario()
        elif scenario == "provider_error":
            if not server_base_url:
                _raise_worker_value_error("provider_error requires --server-base-url")
            _run_provider_error_scenario(server_base_url=server_base_url)
        else:
            _raise_worker_value_error(
                f"Unknown error-boundary worker scenario: {scenario}"
            )

        payload = {"ok": True, "error_type": None, "error_message": None}

    except Exception as exc:  # Defensive: keep payload structured.
        payload = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    finally:
        clear_test_caches()
        install_config(original_config)
        _restore_prefixed_env_vars(_OPENROUTER_ENV_PREFIX, previous_openrouter_keys)

    return ErrorBoundaryWorkerResult(
        ok=bool(payload["ok"]),
        error_type=payload.get("error_type"),
        error_message=payload.get("error_message"),
        returncode=0,
        stdout="",
        stderr="",
    )
