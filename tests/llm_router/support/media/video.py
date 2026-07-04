"""llm_router-specific video scenario helpers.

Why:
    Reuses the shared video schema, prompts, and grounded assertions across
    llm_router video e2e scenarios.

When to use:
    Import from here when a video scenario should validate the same public
    contract on different providers.

How:
    Use `VideoObservation`, the shared prompt builders, and the assertion
    helpers instead of duplicating video-specific schemas in each e2e script.

Examples:
    parsed = assert_rooftop_video_response(response)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from llm_router import LLMRouterResponse
from tests.llm_router.support.assertions import (
    assert_output_text_not_empty,
    parse_json_object,
)


class VideoObservation(BaseModel):
    """Minimal structured summary for a short video clip."""

    action: str = Field(min_length=4)
    location: str = Field(min_length=4)
    evidence: list[str] = Field(min_length=2)


def build_rooftop_video_prompt() -> str:
    """Build a deterministic prompt for the local rooftop-jump clip."""
    return (
        "You are given a short video clip.\n\n"
        "Return JSON with exactly three keys:\n"
        "- action: the main action as a short lowercase verb or gerund\n"
        "- location: a short phrase describing where the action happens\n\n"
        "- evidence: exactly 2 short strings describing visible motion or "
        "scene cues\n\n"
        'If the clip shows a person jumping or leaping, use a value containing "jump" '
        'or "leap" for action.\n'
        "If it happens on a rooftop, skyscraper, or tall building, mention that in "
        "location.\n"
        "In evidence, mention motion or jump-related details.\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def build_indoor_video_prompt() -> str:
    """Build a deterministic prompt for the provided indoor Shorts clip."""
    return (
        "You are given a short video clip.\n\n"
        "Return JSON with exactly three keys:\n"
        "- action: the main activity as a short lowercase word or phrase\n"
        "- location: a short phrase describing where it happens\n\n"
        "- evidence: exactly 2 short strings describing visible motion or "
        "scene cues\n\n"
        "If the clip happens indoors in a gym, dance studio, or training room, "
        "mention that in location.\n"
        "In evidence, mention movement, posture, or indoor scene details.\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def assert_rooftop_video_response(response: LLMRouterResponse) -> VideoObservation:
    """Assert the rooftop-jump invariants for the local video asset."""
    assert_output_text_not_empty(response)
    parsed = VideoObservation.model_validate(parse_json_object(response.output_text))

    action = parsed.action.lower()
    location = parsed.location.lower()
    assert any(token in action for token in ("jump", "leap"))
    assert any(
        token in location
        for token in ("roof", "rooftop", "building", "skyscraper", "high-rise")
    )
    evidence_text = " ".join(parsed.evidence).lower()
    assert any(
        token in evidence_text
        for token in ("jump", "leap", "motion", "air", "landing", "roof", "building")
    )
    return parsed


def assert_indoor_video_response(response: LLMRouterResponse) -> VideoObservation:
    """Assert coarse indoor-setting invariants for the provided Shorts URL."""
    assert_output_text_not_empty(response)
    parsed = VideoObservation.model_validate(parse_json_object(response.output_text))

    assert parsed.action.strip()
    location = parsed.location.lower()
    assert any(
        token in location for token in ("gym", "studio", "indoor", "training", "dance")
    )
    evidence_text = " ".join(parsed.evidence).lower()
    has_activity_cue = any(
        token in evidence_text
        for token in (
            "move",
            "motion",
            "dance",
            "exercise",
            "training",
            "lifting",
            "hoist",
            "shoulder",
            "posture",
        )
    )
    has_indoor_scene_cue = any(
        token in evidence_text
        for token in (
            "indoor",
            "studio",
            "gym",
            "mirror",
            "equipment",
            "treadmill",
            "weights",
            "fitness",
        )
    )
    assert has_activity_cue or has_indoor_scene_cue
    return parsed
