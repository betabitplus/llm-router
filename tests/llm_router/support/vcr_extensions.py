"""llm_router-specific VCR extension registration.

Why:
    Keeps llm_router request matching policy and VCR registration separate from
    shared cross-project matcher primitives.

When to use:
    Import from here when the llm_router test suite configures its VCR
    instance or directly exercises llm_router request-body matching.

How:
    Register the exported matcher functions on a VCR instance and reuse the
    shared `MATCH_ON` and `FILTER_HEADERS` values instead of redefining them.
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import method_case_insensitive

from tests.llm_router.support._vcr_body_matching import body_llmrouter

_VCR_EXTENSIONS_REGISTERED_ATTR = "_llm_router_vcr_extensions_registered"

MATCH_ON: list[str] = ["method", "scheme", "host", "port", "path", "body_llmrouter"]
FILTER_HEADERS: list[str] = [
    "authorization",
    "x-api-key",
    "x-goog-api-key",
    "api-key",
    # Recording can include browser-backed flows (Gemini WebAPI). Never persist
    # session cookies in cassettes.
    "cookie",
    "set-cookie",
]


def register_vcr_extensions(vcr_obj: Any) -> None:
    """Register llm_router matchers once on the given VCR object."""
    if getattr(vcr_obj, _VCR_EXTENSIONS_REGISTERED_ATTR, False):
        return

    vcr_obj.register_matcher("method", method_case_insensitive)
    vcr_obj.register_matcher("body_llmrouter", body_llmrouter)
    setattr(vcr_obj, _VCR_EXTENSIONS_REGISTERED_ATTR, True)
