# %%
"""LLM Router e2e: QwenChat async text completion.

Why:
    Verifies that the public async text path works on QwenChat.

Covers:
    Area: QwenChat provider
    Behavior: async execution, text completion
    Interface: `LLMRouter(RouterProfile(...))`, `aquery(...)`

Checks:
    If the async public call succeeds, then the response object is populated.
    If the smoke prompt is honored, then the normalized reply is `pong`.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_qwenchat_async_text_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_qwenchat_async_text_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode, run_async

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_async,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# The prompt is intentionally tiny so any failure clearly belongs to the async path.


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
    """Build the smoke-test prompt."""
    return "Reply with only: pong"


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


async def run_pipeline() -> LLMRouterResponse:
    """Run the QwenChat async pipeline."""
    # Keep the public async call explicit and minimal.
    router = build_router()
    return await router.aquery(f"{_SYSTEM_PROMPT}\n\n{build_prompt()}")


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the smoke-test response."""
    # The public response object itself must be populated.
    assert response.data is not None
    # Then we check the normalized text so trivial punctuation drift does not
    # obscure whether the async path actually returned the right answer.
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
    # First run the public async smoke flow.
    response = await run_pipeline()
    # Then validate the stable short reply the scenario is built around.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask QwenChat for a tiny async response so we can verify "
        "the public async entry point.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same async flow the test validates.
    response = await run_pipeline()
    assert_pipeline_response(response)

    console.demo_step(
        "What Happened",
        "The async QwenChat path returned the expected short reply.",
        details=[
            f"Raw reply: {response.output_text}",
            f"Normalized reply: {normalize_reply(response.output_text)}",
            f"Has response payload: {response.data is not None}",
            f"Usage: {response.usage}",
        ],
    )
    console.demo_outcome(
        "This passed because the public async path completed "
        "successfully and returned the stable answer this smoke "
        "scenario expects."
    )


if __name__ == "__main__":
    run_async(main())
# %%
