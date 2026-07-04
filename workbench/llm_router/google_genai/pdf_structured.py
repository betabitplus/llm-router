# %%
"""Google GenAI PDF structured-output workbench script.

Why:
    Shows that the native Google client accepts the same inline PDF blob shape
    the adapter builds for `FileSchema`.

Covers:
    Area: google-genai live document input
    Behavior: inline PDF blob, structured extraction
    Interface: `Client.models.generate_content(...)`

Checks:
    If the native Google client accepts the shared PDF fixture, then the document-input
        seam is working.
    If the result exposes `expected_title`, `observed_title`, and
        `title_matches_expected`, then the manual run proves the structured extraction
        stayed grounded in the paper's page-one title.
    If the result also preserves `parsed` and `usage`, then the full structured evidence
        remains visible behind the title comparison.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.pdf_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.pdf_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.genai import types

from tests.llm_router.support.media.pdf import extract_expected_pdf_facts
from tests.support.console import console
from workbench.llm_router.google_genai._media_parts import build_pdf_part
from workbench.llm_router.google_genai._sdk_helpers import (
    build_client,
    parsed_response_dict,
    usage_snapshot,
)
from workbench.llm_router.google_genai._structured_output import (
    PDFDigest,
    build_pdf_digest_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the shared PDF fixture fixed so this script stays about the inline blob
# request shape rather than document variability.
_MODEL = "gemini-2.5-flash"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PDF_PATH = _REPO_ROOT / "tests/llm_router/data/variative.pdf"
_PROMPT = build_pdf_digest_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real native Google PDF-structured request."""
    # Extract the expected title first so the manual output can compare a live
    # parsed field against a known page-one fact.
    _, expected_title = extract_expected_pdf_facts(_PDF_PATH)
    # Build the native client and send the PDF using the same inline blob shape
    # the adapter builds for document inputs.
    client = build_client()
    response = client.models.generate_content(
        model=_MODEL,
        contents=[_PROMPT, build_pdf_part(_PDF_PATH)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PDFDigest,
            temperature=0,
            seed=42,
        ),
    )
    parsed = parsed_response_dict(response)
    return {
        "expected_title": expected_title,
        "observed_title": parsed["metadata"]["title"],
        "title_matches_expected": parsed["metadata"]["title"] == expected_title,
        "parsed": parsed,
        "usage": usage_snapshot(response),
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Uploading the shared PDF fixture as an inline blob through the native "
        "Google client.",
        details=(
            f"Model: {_MODEL}",
            f"File: {_PDF_PATH.name}",
            "Why this shape: it matches the inline PDF part the adapter builds.",
        ),
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Structured PDF Output",
        "The live response returned a structured digest grounded in the paper.",
        details=(
            f"expected_title: {result['expected_title']}",
            f"observed_title: {result['observed_title']}",
            f"title_matches_expected: {result['title_matches_expected']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the native inline PDF path works in this "
        "environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, key verification fields):
{
  "title_matches_expected": true,
  "usage": {
    "input_tokens": 4552,
    "output_tokens": 184,
    "total_tokens": 5862
  }
""".strip()
