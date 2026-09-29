# mutation-pin: REQ_VIDEO_INPUT a6b4e513b6f3bf73
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

import llm_router
from llm_router import VideoUrlSchema
from tests.llm_router.support.builders import build_test_video_url

pytestmark = pytest.mark.verification_kind("unit")

_START_OFFSET = 5
_END_OFFSET = 55


@pytest.mark.verifies("REQ_VIDEO_INPUT[revision==2]")
def test_remote_video_descriptor_keeps_distinct_end_offset() -> None:
    media = llm_router._internal.capabilities.media
    base = build_test_video_url()
    video = VideoUrlSchema(
        url=base.url,
        fps=base.fps,
        start_offset=_START_OFFSET,
        end_offset=_END_OFFSET,
    )

    descriptor = media.describe_media(video)

    assert descriptor.kind == "video_url"
    assert descriptor.url == base.url
    assert descriptor.fps == base.fps
    assert descriptor.start_offset == _START_OFFSET
    assert descriptor.end_offset == _END_OFFSET
