# mutation-pin: REQ_VIDEO_INPUT 8ba45c4ec318c00e
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
import vcr

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    RouterProfile,
    VideoUrlSchema,
)
from tests.llm_router.support.builders import build_test_video_url
from tests.llm_router.support.media.video import build_indoor_video_prompt
from tests.llm_router.support.vcr_extensions import FILTER_HEADERS

pytestmark = pytest.mark.verification_kind("unit")

_START_OFFSET = 1337
_END_OFFSET = 9001

_CASSETTE = (
    "tests/llm_router/bdd/structured_output/cassettes/test_video/"
    "test_a_provider_route_describes_the_example_remote_video[Google GenAI].yaml"
)


class StopCaptureError(RuntimeError):
    pass


@pytest.mark.verifies("REQ_VIDEO_INPUT[revision==2]")
def test_remote_video_descriptor_preserves_distinct_start_offset(
    request: pytest.FixtureRequest,
) -> None:
    base_video = build_test_video_url()
    value = VideoUrlSchema(
        url=base_video.url,
        fps=base_video.fps,
        start_offset=_START_OFFSET,
        end_offset=_END_OFFSET,
    )
    sent: list[bytes] = []

    def capture(outgoing: object, recorded: object) -> None:
        if recorded is not None:
            body = getattr(outgoing, "body", None)
            if body is not None:
                sent.append(
                    body if isinstance(body, bytes) else str(body).encode("utf-8")
                )
        raise StopCaptureError("captured")

    recorder = vcr.VCR(
        match_on=["method", "scheme", "host", "path", "capture"],
        decode_compressed_response=True,
        filter_headers=FILTER_HEADERS,
    )
    recorder.register_matcher("capture", capture)
    router = LLMRouter(
        RouterProfile(
            model=Model.GEMINI_FLASH,
            provider=Provider.GOOGLE,
            max_attempts=1,
        ),
        temperature=0.0,
        seed=42,
    )
    cassette = str(request.config.rootpath / _CASSETTE)
    with (
        pytest.raises((ProviderError, StopCaptureError), match=r"."),
        recorder.use_cassette(cassette, record_mode="none"),
    ):
        router.query([build_indoor_video_prompt(), value])

    body_str = next(iter(sent)).decode("utf-8")
    assert str(_START_OFFSET) in body_str
    assert str(_END_OFFSET) in body_str
