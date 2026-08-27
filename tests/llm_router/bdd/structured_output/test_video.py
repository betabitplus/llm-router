# %%
"""Bindings for the structured video BDD scenario."""

from __future__ import annotations

import pytest
from py_lib_testkit import evidence
from pytest_bdd import given, parsers, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.bdd._support import prepare_gemini_webapi_runtime
from tests.llm_router.support.builders import (
    build_test_video_file,
    build_test_video_url,
    get_llm_router_test_data_path,
)
from tests.llm_router.support.media.video import (
    VideoObservation,
    assert_indoor_video_response,
    assert_rooftop_video_response,
)

scenarios("structured_output/video.feature")

_VIDEO_FILENAME = "jumper.mp4"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_TEST_MODULE = "tests/llm_router/bdd/structured_output/test_video.py"


def _usage_payload(response: LLMRouterResponse) -> object:
    return (
        response.usage.model_dump(mode="json") if response.usage is not None else None
    )


def _video_router(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> LLMRouter:
    if route == "QwenChat":
        return LLMRouter(
            RouterProfile(model=Model.QWEN_VL_32B, provider=Provider.QWENCHAT),
            temperature=0.0,
            seed=42,
        )
    if route == "AI Studio":
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
            temperature=0.0,
            seed=42,
        )
    if route == "Gemini WebAPI":
        prepare_gemini_webapi_runtime(monkeypatch, request)
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
            temperature=0.0,
            seed=42,
        )
    if route == "Google GenAI":
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
            temperature=0.0,
            seed=42,
        )
    raise ValueError(route)  # pragma: no cover - Examples owns the valid values.


@given(parsers.parse('the "{route}" local video route'), target_fixture="video_route")
def local_video_route(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> tuple[str, LLMRouter]:
    return route, _video_router(route, monkeypatch, request)


@given(parsers.parse('the "{route}" remote video route'), target_fixture="video_route")
def remote_video_route(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> tuple[str, LLMRouter]:
    return route, _video_router(route, monkeypatch, request)


@when("the route analyzes the example rooftop video:", target_fixture="response")
def analyze_example_rooftop_video(
    video_route: tuple[str, LLMRouter],
    docstring: str,
) -> LLMRouterResponse:
    _, router = video_route
    video_path = get_llm_router_test_data_path(_VIDEO_FILENAME)
    evidence.file("Input video", video_path, media_type="video/mp4")
    return router.query(
        [_SYSTEM_PROMPT, docstring, build_test_video_file(_VIDEO_FILENAME)],
        response_schema=VideoObservation,
    )


@then("the observation is grounded in a rooftop jump")
def rooftop_observation_is_grounded(response: LLMRouterResponse) -> None:
    observation = assert_rooftop_video_response(response)
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "observation": observation.model_dump(mode="json"),
        },
    )


@when("the route analyzes the example remote video", target_fixture="response")
def analyze_example_remote_video(
    video_route: tuple[str, LLMRouter],
) -> LLMRouterResponse:
    from tests.llm_router.support.media.video import build_indoor_video_prompt

    _, router = video_route
    return router.query(
        [_SYSTEM_PROMPT, build_indoor_video_prompt(), build_test_video_url()],
        response_schema=VideoObservation,
    )


@then("the observation is grounded in the indoor activity")
def indoor_observation_is_grounded(response: LLMRouterResponse) -> None:
    observation = assert_indoor_video_response(response)
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "observation": observation.model_dump(mode="json"),
        },
    )


# %% Run this cell for video scenarios against live providers.
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
    )
# %%
