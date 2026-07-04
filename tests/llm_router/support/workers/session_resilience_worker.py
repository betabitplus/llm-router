"""Subprocess worker for session-resilience llm_router e2e tests.

Why:
    Keeps external SDK patching out of the main pytest process so session
    persistence after resilience behavior is tested through the public API.

When to use:
    Use only via
    `tests.llm_router.support.workers.session_resilience.run_session_resilience_worker(...)`.

How:
    Patch external SDK entry points before importing `llm_router`, then execute
    a save/load session flow where the first assistant reply succeeds only after
    timeout fallback.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from tests.llm_router.support.workers._worker_process import ensure_worker_env
from tests.llm_router.support.workers.worker_patches import prepare_fault_case


def _build_router(*, session: Any) -> Any:
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
    return LLMRouter(
        [delayed, fast],
        session=session,
        limits_by_provider={
            # Disable limiter waits entirely: this scenario is about persistence
            # of timeout-fallback metadata, not rate limiting.
            Provider.OPENROUTER: fast_limits,
            Provider.GROQ: fast_limits,
        },
        temperature=0.0,
        seed=1,
        # The scripted server delays the OpenRouter attempt.
        # Keep the timeout below that while leaving CI headroom so the request
        # reliably reaches the local server before asyncio.wait_for expires.
        attempt_timeout_seconds=1.0,
    )


def _run_scenario(*, scenario: str) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        from llm_router import Session

        if scenario != "resume_after_timeout_fallback":
            msg = f"Unknown session-resilience worker scenario: {scenario}"
            raise ValueError(msg)

        with TemporaryDirectory(prefix="llm_router_session_resilience_") as tmp_dir:
            session_path = Path(tmp_dir) / "session.json"
            session = Session(
                system="Follow instructions exactly. Reply with only digits."
            )
            router = _build_router(session=session)

            first = await router.aquery("Remember secret code 81723. Reply only 81723.")
            session.save(session_path)

            loaded = Session.load(session_path)
            resumed_router = _build_router(session=loaded)
            second = await resumed_router.aquery(
                "What is the secret code? Reply only digits, no words."
            )
            loaded.save(session_path)

            reloaded = Session.load(session_path)
            first_assistant = reloaded.history[1]
            second_assistant = reloaded.history[3]

        return {
            "ok": True,
            "output_text": second.output_text,
            "error_type": None,
            "error_message": None,
            "saved_history_length": len(reloaded.history),
            "first_assistant_meta": first_assistant.meta,
            "second_assistant_meta": second_assistant.meta,
            "first_output_text": first.output_text,
        }

    return asyncio.run(_run())


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
            "saved_history_length": 0,
            "first_assistant_meta": {},
            "second_assistant_meta": {},
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
