# %%
"""Bindings for the async public execution BDD scenario."""

from __future__ import annotations

import asyncio

import pytest
from py_lib_testkit import evidence
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.bdd._support import prepare_gemini_webapi_runtime
from tests.llm_router.support.builders import (
    build_test_image,
    get_llm_router_test_data_path,
)
from tests.llm_router.support.media.legal import LegalCase, assert_legal_case_response
from tests.llm_router.support.media.movie import (
    MovieRecord,
    assert_movie_record_response,
    build_movie_prompt,
)
from tests.llm_router.support.media.scene import (
    SceneSummary,
    assert_traffic_scene_response,
    build_scene_summary_prompt,
)

scenarios("execution/async.feature")

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_LEGAL_SYSTEM_PROMPT = "You are a legal assistant. Extract case details."
_MOVIE_SYSTEM_PROMPT = "You are a movie database API."
_IMAGE_FILENAME = "test_image.png"
_TEST_MODULE = "tests/llm_router/bdd/execution/test_async.py"


def _usage_payload(response: LLMRouterResponse) -> object:
    return (
        response.usage.model_dump(mode="json") if response.usage is not None else None
    )


@given("the QwenChat async route", target_fixture="router")
def qwenchat_async_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


@given("the Gemini WebAPI async route", target_fixture="router")
def gemini_webapi_async_route(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> LLMRouter:
    prepare_gemini_webapi_runtime(monkeypatch, request)
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
        temperature=0.0,
        seed=42,
    )


@given("the OpenAI-compatible async route", target_fixture="router")
def openai_compatible_async_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )


@given("the AI Studio async route", target_fixture="router")
def aistudio_async_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


@given("the Google GenAI async image route", target_fixture="router")
def google_async_image_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )


@when("the async route receives:", target_fixture="response")
def request_short_text(router: LLMRouter, docstring: str) -> LLMRouterResponse:
    return asyncio.run(router.aquery(f"{_SYSTEM_PROMPT}\n\n{docstring}"))


@then('the normalized reply is "pong"')
def short_text_reply_is_preserved(response: LLMRouterResponse) -> None:
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
    return asyncio.run(
        router.aquery(
            [_LEGAL_SYSTEM_PROMPT, docstring],
            response_schema=LegalCase,
            temperature=0.0,
        )
    )


@then("the structured case preserves its parties and legal issues")
def legal_case_is_preserved(response: LLMRouterResponse) -> None:
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


@when("the async route requests the example movie record", target_fixture="response")
def request_movie_record(router: LLMRouter) -> LLMRouterResponse:
    return asyncio.run(
        router.aquery(
            [_MOVIE_SYSTEM_PROMPT, build_movie_prompt()],
            response_schema=MovieRecord,
        )
    )


@then("the structured movie record is grounded in Inception")
def movie_record_is_grounded(response: LLMRouterResponse) -> None:
    movie = assert_movie_record_response(response)
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "movie": movie.model_dump(mode="json"),
        },
    )


@when("the async route analyzes the example traffic image", target_fixture="response")
def analyze_image_asynchronously(router: LLMRouter) -> LLMRouterResponse:
    image_path = get_llm_router_test_data_path(_IMAGE_FILENAME)
    evidence.file("Input image", image_path, media_type="image/png")
    return asyncio.run(
        router.aquery(
            [
                _SYSTEM_PROMPT,
                build_scene_summary_prompt(),
                build_test_image(_IMAGE_FILENAME),
            ],
            response_schema=SceneSummary,
        )
    )


@then("the async image result is a grounded traffic scene")
def async_image_is_grounded(response: LLMRouterResponse) -> None:
    scene = assert_traffic_scene_response(response)
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "scene": scene.model_dump(mode="json"),
        },
    )


# %% Run this cell for the selected async BDD scenarios.
# They execute against live providers.
if __name__ == "__main__":
    import ipytest

    ipytest.run(
        "-q",
        "-s",
        "--disable-recording",
        "--no-cov",
        _TEST_MODULE,
        defopts=False,
        raise_on_error=True,
        run_in_thread=True,
    )
# %%
