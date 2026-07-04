"""QwenChat workbench structured-output helpers.

Why:
    Keeps shared schema models, prompts, and JSON validation helpers in one
    place so the QwenChat workbench scripts stay focused on one provider seam.

When to use:
    Import from QwenChat workbench scripts that need prompt-enforced JSON
    validation for text, image, or PDF scenarios.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from tests.llm_router.support.media.pdf import (
    PDFDigest,
    build_pdf_digest_prompt,
    extract_expected_pdf_facts,
    normalize_text_for_match,
)
from tests.llm_router.support.media.scene import (
    SceneSummary,
    build_scene_summary_prompt,
)

__all__ = [
    "CalculationAudit",
    "CalculationStep",
    "ForcedToolChoiceResult",
    "IncidentReport",
    "PDFDigest",
    "SceneSummary",
    "VideoObservation",
    "build_incident_report_prompt",
    "build_json_instruction",
    "build_mixed_message_prompt",
    "build_pdf_digest_prompt",
    "build_scene_summary_prompt",
    "extract_expected_pdf_facts",
    "normalize_reply",
    "normalize_text_for_match",
    "validate_json_text",
]


# ======================================================================================
# Text Scenario
# ======================================================================================


class Service(BaseModel):
    """One affected service in the incident report scenario."""

    name: str = Field(description="Service name, e.g. payments-api")
    environment: str = Field(description="Environment, e.g. prod or staging")


class TimelineEvent(BaseModel):
    """One ordered event in the incident timeline."""

    timestamp: str = Field(description="ISO 8601 timestamp")
    description: str


class RootCause(BaseModel):
    """Root-cause section for the incident report scenario."""

    category: str = Field(
        description="Short category label, e.g. config, deploy, dependency"
    )
    summary: str
    contributing_factors: list[str] = Field(default_factory=list)


class RemediationItem(BaseModel):
    """One remediation item in the incident report scenario."""

    owner: str
    action: str
    priority: str = Field(description="One of: P0, P1, P2")
    status: str = Field(description="One of: open, in_progress, done")


class IncidentReport(BaseModel):
    """Structured incident report for the QwenChat text scenario."""

    incident_id: str
    title: str
    severity: str = Field(description="One of: SEV1, SEV2, SEV3")
    started_at: str = Field(description="ISO 8601 timestamp")
    ended_at: str | None = Field(default=None, description="ISO 8601 timestamp or null")
    impact_summary: str
    affected_services: list[Service]
    customer_message: str
    timeline: list[TimelineEvent]
    root_cause: RootCause
    remediation_items: list[RemediationItem]


class CalculationStep(BaseModel):
    """One structured tool step in the QwenChat tool-loop scenario."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Structured final result for the QwenChat tool-loop scenario."""

    steps: list[CalculationStep] = Field(min_length=1)
    final_result: int


class ForcedToolChoiceResult(BaseModel):
    """Structured final result for the named-tool-choice scenario."""

    tool_name: str
    final_result: int
    explanation: str


class VideoObservation(BaseModel):
    """Structured summary for the uploaded-video scenario."""

    action: str = Field(min_length=4)
    location: str = Field(min_length=4)
    evidence: list[str] = Field(min_length=2)


# ======================================================================================
# Prompt Builders
# ======================================================================================


def build_incident_report_prompt() -> str:
    """Build the shared structured incident-report prompt."""
    return (
        "Create an incident report for a simulated outage.\n\n"
        "Constraints:\n"
        "- Use incident_id: INC-1042\n"
        "- Severity: SEV2\n"
        "- Environment for services: prod\n"
        "- affected_services: exactly 2 items\n"
        "- timeline: exactly 4 events\n"
        "- remediation_items: exactly 3 items\n"
        "- Keep all strings short and professional.\n"
    )


def build_mixed_message_prompt() -> str:
    """Build the plain-text prompt for the mixed message-parts scenario."""
    return (
        "Final instruction: inspect the attached image and reply with only "
        "`road-ok` if it shows road or highway traffic. Otherwise reply with "
        "only `not-road`."
    )


# ======================================================================================
# Small Text Helpers
# ======================================================================================


def normalize_reply(text: str) -> str:
    """Normalize a short plain-text reply for stable comparisons."""
    return text.strip().rstrip(".").lower()


def build_json_instruction(schema: type[BaseModel]) -> str:
    """Build a deterministic JSON-only instruction for local validation."""
    json_schema = schema.model_json_schema()
    return (
        "You are a JSON API. Output MUST be valid JSON and MUST conform to this "
        "JSON Schema.\n\n"
        "Return ONLY the JSON (no markdown, no code fences, no extra text).\n\n"
        f"JSON Schema:\n{json.dumps(json_schema, ensure_ascii=False)}"
    )


# ======================================================================================
# JSON Parsing And Validation
# ======================================================================================


def _extract_json_substring(text: str) -> str | None:
    """Best-effort extraction of one JSON object substring from model text."""
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def validate_json_text(
    text: str,
    schema: type[BaseModel],
) -> BaseModel:
    """Parse model text as JSON and validate it against one schema model."""
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
            data = json.loads(candidate)
            return schema.model_validate(data)
        except Exception as exc:
            last_error = exc
            continue

    msg = "The live response did not contain valid schema-matching JSON."
    raise ValueError(msg) from last_error
