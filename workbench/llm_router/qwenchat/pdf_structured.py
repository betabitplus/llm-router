# %%
"""QwenChat PDF structured-output workbench script.

Why:
    Shows that QwenChat uploads one real PDF first, injects the returned file
    URL into the mixed content payload, and then returns structured extraction.

Covers:
    Area: qwenchat live file input
    Behavior: PDF upload, mixed content payload, structured output
    Interface: `POST /files/upload`, `POST /chat/completions`

Checks:
    If the direct QwenChat proxy accepts the shared PDF fixture, then the document-input
        seam is working.
    If the result exposes `expected_title`, `observed_title`, and
        `title_matches_expected`, then the manual run proves the structured extraction
        stayed grounded in the paper's page-one title.
    If the result also exposes `attempts` and `usage`, then the manual run shows how the
        structured path completed and what token accounting it returned.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.qwenchat.pdf_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.qwenchat.pdf_structured
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console, get_test_data_path

from workbench.llm_router.qwenchat._runtime import build_sync_client, qwenchat_base_url
from workbench.llm_router.qwenchat._structured_output import (
    PDFDigest,
    build_pdf_digest_prompt,
    extract_expected_pdf_facts,
    normalize_text_for_match,
)
from workbench.llm_router.qwenchat._structured_runner import (
    StructuredRunConfig,
    run_structured_sync,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the shared PDF fixture fixed so this script stays about the upload plus
# structured extraction seam instead of document variability.
_MODEL = "qwen2.5-vl-32b-instruct"
_PDF_PATH = get_test_data_path("llm_router") / "variative.pdf"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROMPT = build_pdf_digest_prompt()
_TEMPERATURE = 0.0
_SEED = 42


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real QwenChat PDF-structured request."""
    # Extract the expected page-one title first so the manual output can prove
    # the live structured result still stays grounded in the PDF.
    _, expected_title = extract_expected_pdf_facts(_PDF_PATH)
    with build_sync_client() as client:
        result = run_structured_sync(
            client=client,
            config=StructuredRunConfig(
                model=_MODEL,
                base_items=[_SYSTEM_PROMPT, _PROMPT, _PDF_PATH],
                schema_model=PDFDigest,
                temperature=_TEMPERATURE,
                seed=_SEED,
            ),
        )

    parsed = result["parsed"]
    observed_title = parsed["metadata"]["title"]
    return {
        "attempts": result["attempts"],
        "expected_title": expected_title,
        "observed_title": observed_title,
        "title_matches_expected": (
            normalize_text_for_match(observed_title)
            == normalize_text_for_match(expected_title)
        ),
        "parsed": parsed,
        "usage": result["usage"],
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        (
            "Uploading the shared PDF fixture through live QwenChat and "
            "asking for a structured digest."
        ),
        details=(
            f"Base URL: {qwenchat_base_url()}",
            f"Model: {_MODEL}",
            f"File: {_PDF_PATH.name}",
        ),
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Structured PDF Output",
        (
            "The live response returned a structured digest whose title "
            "still matches the paper."
        ),
        details=(
            f"expected_title: {result['expected_title']}",
            f"observed_title: {result['observed_title']}",
            f"title_matches_expected: {result['title_matches_expected']}",
            f"attempts: {result['attempts']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the QwenChat file upload and structured "
        "PDF extraction path work in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13 (excerpt):
{
  "attempts": 1,
  "expected_title": "AI-assisted Automated Short Answer ... Mathematics Exams",
  "observed_title": "AI-assisted Automated Short Answer ... Mathematics Exams",
  "title_matches_expected": true
}
""".strip()
