# %%
"""Bindings for the structured image BDD scenario."""

from __future__ import annotations

import pytest
from py_lib_testkit import evidence
from pytest_bdd import given, parsers, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.bdd._support import prepare_gemini_webapi_runtime
from tests.llm_router.support.builders import (
    build_test_image,
    get_llm_router_test_data_path,
)
from tests.llm_router.support.media.scene import (
    SceneSummary,
    assert_traffic_scene_response,
)

scenarios("structured_output/images.feature")

_IMAGE_FILENAME = "test_image.png"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."


def _usage_payload(response: LLMRouterResponse) -> object:
    return (
        response.usage.model_dump(mode="json") if response.usage is not None else None
    )


@given(parsers.parse('the "{route}" image route'), target_fixture="image_route")
def provider_image_route(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> tuple[str, LLMRouter]:
    if route == "QwenChat":
        router = LLMRouter(
            RouterProfile(model=Model.QWEN3_VL_PLUS, provider=Provider.QWENCHAT),
            temperature=0.0,
            seed=42,
        )
    elif route == "OpenAI-compatible":
        router = LLMRouter(
            RouterProfile(model=Model.MISTRAL_LARGE, provider=Provider.MISTRAL),
            temperature=0.0,
        )
    elif route == "AI Studio":
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
            temperature=0.0,
            seed=42,
        )
    elif route == "Gemini WebAPI":
        prepare_gemini_webapi_runtime(monkeypatch, request)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
            temperature=0.0,
            seed=42,
        )
    else:  # pragma: no cover - the Gherkin Examples table owns the valid values.
        raise ValueError(route)
    return route, router


@when("the route analyzes the example traffic image:", target_fixture="response")
def analyze_traffic_image(
    image_route: tuple[str, LLMRouter],
    docstring: str,
) -> LLMRouterResponse:
    route, router = image_route
    image_path = get_llm_router_test_data_path(_IMAGE_FILENAME)
    evidence.file("Input image", image_path, media_type="image/png")
    image = build_test_image(_IMAGE_FILENAME)
    if route == "QwenChat":
        messages = [f"{_SYSTEM_PROMPT}\n\n{docstring}", image]
    else:
        messages = [_SYSTEM_PROMPT, docstring, image]
    return router.query(messages, response_schema=SceneSummary)


@then("the result is a grounded traffic scene")
def traffic_scene_is_grounded(response: LLMRouterResponse) -> None:
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
