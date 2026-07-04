"""Subprocess worker for attempt-timeout llm_router e2e tests.

Why:
    Keeps external SDK patching out of the main pytest process so attempt
    timeout behavior can be tested through the public API without mutating
    library state in-process.

When to use:
    Use only via `tests.llm_router.support.workers.timeout.run_timeout_worker(...)`.

How:
    Patch the OpenAI SDK before importing `llm_router`, then execute one public
    `LLMRouter(...).query(...)` call and print a JSON result.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from tests.llm_router.support.workers._worker_process import ensure_worker_env
from tests.llm_router.support.workers.worker_patches import prepare_fault_case


def _build_router(*, scenario: str) -> Any:
    from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile

    # Use two different OpenAI-compatible providers so each attempt gets a
    # distinct cached client instance (provider+key_id). This avoids CI-only
    # flakiness where the fallback attempt can collide with the still-in-flight
    # timed-out request when both attempts share the same client.
    delayed = RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER)
    # Groq does not expose Deepseek V3 in the built-in model registry, so use
    # a Groq-native model for the fallback attempt.
    fast = RouterProfile(model=Model.LLAMA_SCOUT, provider=Provider.GROQ)

    fast_limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=0,
    )

    if scenario == "fallback_after_timeout":
        return LLMRouter(
            [delayed, fast],
            limits_by_provider={
                # Disable limiter waits entirely: this scenario is about attempt
                # timeout-driven fallback, not rate limiting.
                Provider.OPENROUTER: fast_limits,
                Provider.GROQ: fast_limits,
            },
            temperature=0.0,
            seed=1,
            # The scripted server delays the first attempt by 2.0s.
            # Keep the timeout below that while leaving CI headroom.
            attempt_timeout_seconds=1.0,
        )

    if scenario == "terminal_timeout":
        return LLMRouter(
            delayed,
            limits_by_provider={
                Provider.OPENROUTER: fast_limits,
            },
            temperature=0.0,
            seed=1,
            # The scripted server delays the response by 2.0s in this scenario.
            # Keep the timeout below that so the terminal timeout is deterministic.
            attempt_timeout_seconds=1.0,
        )

    msg = f"Unknown timeout worker scenario: {scenario}"
    raise ValueError(msg)


def _run_scenario(*, scenario: str) -> dict[str, Any]:
    router = _build_router(scenario=scenario)
    prompt = "Reply with the timeout marker only."

    try:
        response = router.query(prompt)
    except Exception as exc:
        return {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "routing_trace": [],
        }

    return {
        "ok": True,
        "output_text": response.output_text,
        "error_type": None,
        "error_message": None,
        "routing_trace": [attempt.model_dump() for attempt in response.routing_trace],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--server-base-url", required=True)
    args = parser.parse_args()

    try:
        # The openai-compatible adapter reads provider keys from env vars.
        # `prepare_fault_case(case='openai', ...)` sets OPENROUTER_API_KEY_1.
        # We add a dummy GROQ key so the fallback provider can resolve a key.
        os.environ.setdefault("GROQ_API_KEY_1", "LOCAL_RETRY_KEY")
        ensure_worker_env()
        prepare_fault_case(case="openai", server_base_url=args.server_base_url)
        result = _run_scenario(scenario=args.scenario)
    except Exception as exc:  # Defensive: worker should always emit JSON.
        result = {
            "ok": False,
            "output_text": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "routing_trace": [],
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
