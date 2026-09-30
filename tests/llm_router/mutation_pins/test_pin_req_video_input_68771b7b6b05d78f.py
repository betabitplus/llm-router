# mutation-pin: REQ_VIDEO_INPUT 68771b7b6b05d78f
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json
from typing import Any

import pytest
import vcr

from llm_router import LLMRouter, Model, Provider, RouterProfile, VideoSchema
from tests.llm_router.support.builders import get_llm_router_test_data_path
from tests.llm_router.support.media.video import VideoObservation

pytestmark = pytest.mark.verification_kind("unit")

_CASSETTE_NAME = (
    "test_a_provider_route_describes_the_example_rooftop_video[Google GenAI].yaml"
)


@pytest.mark.verifies("REQ_VIDEO_INPUT[revision==2]")
def test_local_video_end_offset_reaches_the_provider_request() -> None:
    video_path = get_llm_router_test_data_path("jumper.mp4")
    clip = VideoSchema(
        path=str(video_path),
        fps=2,
        start_offset=4,
        end_offset=22,
    )
    cassette = (
        video_path.parents[1]
        / "bdd/structured_output/cassettes/test_video"
        / _CASSETTE_NAME
    )
    bodies: list[bytes] = []

    def capture(received: Any, recorded: Any) -> bool:
        bodies.append(received.body)
        return recorded is not None

    recorder = vcr.VCR(decode_compressed_response=True)
    recorder.register_matcher("capture", capture)
    recorder.match_on = ["capture"]
    router = LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )

    with recorder.use_cassette(str(cassette), record_mode="none"):
        router.query(
            ["Describe the action in this clip.", clip],
            response_schema=VideoObservation,
        )

    request_body = json.loads(bodies[0])
    metadata = next(
        part["videoMetadata"]
        for content in request_body["contents"]
        for part in content["parts"]
        if "videoMetadata" in part
    )
    assert metadata["start_offset"] == "4s"
    assert metadata["end_offset"] == "22s"
