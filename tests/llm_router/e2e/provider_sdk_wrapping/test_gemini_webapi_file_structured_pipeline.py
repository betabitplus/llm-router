"""LLM Router e2e: Gemini WebAPI PDF file + structured output.

Why:
    Verifies that the browser-backed Gemini route supports PDF input with local
    structured-output validation.

Covers:
    Area: Gemini WebAPI provider
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

Notes:
    Live execution requires local browser cookies for Gemini WebAPI access.

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
from tests.llm_router.support.media.gemini_webapi import require_runtime
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
# We keep one shared PDF fixture so cross-provider PDF scenarios are easy to compare.


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
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, file: FileSchema) -> LLMRouterResponse:
    """Run the Gemini WebAPI PDF pipeline."""
    # This is the whole public flow: prompt plus one PDF attachment and schema.
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
    # Reuse the common PDF helper so title, evidence, and entity checks stay
    # consistent with the native Google and Qwen PDF scenarios.
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
    require_runtime()
    # Derive deterministic facts from the PDF before calling the router so we
    # know what concrete evidence the model should preserve.
    expected_page_text, expected_title = extract_expected_pdf_facts(
        get_llm_router_test_data_path(_PDF_FILENAME)
    )
    # Then run the public PDF workflow once.
    response = run_pipeline(file=build_test_pdf_file(_PDF_FILENAME))
    # Finally, prove the structured answer stays grounded in the source document.
    assert_pipeline_response(
        response,
        expected_page_text=expected_page_text,
        expected_title=expected_title,
    )
