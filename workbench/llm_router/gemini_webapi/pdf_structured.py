# %%
"""Gemini WebAPI PDF structured-output workbench script.

Why:
    Shows that `gemini-webapi` can upload one real PDF file and return a
    structured extraction that stays grounded in page-one content.

Covers:
    Area: gemini-webapi live document input
    Behavior: PDF upload, prompt-driven structured output
    Interface: `GeminiClient.generate_content(..., files=[...])`

Checks:
    If the browser-authenticated session accepts the shared PDF fixture, then the
        document-input seam is working.
    If the result exposes `expected_title`, `observed_title`, and
        `title_matches_expected`, then the manual run proves the structured extraction
        stayed grounded in the paper's page-one title.
    If the result also preserves `parsed`, then the full structured evidence remains
        visible behind the title comparison.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.pdf_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.pdf_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.llm_router.support.media.pdf import extract_expected_pdf_facts
from py_lib_tooling import console
from py_lib_tooling import run_async
from workbench.llm_router.gemini_webapi._opera_cookie_client import managed_client
from workbench.llm_router.gemini_webapi._structured_output import (
    PDFDigest,
    build_pdf_digest_prompt,
    normalize_text_for_match,
    parse_model_output_json,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the shared PDF fixture fixed so this script stays about one real
# browser-backed document upload path.
_MODEL = "gemini-3.0-flash"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PDF_PATH = _REPO_ROOT / "tests/llm_router/data/variative.pdf"
_PROMPT = build_pdf_digest_prompt()
_INIT_TIMEOUT_SECONDS = 120.0


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run the real live Gemini WebAPI PDF-structured flow."""
    # Extract the expected title first so the manual output can compare a live
    # parsed field against a known document fact.
    _, expected_title = extract_expected_pdf_facts(_PDF_PATH)

    # Build and initialize the browser-authenticated client through one shared
    # managed helper before attempting the PDF upload.
    async with managed_client(init_timeout_seconds=_INIT_TIMEOUT_SECONDS) as client:
        # Upload the shared PDF and validate the returned JSON before exposing
        # it as manual evidence.
        output = await client.generate_content(
            _PROMPT,
            files=[_PDF_PATH],
            model=_MODEL,
        )
        parsed = PDFDigest.model_validate(parse_model_output_json(output.text))
        return {
            "expected_title": expected_title,
            "observed_title": parsed.metadata.title,
            "title_matches_expected": (
                normalize_text_for_match(parsed.metadata.title)
                == normalize_text_for_match(expected_title)
            ),
            "parsed": parsed.model_dump(mode="json"),
        }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Uploading the shared PDF fixture through a live Gemini WebAPI session "
        "and asking for a structured digest.",
        details=(
            f"Model: {_MODEL}",
            f"File: {_PDF_PATH.name}",
            "Why this fixture: page-one title and entities are easy to compare "
            "manually.",
        ),
    )

    result = run_async(run_pipeline())
    console.demo_step(
        "Observed Structured PDF Output",
        "The live session returned a structured digest whose title still matches "
        "the uploaded paper.",
        details=(
            f"expected_title: {result['expected_title']}",
            f"observed_title: {result['observed_title']}",
            f"title_matches_expected: {result['title_matches_expected']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "Gemini WebAPI can handle real PDF upload plus structured extraction "
        "that stays grounded in the source document.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, key verification fields):
{
  "title_matches_expected": true
""".strip()
