# %%
"""Bindings for the async public execution living specification."""

from __future__ import annotations

import asyncio

from py_lib_testkit import evidence
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.media.legal import LegalCase, assert_legal_case_response

scenarios("execution/async.feature")

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_LEGAL_SYSTEM_PROMPT = "You are a legal assistant. Extract case details."
_TEST_MODULE = "tests/llm_router/bdd/execution/test_async.py"


def _usage_payload(response: LLMRouterResponse) -> object:
    return (
        response.usage.model_dump(mode="json") if response.usage is not None else None
    )


@given("the QwenChat async route", target_fixture="router")
def qwenchat_async_route() -> LLMRouter:
    """Build the QwenChat route used by the async text example."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


@given("the OpenAI-compatible async route", target_fixture="router")
def openai_compatible_async_route() -> LLMRouter:
    """Build the generic OpenAI-compatible route used by the structured example."""
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )


@when("the async route receives:", target_fixture="response")
def request_short_text(router: LLMRouter, docstring: str) -> LLMRouterResponse:
    """Execute the public async text call using the Gherkin request."""
    return asyncio.run(router.aquery(f"{_SYSTEM_PROMPT}\n\n{docstring}"))


@then('the normalized reply is "pong"')
def short_text_reply_is_preserved(response: LLMRouterResponse) -> None:
    """Validate and publish the short async reply."""
    normalized = response.output_text.strip().rstrip(".").lower()
    assert response.data is not None
    assert normalized == "pong"
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "reply": response.output_text,
        },
    )


@when("the async route extracts a legal case from:", target_fixture="response")
def extract_legal_case(router: LLMRouter, docstring: str) -> LLMRouterResponse:
    """Execute the public async structured-output call using the Gherkin case text."""
    return asyncio.run(
        router.aquery(
            [_LEGAL_SYSTEM_PROMPT, docstring],
            response_schema=LegalCase,
            temperature=0.0,
        )
    )


@then("the structured case preserves its parties and legal issues")
def legal_case_is_preserved(response: LLMRouterResponse) -> None:
    """Validate and publish the structured legal-case result."""
    case = assert_legal_case_response(response)
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "legal_case": case.model_dump(mode="json"),
        },
    )


# %% QwenChat live: run this cell in VS Code's Interactive Window.
if __name__ == "__main__":
    import ipytest

    ipytest.run(
        "-q",
        "-s",
        "--disable-recording",
        "--no-cov",
        "-k",
        "qwenchat",
        _TEST_MODULE,
        defopts=False,
        raise_on_error=True,
        run_in_thread=True,
    )
# %% OpenAI-compatible live: run this cell separately when desired.
if __name__ == "__main__":
    import ipytest

    ipytest.run(
        "-q",
        "-s",
        "--disable-recording",
        "--no-cov",
        "-k",
        "legal_case",
        _TEST_MODULE,
        defopts=False,
        raise_on_error=True,
        run_in_thread=True,
    )
# %%
