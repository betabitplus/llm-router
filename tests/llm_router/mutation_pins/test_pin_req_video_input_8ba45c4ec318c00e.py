# mutation-pin: REQ_VIDEO_INPUT 8ba45c4ec318c00e
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

import llm_router
from llm_router import VideoUrlSchema
from tests.llm_router.support.builders import build_test_video_url

pytestmark = pytest.mark.verification_kind("unit")

_START_OFFSET_SECONDS = 5
_END_OFFSET_SECONDS = 55


@pytest.mark.verifies("REQ_VIDEO_INPUT[revision==2]")
def test_remote_video_descriptor_keeps_declared_start_offset() -> None:
    base_video = build_test_video_url()
    value = VideoUrlSchema(
        url=base_video.url,
        fps=base_video.fps,
        start_offset=_START_OFFSET_SECONDS,
        end_offset=_END_OFFSET_SECONDS,
    )
    describe_media = llm_router._internal.capabilities.media.describe_media

    descriptor = describe_media(value)

    assert descriptor.kind == "video_url"
    assert descriptor.url == base_video.url
    assert descriptor.fps == base_video.fps
    assert descriptor.start_offset == _START_OFFSET_SECONDS
    assert descriptor.end_offset == _END_OFFSET_SECONDS
