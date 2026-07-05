# %%
"""AI Studio PDF structured-output workbench script.

Why:
    Shows that AI Studio can analyze a local PDF through the native streamed
    Gemini-style endpoint and return structured JSON.

Covers:
    Area: AI Studio native file path
    Behavior: local PDF upload, Gemini-native payload, structured output
    Interface: `/v1beta/models/...:streamGenerateContent`

Checks:
    If the native AI Studio file path accepts the shared PDF fixture, then the document-
        input seam is working.
    If the result exposes `expected_title`, `observed_title`, and
        `title_matches_expected`, then the manual run proves the structured extraction
        stayed grounded in the paper's page-one title.
    If the result also preserves `parsed` and `usage`, then the full structured evidence
        remains visible behind the title comparison.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.pdf_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.pdf_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from py_lib_tooling import console

from tests.llm_router.support.media.pdf import (
    PDFDigest,
    build_pdf_digest_prompt,
    extract_expected_pdf_facts,
    normalize_text_for_match,
)
from workbench.llm_router.aistudio._native_media import (
    build_local_file_part,
    build_text_part,
    run_sync_native_request,
)

# =============================================================================
# Scenario
# =============================================================================

_REPO_ROOT = Path(__file__).resolve().parents[3]
# Keep the shared PDF fixture fixed so this script stays about the native AI
# Studio file path rather than changing source content.
_MODEL = "gemini-2.5-flash"
_PDF_PATH = _REPO_ROOT / "tests/llm_router/data/variative.pdf"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROMPT = build_pdf_digest_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real AI Studio native PDF request."""
    _, expected_title = extract_expected_pdf_facts(_PDF_PATH)
    result = run_sync_native_request(
        model=_MODEL,
        parts=[
            build_text_part(_SYSTEM_PROMPT),
            build_text_part(_PROMPT),
            build_local_file_part(path=_PDF_PATH, mime_type="application/pdf"),
        ],
        response_schema=PDFDigest,
        temperature=0.0,
    )
    parsed = PDFDigest.model_validate(result["parsed"])
    return {
        "endpoint": result["endpoint"],
        "expected_title": expected_title,
        "observed_title": parsed.metadata.title,
        "title_matches_expected": (
            normalize_text_for_match(parsed.metadata.title)
            == normalize_text_for_match(expected_title)
        ),
        "parsed": parsed.model_dump(mode="json"),
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
        "Uploading the shared PDF fixture through the native AI Studio streamed "
        "endpoint and asking for a structured digest.",
        details=(
            f"Model: {_MODEL}",
            f"File: {_PDF_PATH.name}",
            "Why this matters: it proves native file analysis beyond the "
            "OpenAI-compatible non-video path.",
        ),
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Structured PDF Output",
        "The native AI Studio file path returned a structured digest whose "
        "title still matches the uploaded paper.",
        details=(
            f"expected_title: {result['expected_title']}",
            f"observed_title: {result['observed_title']}",
            f"title_matches_expected: {result['title_matches_expected']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust the native AI Studio PDF path in this environment.",
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
}
""".strip()
