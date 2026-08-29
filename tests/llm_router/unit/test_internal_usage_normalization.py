from __future__ import annotations

from types import SimpleNamespace

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = [
    pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


def test_openai_usage_mapping_normalizes() -> None:
    assert normalize_usage(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    ) == UsageStats(input_tokens=10, output_tokens=5, total_tokens=15)


def test_google_usage_object_normalizes_and_computes_total() -> None:
    raw = SimpleNamespace(prompt_token_count=4, candidates_token_count=6)

    assert normalize_usage(raw) == UsageStats(
        input_tokens=4,
        output_tokens=6,
        total_tokens=10,
    )


def test_nested_usage_mapping_normalizes() -> None:
    assert normalize_usage({"usage": {"input_tokens": 7, "output_tokens": 8}}) == (
        UsageStats(input_tokens=7, output_tokens=8, total_tokens=15)
    )
