# mutation-pin: TREQ_USAGE_NORMALIZATION f3d4b39e06f3f013
# pinned-by: claude-opus-5-5
from __future__ import annotations

from types import SimpleNamespace

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_normalize_usage_derives_total_when_only_one_token_count_is_nonzero() -> None:
    # Nonzero input tokens, zero output tokens, and explicit zero total
    assert normalize_usage(
        {"input_tokens": 128, "output_tokens": 0, "total_tokens": 0}
    ) == (UsageStats(input_tokens=128, output_tokens=0, total_tokens=128))

    # Nonzero input tokens, zero output tokens, and missing total
    assert normalize_usage({"input_tokens": 128, "output_tokens": 0}) == (
        UsageStats(input_tokens=128, output_tokens=0, total_tokens=128)
    )

    # Zero input tokens, nonzero output tokens, and explicit zero total
    assert normalize_usage(
        {"input_tokens": 0, "output_tokens": 64, "total_tokens": 0}
    ) == (UsageStats(input_tokens=0, output_tokens=64, total_tokens=64))

    # Zero input tokens, nonzero output tokens, and missing total
    assert normalize_usage({"input_tokens": 0, "output_tokens": 64}) == (
        UsageStats(input_tokens=0, output_tokens=64, total_tokens=64)
    )

    # Object-based payloads with zero total and asymmetric token counts
    assert normalize_usage(
        SimpleNamespace(input_tokens=128, output_tokens=0, total_tokens=0)
    ) == (UsageStats(input_tokens=128, output_tokens=0, total_tokens=128))
    assert normalize_usage(
        SimpleNamespace(input_tokens=0, output_tokens=64, total_tokens=0)
    ) == (UsageStats(input_tokens=0, output_tokens=64, total_tokens=64))
