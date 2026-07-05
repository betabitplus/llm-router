# %%
"""LLM Router e2e: QwenChat PDF file + structured output.

Why:
    Verifies that the QwenChat file-upload path supports structured extraction
    from the shared PDF fixture.

Covers:
    Area: QwenChat provider
    Behavior: `FileSchema`, structured output
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If the PDF response succeeds, then it includes structured data and non-empty output
    text.
    If title extraction is correct, then `metadata.title` matches the deterministic
    page-one title.
    If title-word extraction is correct, then every `title_words` entry is non-empty and
    appears in the returned title.
    If abstract summarization is grounded correctly, then `abstract_one_sentence` is
    non-empty and mentions the paper topic.
    If evidence extraction is correct, then every evidence snippet maps back to page-one
    text.
    If entity extraction is correct, then the required key entities map back to page-one
    text.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_qwenchat_file_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_qwenchat_file_structured_pipeline.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import fitz
import pytest
from pydantic import BaseModel, Field

from llm_router import (
    FileSchema,
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
)
from tests.llm_router.support.assertions import (
    assert_response_has_data,
    parse_json_object,
)
from tests.llm_router.support.builders import (
    build_test_pdf_file,
    get_llm_router_test_data_path,
)
from py_lib_tooling import console
from py_lib_tooling import require_vcr_cassette_or_record_mode

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_file,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_PDF_FILENAME = "variative.pdf"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# One fixed PDF makes it easy to compare Qwen behavior with the other document flows.


# =============================================================================
# Helpers
# =============================================================================


class PaperMetadata(BaseModel):
    title: str
    title_words: list[str] = Field(min_length=3, max_length=3)


class EvidenceSnippet(BaseModel):
    text: str = Field(min_length=8)
    source: Literal["title", "abstract", "introduction"]


class PDFDigest(BaseModel):
    metadata: PaperMetadata
    abstract_one_sentence: str = Field(min_length=20)
    contributions: list[str] = Field(min_length=3, max_length=3)
    evidence: list[EvidenceSnippet] = Field(min_length=2, max_length=2)
    key_entities: list[str] = Field(min_length=4, max_length=4)


def normalize_text_for_match(text: str) -> str:
    """Normalize PDF/model text for robust substring checks."""
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = " ".join(text.split())
    return re.sub(r"\s*-\s*", "-", text)


def extract_expected_pdf_facts(pdf_path: Path) -> tuple[str, str]:
    """Extract deterministic content from page one for validation."""
    doc = fitz.open(str(pdf_path))
    page = doc.load_page(0)
    text = page.get_text("text") or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "", ""

    title_lines = lines[1:3] if len(lines) >= 3 else lines[:2]
    title = " ".join(title_lines).strip()
    return normalize_text_for_match(text), title


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the PDF extraction prompt."""
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


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_VL_32B, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, file: FileSchema) -> LLMRouterResponse:
    """Run the QwenChat PDF pipeline."""
    # Keep the user-facing workflow centralized so tests and demos hit the same path.
    router = build_router()
    return router.query(
        [_SYSTEM_PROMPT, build_prompt(), file],
        response_schema=PDFDigest,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(
    response: LLMRouterResponse,
    *,
    expected_page_text: str,
    expected_title: str,
) -> None:
    """Assert the response matches PDF-derived expectations."""
    # First prove the public response really contains structured content.
    assert_response_has_data(response)
    content = response.data.choices[0].message.content
    assert isinstance(content, str)
    assert content.strip()

    parsed = PDFDigest.model_validate(parse_json_object(content))
    # The title is the strongest deterministic anchor from page one.
    normalized_title = normalize_text_for_match(parsed.metadata.title)
    assert normalized_title == normalize_text_for_match(expected_title)

    # Each sampled title word should genuinely come from the title.
    for word in parsed.metadata.title_words:
        assert word
        assert word in parsed.metadata.title

    # The abstract summary should talk about the real paper topic, not generic filler.
    assert parsed.abstract_one_sentence.strip()
    assert any(
        token in parsed.abstract_one_sentence.lower()
        for token in ("grading", "handwritten", "feedback", "assessment")
    )

    # Evidence snippets and key entities must still map back to the source page.
    for snippet in parsed.evidence:
        assert normalize_text_for_match(snippet.text) in expected_page_text

    for entity in parsed.key_entities:
        assert entity
        assert normalize_text_for_match(entity) in expected_page_text


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully and returns correct structured fields."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # Extract deterministic PDF facts first so we know what grounding to expect.
    expected_page_text, expected_title = extract_expected_pdf_facts(
        get_llm_router_test_data_path(_PDF_FILENAME)
    )
    # Then run the public upload-and-parse flow once.
    response = run_pipeline(file=build_test_pdf_file(_PDF_FILENAME))
    # Finally, prove the structured answer still ties back to the source PDF.
    assert_pipeline_response(
        response,
        expected_page_text=expected_page_text,
        expected_title=expected_title,
    )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We upload a shared PDF fixture to QwenChat and ask for a "
        "structured digest of the paper.",
        details=[f"File: {_PDF_FILENAME}", f"Prompt: {build_prompt()}"],
    )
    expected_page_text, expected_title = extract_expected_pdf_facts(
        get_llm_router_test_data_path(_PDF_FILENAME)
    )

    # Run the exact same upload flow the test asserts.
    response = run_pipeline(file=build_test_pdf_file(_PDF_FILENAME))
    # Validate before printing so the demo stays aligned with the assertions.
    assert_pipeline_response(
        response,
        expected_page_text=expected_page_text,
        expected_title=expected_title,
    )
    parsed = PDFDigest.model_validate(parse_json_object(response.output_text))

    console.demo_step(
        "What Happened",
        "QwenChat returned a structured PDF digest grounded in the document.",
        details=[
            f"Expected title from the PDF: {expected_title}",
            f"Usage: {response.usage}",
        ],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the extracted structure still matches "
        "document facts instead of drifting into a generic summary."
    )


if __name__ == "__main__":
    main()
# %%
