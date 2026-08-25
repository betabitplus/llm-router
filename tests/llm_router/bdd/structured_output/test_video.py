# %%
"""Bindings for the structured video living specification."""

from __future__ import annotations

from py_lib_testkit import evidence
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.builders import (
    build_test_video_file,
    get_llm_router_test_data_path,
)
from tests.llm_router.support.media.video import (
    VideoObservation,
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


@given("the QwenChat video route", target_fixture="router")
def qwenchat_video_route() -> LLMRouter:
    """Build the QwenChat route used by the local-video example."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_VL_32B, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


@when("the route analyzes the example video:", target_fixture="response")
def analyze_example_video(router: LLMRouter, docstring: str) -> LLMRouterResponse:
    """Send the shared clip through the public video path using the Gherkin prompt."""
    video_path = get_llm_router_test_data_path(_VIDEO_FILENAME)
    evidence.file("Input video", video_path, media_type="video/mp4")
    return router.query(
        [_SYSTEM_PROMPT, docstring, build_test_video_file(_VIDEO_FILENAME)],
        response_schema=VideoObservation,
    )


@then("the observation is grounded in a rooftop jump")
def rooftop_observation_is_grounded(response: LLMRouterResponse) -> None:
    """Validate and publish the structured video observation."""
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


# %% Run this cell in VS Code's Interactive Window for a real provider call.
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
