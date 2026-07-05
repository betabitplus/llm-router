# %%
"""LLM Router e2e: Gemini WebAPI async text completion.

Why:
    Verifies that the browser-backed Gemini route supports the public async
    text path.

Covers:
    Area: Gemini WebAPI provider
    Behavior: async execution, text completion
    Interface: `LLMRouter(RouterProfile(...))`, `aquery(...)`

Checks:
    If the async public call succeeds, then the response object is populated.
    If the smoke prompt is honored, then the normalized reply is `pong`.

Notes:
    Live manual runs require local browser cookies for Gemini WebAPI access.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_gemini_webapi_async_text_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_async_text_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode, run_async

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.media.gemini_webapi import can_run_demo, require_runtime

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_async,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# The prompt is intentionally tiny so a failure is easy to attribute to the
# async browser-backed path rather than task complexity.


# =============================================================================
# Helpers
# =============================================================================


def normalize_reply(text: str) -> str:
    """Normalize short text replies for stable assertions."""
    return text.strip().rstrip(".").lower()


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the async smoke-test prompt."""
    return "Reply with only: pong"


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
        temperature=0.0,
        seed=42,
    )


async def run_pipeline() -> LLMRouterResponse:
    """Run the Gemini WebAPI async pipeline."""
    # Keep the public async flow explicit and minimal.
    router = build_router()
    return await router.aquery([_SYSTEM_PROMPT, build_prompt()])


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the async text response."""
    # First prove we really got a populated public response object back.
    assert response.data is not None
    # Then check the stable one-word reply this smoke scenario is built around.
    assert normalize_reply(response.output_text) == "pong"


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    require_runtime()
    # First run the exact public async call the scenario documents.
    response = await run_pipeline()
    # Then validate the tiny but important success contract.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the demo flow for manual execution."""
    can_run, reason = can_run_demo()
    if not can_run:
        console.print(f"[warning]{reason}[/]")
        raise SystemExit(0)

    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask the browser-backed Gemini path for a tiny async "
        "response so we can verify the public async entry point works.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same browser-backed async flow as the test.
    response = await run_pipeline()
    assert_pipeline_response(response)

    console.demo_step(
        "What Happened",
        "The async Gemini call returned the expected short answer.",
        details=[
            f"Raw reply: {response.output_text}",
            f"Normalized reply: {normalize_reply(response.output_text)}",
            f"Has response payload: {response.data is not None}",
            f"Usage: {response.usage}",
        ],
    )
    console.demo_outcome(
        "This passed because the public async path completed "
        "successfully and produced the stable reply this smoke "
        "scenario expects."
    )


if __name__ == "__main__":
    run_async(main())
# %%
