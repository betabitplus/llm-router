"""Negative controls for the media payloads the Verification Profiles require.

Each test replays a media scenario's recorded provider exchange twice: once as the
scenario sends it, which the recording answers, and once with one field of the media
part changed on its way to the provider (``interface.payload-schema``). The recording
is matched by the request body, so a changed payload finds no recorded answer and the
request fails: the known-bad sample goes red under the oracle the media scenarios
use. A media part whose change the replay does not notice fails its control.
"""

from __future__ import annotations

import base64
import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import vcr
from PIL import Image
from pytest_bdd.parser import FeatureParser

from llm_router import LLMRouter, Model, Provider, ProviderError, RouterProfile
from llm_router._internal.providers import (
    google_genai as google_module,
    openai_compatible as openai_module,
)
from tests.llm_router.conftest import _vcr_scrub_request, _vcr_scrub_response
from tests.llm_router.support.builders import (
    build_test_image,
    build_test_pdf_file,
    build_test_video_url,
)
from tests.llm_router.support.fault_observation import retain_local_fault_injection
from tests.llm_router.support.media.pdf import PDFDigest
from tests.llm_router.support.media.scene import SceneSummary
from tests.llm_router.support.media.video import (
    VideoObservation,
    build_indoor_video_prompt,
)
from tests.llm_router.support.vcr_extensions import (
    FILTER_HEADERS,
    MATCH_ON,
    register_vcr_extensions,
)

_ROOT = Path(__file__).resolve().parents[3]
_CASSETTES = _ROOT / "tests/llm_router/bdd/structured_output/cassettes"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_FAULT = "interface.payload-schema"


def _docstring(feature: str, step: str) -> str:
    """The docstring a scenario hands its step, as pytest-bdd parses it."""
    parsed = FeatureParser(basedir=str(_ROOT / "features"), filename=feature).parse()
    return next(
        item.docstring or ""
        for scenario in parsed.scenarios.values()
        for item in scenario.steps
        if item.name == step
    )


def _replay(cassette: str, ask: Callable[[], Any]) -> Any:
    """Replay a scenario's recording as the scenarios do: the same matchers and the
    same scrubbing of each request before it is matched (bodies are fingerprinted)."""
    recorder = vcr.VCR(
        match_on=MATCH_ON,
        decode_compressed_response=True,
        filter_headers=FILTER_HEADERS,
        before_record_request=_vcr_scrub_request,
        before_record_response=_vcr_scrub_response,
    )
    register_vcr_extensions(recorder)
    with recorder.use_cassette(str(_CASSETTES / cassette), record_mode="none"):
        return ask()


def _google_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )


@pytest.mark.verifies("REQ_DOCUMENT_INPUT[revision==1]")
@pytest.mark.verification_kind("integration")
@pytest.mark.fault_item("REQ_DOCUMENT_INPUT", _FAULT)
def test_document_part_with_a_changed_mime_type_finds_no_recorded_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retain_local_fault_injection(
        contract_id="REQ_DOCUMENT_INPUT",
        fault_class=_FAULT,
        mechanism="the PDF part reaches the provider with another mime type",
    )
    cassette = (
        "test_documents/test_a_provider_route_extracts_a_grounded_digest_from_the_"
        "example_pdf[Google GenAI].yaml"
    )
    prompt = _docstring(
        "structured_output/documents.feature", "the route analyzes the example PDF:"
    )

    def ask() -> object:
        return _google_router().query(
            [_SYSTEM_PROMPT, prompt, build_test_pdf_file("variative.pdf")],
            response_schema=PDFDigest,
        )

    assert _replay(cassette, ask).output_text
    built = google_module._part_payload

    def changed(part: Any) -> Any:
        payload = built(part)
        if payload.inline_data is not None:
            payload.inline_data.mime_type = "application/octet-stream"
        return payload

    monkeypatch.setattr(google_module, "_part_payload", changed)
    with pytest.raises(ProviderError, match=r"."):
        _replay(cassette, ask)


@pytest.mark.verifies("REQ_IMAGE_INPUT[revision==1]")
@pytest.mark.verification_kind("integration")
@pytest.mark.fault_item("REQ_IMAGE_INPUT", _FAULT)
def test_image_part_with_other_pixels_finds_no_recorded_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retain_local_fault_injection(
        contract_id="REQ_IMAGE_INPUT",
        fault_class=_FAULT,
        mechanism=(
            "the image part reaches the provider carrying other pixels than the "
            "attached image (the replay's matcher reads an image by its pixels, so a "
            "re-encoding alone is no fault)"
        ),
    )
    cassette = (
        "test_images/test_a_provider_route_describes_the_example_traffic_image"
        "[OpenAI-compatible].yaml"
    )
    prompt = _docstring(
        "structured_output/images.feature",
        "the route analyzes the example traffic image:",
    )

    def ask() -> object:
        return LLMRouter(
            RouterProfile(model=Model.MISTRAL_LARGE, provider=Provider.MISTRAL),
            temperature=0.0,
        ).query(
            [_SYSTEM_PROMPT, prompt, build_test_image("test_image.png")],
            response_schema=SceneSummary,
        )

    assert _replay(cassette, ask).output_text
    blank = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(blank, format="JPEG")
    other = "data:image/jpeg;base64," + base64.b64encode(blank.getvalue()).decode()
    monkeypatch.setattr(openai_module, "_image_data_url", lambda _media: other)
    with pytest.raises(ProviderError, match=r"."):
        _replay(cassette, ask)


@pytest.mark.verifies("REQ_VIDEO_INPUT[revision==2]")
@pytest.mark.verification_kind("integration")
@pytest.mark.fault_item("REQ_VIDEO_INPUT", _FAULT)
def test_remote_video_part_with_a_changed_uri_finds_no_recorded_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retain_local_fault_injection(
        contract_id="REQ_VIDEO_INPUT",
        fault_class=_FAULT,
        mechanism="the remote video part reaches the provider with another URI",
    )
    cassette = (
        "test_video/test_a_provider_route_describes_the_example_remote_video"
        "[Google GenAI].yaml"
    )

    def ask() -> object:
        return _google_router().query(
            [_SYSTEM_PROMPT, build_indoor_video_prompt(), build_test_video_url()],
            response_schema=VideoObservation,
        )

    assert _replay(cassette, ask).output_text
    built = google_module._part_payload

    def changed(part: Any) -> Any:
        payload = built(part)
        if payload.file_data is not None:
            payload.file_data.file_uri = f"{payload.file_data.file_uri}#changed"
        return payload

    monkeypatch.setattr(google_module, "_part_payload", changed)
    with pytest.raises(ProviderError, match=r"."):
        _replay(cassette, ask)
