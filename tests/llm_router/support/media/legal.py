"""llm_router-specific legal-case scenario helpers.

Why:
    Reuses one structured legal-case contract across OpenAI-compatible text
    tests so the suite proves the same public behavior in sync and async paths.

When to use:
    Import from here when a scenario extracts structured facts from the shared
    synthetic legal-case text.

How:
    Use `LegalCase`, `build_legal_case_prompt()`, and
    `assert_legal_case_response(...)` rather than redefining the same schema in
    multiple e2e files.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from llm_router import LLMRouterResponse
from tests.llm_router.support.assertions import (
    assert_output_text_not_empty,
    parse_json_object,
)


class PartyType(StrEnum):
    """Party type labels used in the structured legal-case schema."""

    INDIVIDUAL = "individual"
    CORPORATION = "corporation"
    GOVERNMENT = "government"


class Party(BaseModel):
    """Structured party entry."""

    name: str
    type: PartyType
    role: str


class LegalCase(BaseModel):
    """Structured legal-case output used by OpenAI-compatible text tests."""

    case_name: str
    court: str
    plaintiffs: list[Party] = Field(min_length=1)
    defendants: list[Party] = Field(min_length=1)
    legal_issues: list[str] = Field(min_length=1)


def build_legal_case_prompt() -> str:
    """Build the shared legal-case extraction prompt."""
    return """
In the High Court of Techville. Case No. 2025-CV-001.

Between:
Global AI Corp (a Delaware corporation), Plaintiff
v.
John Doe (an individual) and Hackers United Ltd., Defendants.

Summary:
Global AI Corp alleges that John Doe, a former employee, stole proprietary
algorithms and shared them with Hackers United Ltd. The plaintiff claims
breach of contract and trade secret misappropriation.
They are seeking $10 million in damages and a permanent injunction
preventing further use of the algorithms.
""".strip()


def assert_legal_case_response(response: LLMRouterResponse) -> LegalCase:
    """Assert coarse invariants for the shared legal-case scenario."""
    assert_output_text_not_empty(response)
    parsed = LegalCase.model_validate(parse_json_object(response.output_text))

    assert "global ai corp" in " ".join(p.name.lower() for p in parsed.plaintiffs)
    defendant_names = " ".join(p.name.lower() for p in parsed.defendants)
    assert "john doe" in defendant_names
    assert "hackers united" in defendant_names
    assert parsed.court.strip()
    assert parsed.case_name.strip()

    issues_text = " ".join(issue.lower() for issue in parsed.legal_issues)
    assert issues_text.strip()
    assert "breach" in issues_text
    assert "trade secret" in issues_text or "misappropriation" in issues_text
    return parsed
