"""Project-specific helpers for contract-focused llm_router e2e tests.

Why:
    Keeps contract e2e scenarios focused on public outcomes instead of
    repeating subprocess orchestration and JSON worker parsing in every file.

When to use:
    Use from llm_router contract e2e tests that need isolated process setup
    before importing `llm_router`.

How:
    Call `run_contract_worker(...)` with one scenario identifier and the local
    scripted server URL, then assert on the returned `ContractWorkerResult`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from tests.llm_router.support.workers.worker_patches import patched_openai_sdk


@dataclass(frozen=True, slots=True)
class ContractWorkerResult:
    """Structured result returned by the contract worker."""

    ok: bool
    output_text: str
    routing_trace: list[dict[str, Any]]
    error_type: str | None
    error_message: str | None
    returncode: int
    stdout: str
    stderr: str


def run_contract_worker(
    *,
    scenario: str,
    server_base_url: str,
) -> ContractWorkerResult:
    """Run one contract scenario.

    For speed, contract scenarios run in-process with temporary SDK patching
    that is restored before returning.
    """
    return run_contract_worker_inprocess(
        scenario=scenario, server_base_url=server_base_url
    )


def run_contract_worker_batch(
    *,
    scenarios: list[str],
    server_base_url: str,
) -> dict[str, ContractWorkerResult]:
    """Run multiple contract scenarios.

    For speed, this runs in-process with temporary SDK patching that is
    restored before returning.
    """
    return run_contract_worker_batch_inprocess(
        scenarios=scenarios, server_base_url=server_base_url
    )


def run_contract_worker_inprocess(
    *,
    scenario: str,
    server_base_url: str,
) -> ContractWorkerResult:
    """Run one contract scenario in-process (no subprocess overhead)."""
    results = run_contract_worker_batch_inprocess(
        scenarios=[scenario],
        server_base_url=server_base_url,
    )
    return results[scenario]


def run_contract_worker_batch_inprocess(
    *,
    scenarios: list[str],
    server_base_url: str,
) -> dict[str, ContractWorkerResult]:
    """Run multiple contract scenarios in-process (no subprocess overhead)."""
    import tests.llm_router.support.workers.contract_worker as worker
    from tests.llm_router.support.runtime import clear_test_caches

    previous_openrouter_key = os.environ.get("OPENROUTER_API_KEY_1")
    os.environ.setdefault("OPENROUTER_API_KEY_1", "LOCAL_RETRY_KEY")

    try:
        clear_test_caches()
        with patched_openai_sdk(
            forced_base_url=f"{server_base_url}/v1",
            disable_sdk_retries=True,
        ):
            payload = worker._run_batch(scenarios=scenarios)
    except Exception as exc:
        payload = {scenario: worker._error_payload(exc) for scenario in scenarios}
    finally:
        clear_test_caches()
        if previous_openrouter_key is None:
            os.environ.pop("OPENROUTER_API_KEY_1", None)
        else:
            os.environ["OPENROUTER_API_KEY_1"] = previous_openrouter_key

    return {
        scenario: ContractWorkerResult(
            ok=bool(result_payload.get("ok")),
            output_text=str(result_payload.get("output_text", "")),
            routing_trace=list(result_payload.get("routing_trace", [])),
            error_type=result_payload.get("error_type"),
            error_message=result_payload.get("error_message"),
            returncode=0,
            stdout="",
            stderr="",
        )
        for scenario, result_payload in payload.items()
    }
