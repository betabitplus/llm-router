# %%
"""LLM Router e2e: Google GenAI PDF file + structured output.

Why:
    Verifies native Google PDF ingestion with structured extraction output.

Covers:
    Area: Google GenAI provider
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
            tests.llm_router.e2e.provider_sdk_wrapping.test_google_genai_file_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_file_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode

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
    pytest.mark.e2e_contract,
    pytest.mark.cap_file,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_PDF_FILENAME = "variative.pdf"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# Keeping one shared PDF fixture makes the extracted facts directly comparable
# with the other document scenarios.


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
        RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, file: FileSchema) -> LLMRouterResponse:
    """Run the Google GenAI PDF pipeline."""
    # This is the end-to-end public flow: one prompt, one PDF, one schema.
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
    # Reuse the common PDF contract so this scenario stays focused on proving
    # the native Google path, not a different set of PDF assertions.
    assert_pdf_digest_response(
        response,
        expected_page_text=expected_page_text,
        expected_title=expected_title,
    )


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # Extract deterministic facts up front so we know what the model must preserve.
    expected_page_text, expected_title = extract_expected_pdf_facts(
        get_llm_router_test_data_path(_PDF_FILENAME)
    )
    # Then run the real PDF workflow once.
    response = run_pipeline(file=build_test_pdf_file(_PDF_FILENAME))
    # Finally, prove the structured answer stays grounded in the document.
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
        "We ask the native Google client to read a PDF and turn it "
        "into a structured digest.",
        details=[f"File: {_PDF_FILENAME}", f"Prompt: {build_prompt()}"],
    )

    expected_page_text, expected_title = extract_expected_pdf_facts(
        get_llm_router_test_data_path(_PDF_FILENAME)
    )
    # Run the same public PDF flow the test validates.
    response = run_pipeline(file=build_test_pdf_file(_PDF_FILENAME))

    # Validate first so the printed digest reflects a checked result.
    parsed = assert_pdf_digest_response(
        response,
        expected_page_text=expected_page_text,
        expected_title=expected_title,
    )
    console.demo_step(
        "What Happened",
        "The PDF was converted into a structured summary with evidence "
        "tied back to page content.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the structured extraction kept the title "
        "and evidence grounded in the real document."
    )


if __name__ == "__main__":
    main()
# %%
