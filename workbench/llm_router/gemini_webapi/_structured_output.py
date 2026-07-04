"""Gemini WebAPI workbench structured-output helpers.

Why:
    Keeps shared JSON parsing, prompts, and lightweight validation models in
    one place so the Gemini WebAPI capability scripts stay short and comparable.

When to use:
    Import from Gemini WebAPI workbench scripts that inspect structured JSON
    output for the shared image, PDF, or video fixtures.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

# ======================================================================================
# Shared Schema Models
# ======================================================================================


class TrafficSceneSummary(BaseModel):
    """Structured summary for the shared road-traffic image fixture."""

    primary_subject: str = Field(min_length=3)
    setting: str = Field(min_length=3)
    visible_objects: list[str] = Field(min_length=3)
    evidence: list[str] = Field(min_length=2)


class CalculationStep(BaseModel):
    """One structured tool step in a prompt-driven tool loop."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Structured final result for the prompt-driven tool-loop scenario."""

    steps: list[CalculationStep] = Field(min_length=1)
    final_result: int


class ForcedToolChoiceResult(BaseModel):
    """Structured final result for the prompt-driven named-tool scenario."""

    tool_name: str
    final_result: int
    explanation: str


class PaperMetadata(BaseModel):
    """Structured title metadata for the shared PDF fixture."""

    title: str
    title_words: list[str] = Field(min_length=3, max_length=3)


class PDFDigest(BaseModel):
    """Structured digest extracted from the shared PDF fixture."""

    metadata: PaperMetadata
    abstract_one_sentence: str = Field(min_length=20)
    contributions: list[str] = Field(min_length=3, max_length=3)
    evidence: list[str] = Field(min_length=2, max_length=2)
    key_entities: list[str] = Field(min_length=4, max_length=4)


class VideoObservation(BaseModel):
    """Minimal structured summary for a short video clip."""

    action: str = Field(min_length=4)
    location: str = Field(min_length=4)
    evidence: list[str] = Field(min_length=2)


# ======================================================================================
# Prompt Builders
# ======================================================================================


def build_scene_summary_prompt() -> str:
    """Build the shared structured-image prompt."""
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


def build_tool_loop_prompt() -> str:
    """Build the prompt-driven multi-step tool-loop prompt."""
    return (
        "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
        "Step 1: use add with a=2 and b=3.\n"
        "Step 2: multiply the step-1 result by 4.\n"
        "Do not solve the arithmetic yourself.\n"
        "Reply with exactly one function call like add(a=2, b=3) or "
        "multiply(a=5, b=4) and nothing else until both tool steps are finished.\n"
        "Do not return final JSON after step 1.\n"
        "After all tool results are provided, return JSON with:\n"
        "- steps: a list of tool call summaries with `tool_name` and `result`\n"
        "- final_result\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def build_named_tool_choice_prompt() -> str:
    """Build the prompt-driven named-tool-choice prompt."""
    return (
        "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
        "Use ONLY add with a=40 and b=2.\n"
        "Do not compute the answer yourself.\n"
        "Your first reply must be exactly one function call and nothing else.\n"
        "Do not return JSON before the tool result is provided.\n"
        "After the tool result is provided, return JSON with:\n"
        "- tool_name\n"
        "- final_result\n"
        "- explanation\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def build_pdf_digest_prompt() -> str:
    """Build the shared PDF extraction prompt."""
    return (
        "You are given a PDF file attachment.\n\n"
        "Extract content from the PDF itself, not file metadata.\n"
        "Return JSON with:\n"
        "- metadata.title: exact paper title from page 1, as a single line\n"
        "- metadata.title_words: exactly 3 distinct words taken from the title, "
        "preserving case\n"
        "- abstract_one_sentence: one sentence summarizing the Abstract (<= 25 words)\n"
        "- contributions: exactly 3 short bullet points (<= 12 words each)\n"
        "- evidence: exactly 2 verbatim snippets copied from page 1 (8+ chars)\n"
        "- key_entities: exactly 4 proper nouns or model names from page 1 "
        "(preserve case)\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def build_rooftop_video_prompt() -> str:
    """Build a deterministic prompt for the shared rooftop-jump clip."""
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
    """Build a deterministic prompt for a public indoor video URL."""
    return (
        "You are given a public video URL.\n\n"
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


# ======================================================================================
# JSON/Text Normalization Helpers
# ======================================================================================


def _extract_json_substring(text: str) -> str | None:
    """Best-effort extraction of a JSON object substring from model text."""
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def parse_model_output_json(text: str) -> dict[str, Any]:
    """Parse JSON-like model text and return one validated object payload."""
    cleaned = text.strip()
    cleaned = cleaned.removeprefix("```json")
    cleaned = cleaned.removeprefix("```")
    cleaned = cleaned.removesuffix("```")
    cleaned = cleaned.strip()

    last_error: Exception | None = None
    for candidate in (cleaned, _extract_json_substring(cleaned)):
        if candidate is None:
            continue
        try:
            parsed = json.loads(candidate)
        except Exception as exc:
            last_error = exc
            continue
        if not isinstance(parsed, dict):
            msg = "The live response JSON was not an object."
            raise TypeError(msg)
        return parsed

    msg = "The live response did not contain parseable JSON."
    raise ValueError(msg) from last_error


def normalize_text_for_match(text: str) -> str:
    """Normalize extracted PDF text for stable manual comparisons."""
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = " ".join(text.split())
    return re.sub(r"\s*-\s*", "-", text)
