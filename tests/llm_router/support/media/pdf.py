"""llm_router-specific PDF scenario helpers.

Why:
    Keeps the shared PDF extraction schema, prompt, and page-one assertions in
    one place so file e2e scripts compare the same contract across providers.

When to use:
    Import from here when a scenario validates structured extraction from the
    shared `variative.pdf` fixture.

How:
    Use `PDFDigest`, `build_pdf_digest_prompt()`, `extract_expected_pdf_facts()`,
    and `assert_pdf_digest_response(...)` instead of duplicating file-specific
    parsing logic inside each e2e script.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import fitz
from pydantic import BaseModel, Field

from llm_router import LLMRouterResponse
from tests.llm_router.support.assertions import (
    assert_output_text_not_empty,
    assert_response_has_data,
    parse_json_object,
)


class PaperMetadata(BaseModel):
    """Structured title metadata for the shared PDF fixture."""

    title: str
    title_words: list[str] = Field(min_length=3, max_length=3)


class EvidenceSnippet(BaseModel):
    """Short grounded evidence copied from page one."""

    text: str = Field(min_length=8)
    source: Literal["title", "abstract", "introduction"]


class PDFDigest(BaseModel):
    """Structured digest extracted from the shared PDF fixture."""

    metadata: PaperMetadata
    abstract_one_sentence: str = Field(min_length=20)
    contributions: list[str] = Field(min_length=3, max_length=3)
    evidence: list[EvidenceSnippet] = Field(min_length=2, max_length=2)
    key_entities: list[str] = Field(min_length=4, max_length=4)


def build_pdf_digest_prompt() -> str:
    """Build the shared PDF extraction prompt."""
    return (
        "You are given a PDF file attachment.\n\n"
        "Extract content from the PDF (focus on the paper itself, not file metadata).\n"
        "Return JSON with:\n"
        "- metadata.title: exact paper title from page 1, as a single line\n"
        "- metadata.title_words: exactly 3 distinct words taken from the title, "
        "preserving case\n"
        "- abstract_one_sentence: one sentence summarizing the Abstract (<= 25 words)\n"
        "- contributions: exactly 3 short bullet points (<= 12 words each)\n"
        "- evidence: exactly 2 verbatim snippets copied from page 1 (8+ chars). "
        "Choose snippets that are not broken by hyphenation across lines.\n"
        "  - source must be one of: title, abstract, introduction\n"
        "- key_entities: exactly 4 proper nouns or model names that appear on page 1 "
        "(preserve case)\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def normalize_text_for_match(text: str) -> str:
    """Normalize text for robust page-content comparisons."""
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = " ".join(text.split())
    return re.sub(r"\s*-\s*", "-", text)


def _compact_text_for_match(text: str) -> str:
    """Compact text to alphanumerics for OCR/layout-tolerant matching."""
    return re.sub(r"[^a-z0-9]+", "", normalize_text_for_match(text).lower())


def extract_expected_pdf_facts(pdf_path: Path) -> tuple[str, str]:
    """Extract deterministic page-one facts used by the shared assertions."""
    doc = fitz.open(str(pdf_path))
    page = doc.load_page(0)
    text = page.get_text("text") or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "", ""

    title_lines = lines[1:3] if len(lines) >= 3 else lines[:2]
    title = " ".join(title_lines).strip()
    return normalize_text_for_match(text), title


def assert_pdf_digest_response(
    response: LLMRouterResponse,
    *,
    expected_page_text: str,
    expected_title: str,
    allow_compact_snippet_match: bool = False,
    min_entity_matches: int | None = None,
) -> PDFDigest:
    """Assert that a PDF digest matches deterministic page-one facts."""
    assert_response_has_data(response)
    assert_output_text_not_empty(response)

    parsed = PDFDigest.model_validate(parse_json_object(response.output_text))
    normalized_title = normalize_text_for_match(parsed.metadata.title)
    normalized_expected_title = normalize_text_for_match(expected_title)
    normalized_expected_page = normalize_text_for_match(expected_page_text)
    compact_expected_page = _compact_text_for_match(expected_page_text)

    assert normalized_title == normalized_expected_title
    for word in parsed.metadata.title_words:
        assert word
        assert word in parsed.metadata.title

    assert parsed.abstract_one_sentence.strip()
    assert any(
        token in parsed.abstract_one_sentence.lower()
        for token in ("grading", "handwritten", "feedback", "assessment")
    )

    for snippet in parsed.evidence:
        normalized_snippet = normalize_text_for_match(snippet.text)
        if allow_compact_snippet_match:
            assert (
                normalized_snippet in normalized_expected_page
                or _compact_text_for_match(normalized_snippet) in compact_expected_page
            )
        else:
            assert normalized_snippet in normalized_expected_page

    matched_entities = 0
    for entity in parsed.key_entities:
        assert entity
        normalized_entity = normalize_text_for_match(entity)
        if allow_compact_snippet_match:
            matched = (
                normalized_entity in normalized_expected_page
                or _compact_text_for_match(normalized_entity) in compact_expected_page
            )
        else:
            matched = normalized_entity in normalized_expected_page
        matched_entities += int(matched)

    required_entity_matches = (
        len(parsed.key_entities) if min_entity_matches is None else min_entity_matches
    )
    assert matched_entities >= required_entity_matches

    return parsed
