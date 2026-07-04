"""Google GenAI workbench structured-output helpers.

Why:
    Keeps shared prompt builders and lightweight response models in one place
    so the Google GenAI capability scripts stay short and comparable.

When to use:
    Import from Google GenAI workbench scripts that inspect structured output
    for the shared image, PDF, video, or tool-loop scenarios.
"""

from __future__ import annotations

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


class LegalCaseSummary(BaseModel):
    """Structured legal-case summary for text-only schema probes."""

    case_name: str
    court: str
    plaintiffs: list[str] = Field(min_length=1)
    defendants: list[str] = Field(min_length=1)
    legal_issues: list[str] = Field(min_length=3)


class PaperMetadata(BaseModel):
    """Structured title metadata for the shared PDF fixture."""

    title: str
    title_words: list[str] = Field(min_length=3, max_length=3)


class EvidenceSnippet(BaseModel):
    """Short grounded evidence copied from page one."""

    text: str = Field(min_length=8)
    source: str


class PDFDigest(BaseModel):
    """Structured digest extracted from the shared PDF fixture."""

    metadata: PaperMetadata
    abstract_one_sentence: str = Field(min_length=20)
    contributions: list[str] = Field(min_length=3, max_length=3)
    evidence: list[EvidenceSnippet] = Field(min_length=2, max_length=2)
    key_entities: list[str] = Field(min_length=4, max_length=4)


class VideoObservation(BaseModel):
    """Minimal structured summary for a short video clip."""

    action: str = Field(min_length=4)
    location: str = Field(min_length=4)
    evidence: list[str] = Field(min_length=2)


class ToolCallSummary(BaseModel):
    """Structured tool-call summary for the final JSON response."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Structured final result for the callable tool-loop scenario."""

    final_result: int
    tool_calls: list[ToolCallSummary] = Field(min_length=1)


class ForcedToolChoiceResult(BaseModel):
    """Structured final result for the named-tool-choice scenario."""

    tool_name: str
    final_result: int
    explanation: str


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


def build_legal_case_prompt() -> str:
    """Build the shared structured-text prompt."""
    return (
        "Convert the case summary into JSON with:\n"
        "- case_name\n"
        "- court\n"
        "- plaintiffs\n"
        "- defendants\n"
        "- legal_issues\n\n"
        "Case summary: In Smith v. Horizon Retail LLC, the plaintiff Alice Smith "
        "sued Horizon Retail LLC in the Delaware Superior Court after a warehouse "
        "forklift injured her during a loading operation. The dispute focused on "
        "negligence, workplace safety failures, and Horizon's maintenance duties.\n\n"
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
        "  - source must be one of: title, abstract, introduction\n"
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
    """Build a deterministic prompt for the shared remote indoor clip."""
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


def build_tool_audit_prompt() -> str:
    """Build the callable tool-loop prompt."""
    return (
        "You have a tool named multiply(a, b) that returns {result}.\n"
        "Compute 17*19 using the tool.\n"
        "Then return JSON with:\n"
        "- final_result\n"
        "- tool_calls: a list of tool call summaries with `tool_name` and `result`\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def build_named_tool_choice_prompt() -> str:
    """Build the named-tool-choice prompt with a structured final result."""
    return (
        "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
        "Use ONLY add with a=2 and b=3.\n"
        "Then return JSON with:\n"
        "- tool_name\n"
        "- final_result\n"
        "- explanation\n\n"
        "Return ONLY valid JSON. No markdown."
    )
