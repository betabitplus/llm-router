# %%
"""Bindings for the structured document BDD scenario."""

from __future__ import annotations

import pytest
from py_lib_testkit import evidence
from pytest_bdd import given, parsers, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.bdd._support import prepare_gemini_webapi_runtime
from tests.llm_router.support.builders import (
    build_test_pdf_file,
    get_llm_router_test_data_path,
)
from tests.llm_router.support.media.pdf import (
    PDFDigest,
    assert_pdf_digest_response,
    extract_expected_pdf_facts,
    extract_pdf_document_text,
)

scenarios("structured_output/documents.feature")

_PDF_FILENAME = "variative.pdf"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_TEST_MODULE = "tests/llm_router/bdd/structured_output/test_documents.py"


def _usage_payload(response: LLMRouterResponse) -> object:
    return (
        response.usage.model_dump(mode="json") if response.usage is not None else None
    )


@given(parsers.parse('the "{route}" document route'), target_fixture="document_route")
def provider_document_route(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> tuple[str, LLMRouter]:
    if route == "QwenChat":
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_VL_32B, provider=Provider.QWENCHAT),
            temperature=0.0,
            seed=42,
        )
    elif route == "AI Studio":
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
            temperature=0.0,
            seed=42,
        )
    elif route == "Gemini WebAPI":
        prepare_gemini_webapi_runtime(monkeypatch, request)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
            temperature=0.0,
            seed=42,
        )
    elif route == "Google GenAI":
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
            temperature=0.0,
            seed=42,
        )
    else:  # pragma: no cover - Examples owns the valid values.
        raise ValueError(route)
    return route, router


@when("the route analyzes the example PDF:", target_fixture="response")
def analyze_example_pdf(
    document_route: tuple[str, LLMRouter],
    docstring: str,
) -> LLMRouterResponse:
    _, router = document_route
    pdf_path = get_llm_router_test_data_path(_PDF_FILENAME)
    evidence.file("Input PDF", pdf_path, media_type="application/pdf")
    return router.query(
        [_SYSTEM_PROMPT, docstring, build_test_pdf_file(_PDF_FILENAME)],
        response_schema=PDFDigest,
    )


@then("the digest is grounded in the PDF text")
def pdf_digest_is_grounded(
    response: LLMRouterResponse,
    document_route: tuple[str, LLMRouter],
) -> None:
    route, _ = document_route
    pdf_path = get_llm_router_test_data_path(_PDF_FILENAME)
    page_text, expected_title = extract_expected_pdf_facts(pdf_path)
    relaxed_layout = route in {"AI Studio", "Gemini WebAPI"}
    qwenchat = route == "QwenChat"
    digest = assert_pdf_digest_response(
        response,
        expected_page_text=page_text,
        expected_title=expected_title,
        allow_compact_snippet_match=relaxed_layout,
        min_entity_matches=3 if qwenchat else (2 if relaxed_layout else None),
        expected_entity_text=extract_pdf_document_text(pdf_path) if qwenchat else None,
    )
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


# %% Run this cell for document scenarios against live providers.
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
