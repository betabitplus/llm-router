"""LLM Router e2e: AI Studio PDF file + structured output.

Why:
    Verifies that AI Studio supports the native PDF/file path with structured
    extraction from the shared paper fixture.

Covers:
    Area: AI Studio provider
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
    text under the fixture-tolerant matching rule.
    If entity extraction is correct, then at least the required key-entity matches map
    back to page-one text.

"""

from __future__ import annotations

import pytest

from llm_router import (
    FileSchema,
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
)
from tests.llm_router.support.builders import (
    build_test_pdf_file,
    get_llm_router_test_data_path,
)
from tests.llm_router.support.media.pdf import (
    PDFDigest,
    assert_pdf_digest_response,
    build_pdf_digest_prompt,
    extract_expected_pdf_facts,
)

pytestmark = [
    pytest.mark.cap_file,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_PDF_FILENAME = "variative.pdf"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# Reuse the same PDF fixture as the other file-capability tests so this script
# isolates the AI Studio native file path rather than changing document content.


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the PDF extraction prompt."""
    return build_pdf_digest_prompt()


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, file: FileSchema) -> LLMRouterResponse:
    """Run the AI Studio PDF pipeline."""
    # Keep the public call shape obvious: prompt, one PDF attachment, one schema.
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
    """Assert the response matches deterministic PDF facts."""
    # Native AI Studio media responses can be a little noisier, so we keep the
    # shared grounding checks but allow compact snippet/entity matching.
    assert_pdf_digest_response(
        response,
        expected_page_text=expected_page_text,
        expected_title=expected_title,
        allow_compact_snippet_match=True,
        min_entity_matches=2,
    )


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    # Extract deterministic grounding facts first so the assertion stays source-based.
    expected_page_text, expected_title = extract_expected_pdf_facts(
        get_llm_router_test_data_path(_PDF_FILENAME)
    )
    # Then run the public PDF workflow once.
    response = run_pipeline(file=build_test_pdf_file(_PDF_FILENAME))
    # Finally, prove the structured answer still points back to the document.
    assert_pipeline_response(
        response,
        expected_page_text=expected_page_text,
        expected_title=expected_title,
    )
