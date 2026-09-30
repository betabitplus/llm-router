# mutation-pin: REQ_VIDEO_INPUT 8ba45c4ec318c00e
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest
import vcr

from llm_router import LLMRouter, Model, Provider, RouterProfile, VideoUrlSchema
from tests.llm_router.support.builders import build_test_video_url
from tests.llm_router.support.media.video import (
    VideoObservation,
    build_indoor_video_prompt,
)
from tests.llm_router.support.vcr_extensions import FILTER_HEADERS

pytestmark = pytest.mark.verification_kind("unit")

_START_OFFSET_SECONDS = 5
_END_OFFSET_SECONDS = 55

_CASSETTE = (
    "tests/llm_router/bdd/structured_output/cassettes/test_video/"
    "test_a_provider_route_describes_the_example_remote_video[Google GenAI].yaml"
)


@pytest.mark.verifies("REQ_VIDEO_INPUT[revision==2]")
def test_remote_video_sent_to_provider_keeps_declared_start_offset(
    request: pytest.FixtureRequest,
) -> None:
    base_video = build_test_video_url()
    value = VideoUrlSchema(
        url=base_video.url,
        fps=base_video.fps,
        start_offset=_START_OFFSET_SECONDS,
        end_offset=_END_OFFSET_SECONDS,
    )
    sent: list[bytes] = []

    def capture(outgoing: object, recorded: object) -> None:
        _ = recorded
        body = getattr(outgoing, "body", None)
        sent.append(body if isinstance(body, bytes) else str(body).encode("utf-8"))

    recorder = vcr.VCR(
        match_on=["method", "scheme", "host", "path", "capture"],
        decode_compressed_response=True,
        filter_headers=FILTER_HEADERS,
    )
    recorder.register_matcher("capture", capture)
    router = LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )
    cassette = str(request.config.rootpath / _CASSETTE)
    with recorder.use_cassette(cassette, record_mode="none"):
        router.query(
            ["Follow instructions.", build_indoor_video_prompt(), value],
            response_schema=VideoObservation,
        )

    payload = json.loads(sent[0])
    parts = [
        part
        for content in payload["contents"]
        for part in content["parts"]
        if "videoMetadata" in part
    ]
    metadata = parts[0]["videoMetadata"]
    assert metadata["start_offset"] == f"{_START_OFFSET_SECONDS}s"
    assert metadata["end_offset"] == f"{_END_OFFSET_SECONDS}s"
