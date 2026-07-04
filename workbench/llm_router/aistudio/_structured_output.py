"""AI Studio workbench structured-output models and prompts.

Why:
    Keeps reusable AI Studio workbench schemas and prompts together so the
    executable scripts stay focused on one provider seam at a time.

When to use:
    Import from AI Studio workbench scripts that need a prompt plus one local
    response model for structured output.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ======================================================================================
# Text-Only Scenario
# ======================================================================================


class Actor(BaseModel):
    """Structured cast member entry."""

    name: str
    character_name: str


class Review(BaseModel):
    """Short review entry."""

    source: str
    rating: float = Field(description="Rating out of 10")


class MovieRecord(BaseModel):
    """Structured movie record for the AI Studio text scenario."""

    movie_title: str
    director: str
    cast: list[Actor] = Field(min_length=3)
    reviews: list[Review] = Field(min_length=2)
    tagline: str


def build_movie_prompt() -> str:
    """Build the shared movie-record prompt."""
    return (
        "Generate a database entry for the 2010 movie Inception.\n\n"
        "Return JSON with:\n"
        "- movie_title\n"
        "- director\n"
        "- cast: at least 3 actors with `name` and `character_name`\n"
        "- reviews: at least 2 entries with `source` and numeric `rating`\n"
        "- tagline\n\n"
        "Return ONLY valid JSON. No markdown."
    )


# ======================================================================================
# Image Scenario
# ======================================================================================


class SceneSummary(BaseModel):
    """Structured image summary for the AI Studio image scenario."""

    primary_subject: str
    setting: str
    visible_objects: list[str] = Field(min_length=3)
    evidence: list[str] = Field(min_length=2)


def build_scene_summary_prompt() -> str:
    """Build the structured-image prompt."""
    return (
        "Describe the attached image and return JSON.\n\n"
        "Return exactly these keys:\n"
        "- primary_subject: a short phrase naming the main thing shown\n"
        "- setting: a short phrase describing the setting\n"
        "- visible_objects: at least 3 short object names\n"
        "- evidence: at least 2 short phrases grounding the answer in the image\n\n"
        "If the scene is a road, highway, or traffic setting, mention that clearly.\n"
        "Return ONLY valid JSON. No markdown."
    )


# ======================================================================================
# Tool Scenarios
# ======================================================================================


class CalculationStep(BaseModel):
    """Structured tool-step summary."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Structured result for the AI Studio tools scenario."""

    steps: list[CalculationStep] = Field(min_length=2)
    final_result: int


class ForcedToolChoiceResult(BaseModel):
    """Structured result for the forced named-tool-choice scenario."""

    tool_name: str
    final_result: int
    explanation: str


def build_tool_choice_prompt() -> str:
    """Build the forced-tool-choice prompt."""
    return (
        "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
        "Use ONLY add with a=40 and b=2, then reply with ONLY the number."
    )


def build_tools_structured_prompt() -> str:
    """Build the multi-round structured tool prompt."""
    return (
        "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
        "Step 1: use add with a=40 and b=2.\n"
        "Step 2: multiply the step-1 result by 2.\n"
        "Return JSON with:\n"
        "- steps: a list of tool call summaries with `tool_name` and `result`\n"
        "- final_result\n\n"
        "Return ONLY valid JSON. No markdown."
    )


# ======================================================================================
# Schema-Resolution Scenario
# ======================================================================================


class CandidateProfile(BaseModel):
    """Nested profile section for the schema-resolution scenario."""

    full_name: str
    strengths: list[str] = Field(min_length=2)


class InterviewAssessment(BaseModel):
    """Nested assessment section for the schema-resolution scenario."""

    recommendation: str
    evidence: list[str] = Field(min_length=2)


class CandidatePacket(BaseModel):
    """Nested structured record used to trigger `$defs` and `$ref`."""

    candidate_profile: CandidateProfile
    interview_assessment: InterviewAssessment


def build_candidate_packet_prompt() -> str:
    """Build the nested-schema prompt for the `$ref`-resolution scenario."""
    return (
        "Create a hiring-screen summary for candidate Maya Chen.\n\n"
        "Return JSON with:\n"
        "- candidate_profile: object with `full_name` and at least 2 `strengths`\n"
        "- interview_assessment: object with `recommendation` and at least 2 "
        "`evidence` strings\n\n"
        "Return ONLY valid JSON. No markdown."
    )


# ======================================================================================
# Video Scenarios
# ======================================================================================


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
        "- location: a short phrase describing where the action happens\n"
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
        "- location: a short phrase describing where it happens\n"
        "- evidence: exactly 2 short strings describing visible motion or "
        "scene cues\n\n"
        "If the clip happens indoors in a gym, dance studio, or training room, "
        "mention that in location.\n"
        "In evidence, mention movement, posture, or indoor scene details.\n\n"
        "Return ONLY valid JSON. No markdown."
    )
