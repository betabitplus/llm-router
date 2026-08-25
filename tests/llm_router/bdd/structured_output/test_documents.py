# %%
"""Bindings for the structured document living specification."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import pymupdf
from py_lib_testkit import evidence
from pydantic import BaseModel, Field
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import (
    assert_response_has_data,
    parse_json_object,
)
from tests.llm_router.support.builders import (
    build_test_pdf_file,
    get_llm_router_test_data_path,
)

scenarios("structured_output/documents.feature")

_PDF_FILENAME = "variative.pdf"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_TEST_MODULE = "tests/llm_router/bdd/structured_output/test_documents.py"


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
    key_entities: list[str] = Field(
        min_length=4,
        max_length=4,
        description=(
            "Exactly four complete proper-noun or model-name strings copied verbatim "
            "from the PDF; do not infer abbreviations or outside entities."
        ),
    )


def _normalize_text(text: str) -> str:
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = " ".join(text.split())
    return re.sub(r"\s*-\s*", "-", text)


def _expected_pdf_facts(pdf_path: Path) -> tuple[str, str, str]:
    document = pymupdf.open(str(pdf_path))
    page_text = document.load_page(0).get_text("text") or ""
    document_text = "\n".join(
        document.load_page(index).get_text("text") or ""
        for index in range(document.page_count)
    )
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    title_lines = lines[1:3] if len(lines) >= 3 else lines[:2]
    return (
        _normalize_text(page_text),
        _normalize_text(document_text),
        " ".join(title_lines).strip(),
    )


def _usage_payload(response: LLMRouterResponse) -> object:
    return (
        response.usage.model_dump(mode="json") if response.usage is not None else None
    )


@given("the QwenChat document route", target_fixture="router")
def qwenchat_document_route() -> LLMRouter:
    """Build the QwenChat route used by the PDF example."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_VL_32B, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


@when("the route analyzes the example PDF:", target_fixture="response")
def analyze_example_pdf(router: LLMRouter, docstring: str) -> LLMRouterResponse:
    """Send the shared PDF through the public file path using the Gherkin prompt."""
    pdf_path = get_llm_router_test_data_path(_PDF_FILENAME)
    evidence.file("Input PDF", pdf_path, media_type="application/pdf")
    return router.query(
        [_SYSTEM_PROMPT, docstring, build_test_pdf_file(_PDF_FILENAME)],
        response_schema=PDFDigest,
    )


@then("the digest is grounded in the PDF text")
def pdf_digest_is_grounded(response: LLMRouterResponse) -> None:
    """Validate source grounding and publish the extracted digest."""
    assert_response_has_data(response)
    content = response.data.choices[0].message.content
    assert isinstance(content, str)
    assert content.strip()
    digest = PDFDigest.model_validate(parse_json_object(content))

    page_text, document_text, expected_title = _expected_pdf_facts(
        get_llm_router_test_data_path(_PDF_FILENAME)
    )
    assert _normalize_text(digest.metadata.title) == _normalize_text(expected_title)
    assert all(
        word and word in digest.metadata.title for word in digest.metadata.title_words
    )
    assert any(
        token in digest.abstract_one_sentence.lower()
        for token in ("grading", "handwritten", "feedback", "assessment")
    )
    assert all(_normalize_text(item.text) in page_text for item in digest.evidence)
    grounded_entities = sum(
        _normalize_text(entity) in document_text
        for entity in digest.key_entities
        if entity
    )
    assert grounded_entities >= 3

    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "expected_title": expected_title,
            "digest": digest.model_dump(mode="json"),
        },
    )


# %% Run this cell in VS Code's Interactive Window for a real provider call.
if __name__ == "__main__":
    import ipytest

    ipytest.run(
        "-q",
        "-s",
        "--disable-recording",
        "--no-cov",
        _TEST_MODULE,
        defopts=False,
        raise_on_error=True,
    )
# %%
