from __future__ import annotations

from types import SimpleNamespace

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage


def test_none_usage_stays_absent() -> None:
    assert normalize_usage(None) is None


def test_existing_usage_stats_are_preserved() -> None:
    usage = UsageStats(input_tokens=1, output_tokens=2, total_tokens=3)

    assert normalize_usage(usage) is usage


def test_openai_style_mapping_usage_normalizes() -> None:
    usage = normalize_usage(
        {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
    )

    assert usage == UsageStats(input_tokens=10, output_tokens=5, total_tokens=15)


def test_google_style_object_usage_normalizes_and_computes_total() -> None:
    raw = SimpleNamespace(prompt_token_count=4, candidates_token_count=6)

    usage = normalize_usage(raw)

    assert usage == UsageStats(input_tokens=4, output_tokens=6, total_tokens=10)


def test_google_camel_case_nested_usage_normalizes() -> None:
    raw = SimpleNamespace(
        usageMetadata=SimpleNamespace(
            promptTokenCount=3,
            candidatesTokenCount=4,
            totalTokenCount=7,
        )
    )

    usage = normalize_usage(raw)

    assert usage == UsageStats(input_tokens=3, output_tokens=4, total_tokens=7)


def test_nested_usage_mapping_normalizes() -> None:
    usage = normalize_usage(
        {
            "usage": {
                "input_tokens": 7,
                "output_tokens": 8,
            }
        }
    )

    assert usage == UsageStats(input_tokens=7, output_tokens=8, total_tokens=15)
