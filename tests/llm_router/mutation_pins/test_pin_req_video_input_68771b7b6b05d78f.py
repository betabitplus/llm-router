# mutation-pin: REQ_VIDEO_INPUT 68771b7b6b05d78f
# pinned-by: claude-opus-5-5
"""Pin REQ_VIDEO_INPUT[revision==2]: video end_offset survives normalization.

describe_media() must copy VideoSchema.end_offset into the returned
VideoFileMedia.end_offset. A known defect instead copies start_offset
into that field, so this test uses a clip whose start_offset and
end_offset differ and checks that the returned end_offset matches the
input's end_offset, not its start_offset.
"""

from __future__ import annotations

import pytest

import llm_router
from llm_router import VideoSchema
from tests.llm_router.support.builders import get_llm_router_test_data_path

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_VIDEO_INPUT[revision==2]")
def test_describe_media_keeps_video_end_offset_distinct_from_start() -> None:
    video_path = get_llm_router_test_data_path("jumper.mp4")
    clip = VideoSchema(
        path=str(video_path),
        fps=2,
        start_offset=4,
        end_offset=22,
    )

    descriptor = llm_router._internal.capabilities.media.describe_media(clip)

    assert descriptor.kind == "video_file"
    assert descriptor.start_offset == 4
    assert descriptor.end_offset == 22
